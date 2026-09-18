import json
import os
import sqlite3

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values
from pymongo import MongoClient
from pymongo.server_api import ServerApi

load_dotenv()


class Load:
    """
    Responsável por persistir os dados do pipeline: o resultado bruto da
    extração em um arquivo JSON local, em uma coleção do MongoDB Atlas,
    e o resultado já transformado em tabelas de um banco relacional em
    nuvem (NeonDB).
    """

    def __init__(self):
        self.mongo_uri = os.getenv("MONGODB_URI")
        self.neon_dsn = os.getenv("NEON_DB_URL")
        self.client = MongoClient(self.mongo_uri, server_api=ServerApi("1"))

    def close(self) -> None:
        """Encerra a conexão com o MongoDB."""
        self.client.close()

    def load_json(self, nome_arquivo: str, data: dict | list[dict]) -> None:
        """
        Salva o resultado da extração em um arquivo JSON local, em jsons/.

        Atributos:
            nome_arquivo: nome do arquivo de destino, sem extensão
            data: dicionário ou lista de dicionários retornada pela API
                da Open-Meteo
        """
        os.makedirs("jsons", exist_ok=True)
        with open(f"jsons/{nome_arquivo}.json", "w", encoding="UTF-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"Dados salvos com sucesso em 'jsons/{nome_arquivo}.json'!")

    def load_mongo(self, data: dict | list[dict], db_name: str, collection_name: str) -> None:
        """
        Insere o resultado bruto da extração em uma coleção do MongoDB Atlas.
        Aceita tanto um único documento (dict) — como as respostas da
        Open-Meteo — quanto uma lista de documentos.

        Atributos:
            data: dicionário ou lista de dicionários retornada pela API
                da Open-Meteo
            db_name: nome do banco de dados no MongoDB
            collection_name: nome da coleção onde os documentos serão inseridos
        """
        collection = self.client[db_name][collection_name]

        if isinstance(data, list):
            if data:
                collection.insert_many(data)
        elif data:
            collection.insert_one(data)

        print(f"Dados inseridos com sucesso na coleção '{collection_name}'!")
        self.close()

    def load_neon(
        self,
        df: pd.DataFrame,
        nome_tabela: str,
        schema: str = "public",
    ) -> None:
        """
        Persiste um DataFrame já transformado em um banco PostgreSQL
        (NeonDB) usando a conexão definida na variável de ambiente
        NEON_DB_URL.
        """
        if df.empty:
            raise ValueError("DataFrame vazio. Não há registros para carregar no NeonDB.")

        if not self.neon_dsn:
            raise ValueError("NEON_DB_URL não configurada. Defina a string de conexão do NeonDB.")

        with psycopg2.connect(self.neon_dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(f'DROP TABLE IF EXISTS "{schema}"."{nome_tabela}"')

                colunas_sql = []
                for coluna in df.columns:
                    nome_coluna = str(coluna)
                    if pd.api.types.is_datetime64_any_dtype(df[nome_coluna]):
                        tipo = "TIMESTAMP"
                    elif pd.api.types.is_integer_dtype(df[nome_coluna]):
                        tipo = "BIGINT"
                    elif pd.api.types.is_float_dtype(df[nome_coluna]):
                        tipo = "DOUBLE PRECISION"
                    elif pd.api.types.is_bool_dtype(df[nome_coluna]):
                        tipo = "BOOLEAN"
                    else:
                        tipo = "TEXT"
                    colunas_sql.append(f'"{nome_coluna}" {tipo}')

                cur.execute(
                    f'CREATE TABLE "{schema}"."{nome_tabela}" ({", ".join(colunas_sql)})'
                )

                registros = []
                for _, linha in df.iterrows():
                    registro = []
                    for coluna in df.columns:
                        valor = linha[coluna]
                        if pd.isna(valor):
                            registro.append(None)
                        elif isinstance(valor, pd.Timestamp):
                            registro.append(valor.to_pydatetime())
                        else:
                            registro.append(valor.item() if hasattr(valor, "item") else valor)
                    registros.append(tuple(registro))

                if registros:
                    execute_values(
                        cur,
                        f'INSERT INTO "{schema}"."{nome_tabela}" VALUES %s',
                        registros,
                        page_size=1000,
                    )

        print(f"Dados salvos com sucesso na tabela '{nome_tabela}' do NeonDB!")

    def load_sqlite(
        self,
        df: pd.DataFrame,
        nome_banco: str = "smart_city.db",
        nome_tabela: str = "clima",
    ) -> None:
        """
        Salva um DataFrame (já transformado) em uma tabela de um banco
        SQLite local.

        Atributos:
            df: DataFrame a ser salvo (ex.: retorno de `Transform.transform_clima`
                ou `Transform.transform_qualidade_ar`)
            nome_banco: nome do arquivo do banco SQLite
            nome_tabela: nome da tabela onde os dados serão gravados
        """
        pasta = os.path.dirname(os.path.abspath(nome_banco))
        if pasta:
            os.makedirs(pasta, exist_ok=True)

        conn = sqlite3.connect(nome_banco)
        df.to_sql(nome_tabela, conn, if_exists="replace", index=False)
        conn.close()

        print(f"Dados salvos com sucesso na tabela '{nome_tabela}' do banco '{nome_banco}'!")
