import os

import requests
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.server_api import ServerApi

load_dotenv()


class Extract:
    """
    Responsável por extrair dados de duas APIs públicas da Open-Meteo
    ligadas a temas de smart city: previsão do tempo (`clima`) e
    qualidade do ar (`qualidade_ar`), para um conjunto fechado de
    cidades brasileiras. Nenhuma das duas APIs exige cadastro ou chave
    de acesso.

    Também é capaz de reler, de uma coleção do MongoDB, dados que já
    foram carregados anteriormente por `Load.load_mongo`, para alimentar
    a etapa de transformação do pipeline (mesmo padrão usado no projeto
    do PNAD Contínua/IBGE).
    """

    # Conjunto fechado de cidades suportadas: nome -> (latitude, longitude)
    CIDADES = {
        "Recife": (-8.0539, -34.8811),
        "São Paulo": (-23.5505, -46.6333),
        "Rio de Janeiro": (-22.9068, -43.1729),
        "Curitiba": (-25.4284, -49.2733),
        "Fortaleza": (-3.7319, -38.5267),
        "Belo Horizonte": (-19.9167, -43.9345),
        "Salvador": (-12.9714, -38.5014),
        "Porto Alegre": (-30.0346, -51.2177),
        "Brasília": (-15.7797, -47.9297),
        "Manaus": (-3.1019, -60.0250),
    }

    # Conjunto fechado de variáveis climáticas horárias aceitas pela
    # Forecast API da Open-Meteo
    VARIAVEIS_CLIMA = {
        "temperature_2m": "Temperatura do ar a 2m de altura (°C)",
        "relative_humidity_2m": "Umidade relativa do ar a 2m de altura (%)",
        "precipitation": "Precipitação (mm)",
        "wind_speed_10m": "Velocidade do vento a 10m de altura (km/h)",
    }

    # Conjunto fechado de poluentes aceitos pela Air Quality API da
    # Open-Meteo
    POLUENTES = {
        "pm10": "Partículas inaláveis PM10 (µg/m³)",
        "pm2_5": "Partículas finas PM2.5 (µg/m³)",
        "carbon_monoxide": "Monóxido de carbono (µg/m³)",
        "nitrogen_dioxide": "Dióxido de nitrogênio (µg/m³)",
        "ozone": "Ozônio (µg/m³)",
    }

    def __init__(self):
        self.base_url_clima = "https://api.open-meteo.com/v1/forecast"
        self.base_url_qualidade_ar = "https://air-quality-api.open-meteo.com/v1/air-quality"
        self.mongo_uri = os.getenv("MONGODB_URI")
        self.client = MongoClient(self.mongo_uri, server_api=ServerApi("1"))

    def close(self) -> None:
        """Encerra a conexão com o MongoDB."""
        self.client.close()

    def clima(
        self,
        cidade: str,
        variaveis: list[str] | None = None,
        dias_previsao: int = 1,
    ) -> dict:
        """
        Busca, na Forecast API da Open-Meteo, a série horária de uma ou
        mais variáveis climáticas para uma cidade.

        Atributos:
            cidade: nome da cidade a ser consultada (ver `Extract.CIDADES`)
            variaveis: lista de variáveis climáticas horárias a retornar
                (ver `Extract.VARIAVEIS_CLIMA`); se None, busca todas
            dias_previsao: quantidade de dias de previsão, de 1 a 7
        """
        if cidade not in self.CIDADES:
            raise ValueError(f"Cidade não suportada: {cidade}")

        if variaveis is None:
            variaveis = list(self.VARIAVEIS_CLIMA.keys())

        for variavel in variaveis:
            if variavel not in self.VARIAVEIS_CLIMA:
                raise ValueError(f"Variável climática inválida: {variavel}")

        latitude, longitude = self.CIDADES[cidade]
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": ",".join(variaveis),
            "forecast_days": dias_previsao,
            "timezone": "auto",
        }

        response = requests.get(self.base_url_clima, params=params)
        response.raise_for_status()

        data = response.json()
        data["cidade"] = cidade

        print(f"Dados de clima extraídos com sucesso da Open-Meteo para {cidade}!")
        return data

    def qualidade_ar(
        self,
        cidade: str,
        poluentes: list[str] | None = None,
        dias_previsao: int = 1,
    ) -> dict:
        """
        Busca, na Air Quality API da Open-Meteo, a série horária de
        concentração de um ou mais poluentes para uma cidade.

        Atributos:
            cidade: nome da cidade a ser consultada (ver `Extract.CIDADES`)
            poluentes: lista de poluentes a retornar (ver `Extract.POLUENTES`);
                se None, busca todos
            dias_previsao: quantidade de dias de previsão, de 1 a 7
        """
        if cidade not in self.CIDADES:
            raise ValueError(f"Cidade não suportada: {cidade}")

        if poluentes is None:
            poluentes = list(self.POLUENTES.keys())

        for poluente in poluentes:
            if poluente not in self.POLUENTES:
                raise ValueError(f"Poluente inválido: {poluente}")

        latitude, longitude = self.CIDADES[cidade]
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": ",".join(poluentes),
            "forecast_days": dias_previsao,
            "timezone": "auto",
        }

        response = requests.get(self.base_url_qualidade_ar, params=params)
        response.raise_for_status()

        data = response.json()
        data["cidade"] = cidade

        print(f"Dados de qualidade do ar extraídos com sucesso da Open-Meteo para {cidade}!")
        return data

    def extract_collection_from_mongo(self, db_name: str, collection_name: str) -> list[dict]:
        """
        Busca todos os documentos de uma coleção do MongoDB.

        Atributos:
            db_name: nome do banco de dados no MongoDB
            collection_name: nome da coleção a ser lida
        """
        collection = self.client[db_name][collection_name]
        documentos = list(collection.find())

        print(f"Dados lidos com sucesso da coleção '{collection_name}'!")
        return documentos
