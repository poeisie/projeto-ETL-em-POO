"""
Orquestração da pipeline ETL Smart City com Prefect.

Cada etapa da pipeline (API -> MongoDB Atlas -> Transformação -> NeonDB)
vira uma task do Prefect, e o flow `etl_smart_city` organiza a execução
respeitando as dependências entre elas:

    extrair_clima ──> salvar_mongo ──> ler_mongo ──> transformar_clima ──> carregar_neon
    extrair_qualidade_ar ──> salvar_mongo ──> ler_mongo ──> transformar_qualidade_ar ──> carregar_neon

Os dois ramos (clima e qualidade do ar) são independentes entre si e
rodam em paralelo; dentro de cada ramo, uma etapa só começa quando a
anterior termina com sucesso. Se uma task falhar (depois das novas
tentativas configuradas), as tasks que dependem dela não são executadas
e o flow termina com estado "Failed", visível na interface do Prefect.

Uso:
    python flow_etl.py                    # executa o flow uma vez
    python flow_etl.py --cidade Fortaleza # executa para outra cidade
    python flow_etl.py --serve            # deixa o flow agendado (de hora em hora)
"""
import argparse

import pandas as pd
from prefect import flow, get_run_logger, task
from prefect.futures import wait

from src.config import DB_MONGO
from src.extract import Extract
from src.load import Load
from src.transform import Transform


# --- Extração ---------------------------------------------------------------

@task(
    name="Extrair clima (Open-Meteo)",
    retries=3,
    retry_delay_seconds=10,
    tags=["extract", "api"],
)
def extrair_clima(cidade: str, dias_previsao: int) -> dict:
    """Busca a série horária de clima da cidade na Forecast API."""
    logger = get_run_logger()
    ext = Extract()
    try:
        dados = ext.clima(cidade=cidade, dias_previsao=dias_previsao)
    finally:
        ext.close()
    logger.info("Clima de %s: %d registros horários extraídos.", cidade, len(dados["hourly"]["time"]))
    return dados


@task(
    name="Extrair qualidade do ar (Open-Meteo)",
    retries=3,
    retry_delay_seconds=10,
    tags=["extract", "api"],
)
def extrair_qualidade_ar(cidade: str, dias_previsao: int) -> dict:
    """Busca a série horária de poluentes da cidade na Air Quality API."""
    logger = get_run_logger()
    ext = Extract()
    try:
        dados = ext.qualidade_ar(cidade=cidade, dias_previsao=dias_previsao)
    finally:
        ext.close()
    logger.info(
        "Qualidade do ar de %s: %d registros horários extraídos.", cidade, len(dados["hourly"]["time"])
    )
    return dados


# --- Armazenamento bruto (MongoDB Atlas) -----------------------------------

@task(
    name="Salvar dados brutos no MongoDB Atlas",
    retries=2,
    retry_delay_seconds=5,
    tags=["load", "mongodb"],
)
def salvar_mongo(dados: dict, colecao: str) -> str:
    """Grava a resposta bruta da API em uma coleção do MongoDB Atlas."""
    # Copia o dicionário para que o _id gerado pelo MongoDB não altere o
    # resultado da task de extração.
    Load().load_mongo(dict(dados), DB_MONGO, colecao)
    get_run_logger().info("Documento bruto gravado em %s.%s.", DB_MONGO, colecao)
    return colecao


@task(
    name="Ler dados brutos do MongoDB Atlas",
    retries=2,
    retry_delay_seconds=5,
    tags=["extract", "mongodb"],
)
def ler_mongo(colecao: str) -> dict:
    """Lê o documento mais recente da coleção, que alimenta a transformação."""
    ext = Extract()
    try:
        documentos = ext.extract_collection_from_mongo(DB_MONGO, colecao)
    finally:
        ext.close()

    if not documentos:
        raise RuntimeError(f"A coleção '{colecao}' do MongoDB Atlas está vazia.")

    get_run_logger().info("%d documento(s) em %s.%s; usando o mais recente.", len(documentos), DB_MONGO, colecao)
    return documentos[-1]


# --- Transformação ----------------------------------------------------------

@task(name="Transformar clima", tags=["transform"])
def transformar_clima(documento: dict) -> pd.DataFrame:
    """Converte o documento bruto de clima em um DataFrame."""
    df = Transform().transform_clima(documento)
    if df.empty:
        raise ValueError("A transformação de clima gerou um DataFrame vazio.")
    get_run_logger().info("Clima transformado: %d linhas x %d colunas.", *df.shape)
    return df


