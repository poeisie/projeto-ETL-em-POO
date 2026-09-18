import pandas as pd


class Transform:
    """
    Responsável por transformar os dados brutos extraídos das APIs da
    Open-Meteo, deixando-os prontos para carga em um banco relacional
    (SQLite).
    """

    def __init__(self):
        pass

    def transform_clima(self, data: dict) -> pd.DataFrame:
        """
        Converte o resultado bruto da Forecast API da Open-Meteo em um
        DataFrame com uma linha por hora, pronto para carga no SQLite.

        Atributos:
            data: dicionário no formato retornado pela Open-Meteo (o
                mesmo salvo por `Load.load_mongo`), contendo a chave
                "hourly" com as séries horárias e a chave "cidade"
                adicionada por `Extract.clima`
        """
        hourly = data["hourly"]

        df = pd.DataFrame(hourly)
        df = df.rename(columns={"time": "data_hora"})
        df["data_hora"] = pd.to_datetime(df["data_hora"])
        df["cidade"] = data.get("cidade", "desconhecida")

        colunas = ["cidade", "data_hora"] + [
            coluna for coluna in df.columns if coluna not in ("cidade", "data_hora")
        ]
        df = df[colunas]

        print("Dados de clima transformados com sucesso!")
        return df

    def transform_qualidade_ar(self, data: dict) -> pd.DataFrame:
        """
        Converte o resultado bruto da Air Quality API da Open-Meteo em
        um DataFrame com uma linha por hora, pronto para carga no
        SQLite.

        Atributos:
            data: dicionário no formato retornado pela Open-Meteo (o
                mesmo salvo por `Load.load_mongo`), contendo a chave
                "hourly" com as séries horárias e a chave "cidade"
                adicionada por `Extract.qualidade_ar`
        """
        hourly = data["hourly"]

        df = pd.DataFrame(hourly)
        df = df.rename(columns={"time": "data_hora"})
        df["data_hora"] = pd.to_datetime(df["data_hora"])
        df["cidade"] = data.get("cidade", "desconhecida")

        colunas = ["cidade", "data_hora"] + [
            coluna for coluna in df.columns if coluna not in ("cidade", "data_hora")
        ]
        df = df[colunas]

        print("Dados de qualidade do ar transformados com sucesso!")
        return df
