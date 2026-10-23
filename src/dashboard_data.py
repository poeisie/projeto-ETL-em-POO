import time
from typing import Optional
import pandas as pd
import psycopg2

from src.config import NEON_DB_URL


def get_neon_connection(max_retries: int = 3, delay_seconds: float = 1.5):
    """
    Retorna uma conexão ativa com o banco PostgreSQL no NeonDB com política de retentativa.
    Trata eventuais erros de SSL/unexpected EOF causados pelo cold start do compute node do Neon.
    """
    if not NEON_DB_URL:
        raise ValueError("NEON_DB_URL não configurada no ambiente ou no arquivo .env.")

    ultimo_erro = None
    for tentativa in range(1, max_retries + 1):
        try:
            return psycopg2.connect(
                NEON_DB_URL,
                connect_timeout=15,
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=10,
                keepalives_count=5,
            )
        except (psycopg2.OperationalError, psycopg2.DatabaseError) as e:
            ultimo_erro = e
            if tentativa < max_retries:
                time.sleep(delay_seconds * tentativa)
            else:
                raise ultimo_erro


def fetch_cidades_disponiveis() -> list[str]:
    """Retorna a lista de cidades que possuem dados cadastrados no NeonDB."""
    query = """
    SELECT DISTINCT cidade FROM (
        SELECT cidade FROM clima
        UNION
        SELECT cidade FROM qualidade_ar
    ) sub
    ORDER BY cidade ASC;
    """
    try:
        with get_neon_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
                cidades = [r[0] for r in rows if r[0]]
                return cidades if cidades else ["Recife"]
    except Exception as e:
        print(f"Erro ao buscar cidades: {e}")
        return ["Recife"]


def fetch_clima_data(cidade: Optional[str] = None) -> pd.DataFrame:
    """Busca os dados horários de clima salvos no NeonDB com tratamento resiliente de conexão."""
    query = """
        SELECT cidade, data_hora, temperature_2m, relative_humidity_2m, precipitation, wind_speed_10m
        FROM clima
    """
    params = []
    if cidade:
        query += " WHERE cidade = %s"
        params.append(cidade)
    query += " ORDER BY data_hora ASC;"

    try:
        with get_neon_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params)

        if not df.empty and "data_hora" in df.columns:
            df["data_hora"] = pd.to_datetime(df["data_hora"])
        return df
    except Exception as e:
        print(f"Aviso ao buscar clima para {cidade}: {e}")
        return pd.DataFrame()


def fetch_qualidade_ar_data(cidade: Optional[str] = None) -> pd.DataFrame:
    """Busca os dados horários de qualidade do ar salvos no NeonDB com tratamento resiliente de conexão."""
    query = """
        SELECT cidade, data_hora, pm10, pm2_5, carbon_monoxide, nitrogen_dioxide, ozone
        FROM qualidade_ar
    """
    params = []
    if cidade:
        query += " WHERE cidade = %s"
        params.append(cidade)
    query += " ORDER BY data_hora ASC;"

    try:
        with get_neon_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params)

        if not df.empty and "data_hora" in df.columns:
            df["data_hora"] = pd.to_datetime(df["data_hora"])
        return df
    except Exception as e:
        print(f"Aviso ao buscar qualidade do ar para {cidade}: {e}")
        return pd.DataFrame()



def fetch_merged_data(cidade: str) -> pd.DataFrame:
    """Combina os dados de clima e qualidade do ar por timestamp e cidade."""
    df_clima = fetch_clima_data(cidade=cidade)
    df_qualidade = fetch_qualidade_ar_data(cidade=cidade)

    if df_clima.empty and df_qualidade.empty:
        return pd.DataFrame()

    if df_clima.empty:
        return df_qualidade
    if df_qualidade.empty:
        return df_clima

    merged = pd.merge(
        df_clima,
        df_qualidade,
        on=["cidade", "data_hora"],
        how="outer"
    ).sort_values("data_hora").reset_index(drop=True)

    return merged


def fetch_all_cities_summary() -> pd.DataFrame:
    """
    Retorna métricas consolidadas (médias, máximas, mínimas) para todas as cidades
    persistidas no NeonDB para permitir a comparação multi-cidades (Fase 4).
    """
    query = """
        SELECT 
            c.cidade,
            ROUND(AVG(c.temperature_2m)::numeric, 1) as temp_media,
            ROUND(MAX(c.temperature_2m)::numeric, 1) as temp_max,
            ROUND(MIN(c.temperature_2m)::numeric, 1) as temp_min,
            ROUND(AVG(c.relative_humidity_2m)::numeric, 0) as umidade_media,
            ROUND(SUM(c.precipitation)::numeric, 1) as chuva_acumulada,
            ROUND(AVG(c.wind_speed_10m)::numeric, 1) as vento_medio,
            ROUND(AVG(q.pm2_5)::numeric, 1) as pm25_medio,
            ROUND(MAX(q.pm2_5)::numeric, 1) as pm25_max,
            ROUND(AVG(q.pm10)::numeric, 1) as pm10_medio,
            ROUND(AVG(q.ozone)::numeric, 1) as ozone_medio
        FROM clima c
        LEFT JOIN qualidade_ar q ON c.cidade = q.cidade AND c.data_hora = q.data_hora
        GROUP BY c.cidade
        ORDER BY c.cidade ASC;
    """
    try:
        with get_neon_connection() as conn:
            df = pd.read_sql_query(query, conn)
            return df
    except Exception as e:
        print(f"Erro ao buscar resumo das cidades: {e}")
        return pd.DataFrame()


def sincronizar_cidade_api_neon(cidade: str) -> None:
    """Extrai dados atualizados da API Open-Meteo, transforma e salva no NeonDB para a cidade."""
    from src.extract import Extract
    from src.transform import Transform
    from src.load import Load

    ext = Extract()
    trans = Transform()
    ld = Load()

    c_raw = ext.clima(cidade=cidade)
    q_raw = ext.qualidade_ar(cidade=cidade)

    df_c = trans.transform_clima(c_raw)
    df_q = trans.transform_qualidade_ar(q_raw)

    ld.load_neon(df=df_c, nome_tabela="clima")
    ld.load_neon(df=df_q, nome_tabela="qualidade_ar")
    ld.close()
    ext.close()