@task(name="Transformar qualidade do ar", tags=["transform"])
def transformar_qualidade_ar(documento: dict) -> pd.DataFrame:
    """Converte o documento bruto de qualidade do ar em um DataFrame."""
    df = Transform().transform_qualidade_ar(documento)
    if df.empty:
        raise ValueError("A transformação de qualidade do ar gerou um DataFrame vazio.")
    get_run_logger().info("Qualidade do ar transformada: %d linhas x %d colunas.", *df.shape)
    return df


# --- Carga final (NeonDB) ---------------------------------------------------

@task(
    name="Carregar no NeonDB",
    retries=2,
    retry_delay_seconds=10,
    tags=["load", "neondb"],
)
def carregar_neon(df: pd.DataFrame, tabela: str) -> int:
    """Recria a tabela no NeonDB e carrega o DataFrame transformado."""
    ld = Load()
    try:
        ld.load_neon(df=df, nome_tabela=tabela)
    finally:
        ld.close()
    get_run_logger().info("%d linhas carregadas na tabela public.%s do NeonDB.", len(df), tabela)
    return len(df)


# --- Flow -------------------------------------------------------------------

@flow(
    name="ETL Smart City",
    description="API Open-Meteo -> MongoDB Atlas -> Transformação (pandas) -> NeonDB",
    log_prints=True,
)
def etl_smart_city(cidade: str = "Recife", dias_previsao: int = 1) -> dict:
    """
    Orquestra a pipeline completa para uma cidade.

    Parâmetros:
        cidade: nome da cidade (ver `Extract.CIDADES`)
        dias_previsao: dias de previsão a buscar, de 1 a 7
    """
    logger = get_run_logger()

    if cidade not in Extract.CIDADES:
        raise ValueError(f"Cidade não suportada: {cidade}. Opções: {', '.join(Extract.CIDADES)}")
    if not 1 <= dias_previsao <= 7:
        raise ValueError("dias_previsao deve estar entre 1 e 7.")

    logger.info("Iniciando ETL Smart City para %s (%d dia(s) de previsão).", cidade, dias_previsao)

    # Ramo 1: clima
    clima_bruto = extrair_clima.submit(cidade, dias_previsao)
    clima_salvo = salvar_mongo.submit(clima_bruto, "Clima")
    # A leitura não recebe dados da gravação, então a dependência é explícita.
    clima_doc = ler_mongo.submit("Clima", wait_for=[clima_salvo])
    df_clima = transformar_clima.submit(clima_doc)
    carga_clima = carregar_neon.submit(df_clima, "clima")

    # Ramo 2: qualidade do ar (independente do ramo 1, roda em paralelo)
    qualidade_bruta = extrair_qualidade_ar.submit(cidade, dias_previsao)
    qualidade_salva = salvar_mongo.submit(qualidade_bruta, "QualidadeAr")
    qualidade_doc = ler_mongo.submit("QualidadeAr", wait_for=[qualidade_salva])
    df_qualidade = transformar_qualidade_ar.submit(qualidade_doc)
    carga_qualidade = carregar_neon.submit(df_qualidade, "qualidade_ar")

    etapas = [
        clima_bruto, clima_salvo, clima_doc, df_clima, carga_clima,
        qualidade_bruta, qualidade_salva, qualidade_doc, df_qualidade, carga_qualidade,
    ]
    wait(etapas)

    # Quando uma task falha, as que dependem dela nem chegam a rodar. Para o
    # flow terminar como "Failed" com o erro original (e não com um erro
    # genérico de task pendente), relançamos a exceção da primeira task que
    # falhou, na ordem da pipeline.
    falhas = [etapa for etapa in etapas if etapa.state.is_failed()]
    for etapa in falhas:
        logger.error("Etapa com falha: %s", etapa.state.message)
    if falhas:
        falhas[0].result()

    resumo = {
        "cidade": cidade,
        "linhas_clima": carga_clima.result(),
        "linhas_qualidade_ar": carga_qualidade.result(),
    }
    logger.info("ETL concluída: %s", resumo)
    return resumo


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Executa a ETL Smart City orquestrada pelo Prefect.")
    parser.add_argument("--cidade", default="Recife", help="Cidade a consultar (padrão: Recife)")
    parser.add_argument("--dias", type=int, default=1, help="Dias de previsão, de 1 a 7 (padrão: 1)")
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Cria um deployment agendado (de hora em hora) e fica aguardando execuções",
    )
    args = parser.parse_args()

    if args.serve:
        etl_smart_city.serve(
            name="etl-smart-city-horaria",
            cron="0 * * * *",
            parameters={"cidade": args.cidade, "dias_previsao": args.dias},
        )
    else:
        etl_smart_city(cidade=args.cidade, dias_previsao=args.dias)
