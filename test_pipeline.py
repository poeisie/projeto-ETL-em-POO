"""
Script de teste local: substitui as chamadas reais à Open-Meteo e ao
MongoDB por dublês (fakes), para validar a LÓGICA do pipeline
(validação de parâmetros, montagem do DataFrame, gravação no SQLite)
sem depender de rede externa nem de um MongoDB real.

Não faz parte do pipeline entregue — é só uma checagem de sanidade.
"""
import os
import sqlite3
import sys
from unittest import mock

os.environ["MONGODB_URI"] = "mongodb://fake-uri-para-teste"

import mongomock  # noqa: E402

sys.path.insert(0, os.path.dirname(__file__))

# --- fakes -------------------------------------------------------------

FAKE_CLIMA_RESPONSE = {
    "latitude": -8.05,
    "longitude": -34.9,
    "timezone": "America/Recife",
    "hourly_units": {"time": "iso8601", "temperature_2m": "°C"},
    "hourly": {
        "time": ["2026-09-10T00:00", "2026-09-10T01:00", "2026-09-10T02:00"],
        "temperature_2m": [24.1, 23.8, 23.5],
        "relative_humidity_2m": [88, 89, 90],
        "precipitation": [0.0, 0.0, 0.2],
        "wind_speed_10m": [11.2, 10.8, 9.9],
    },
}

FAKE_QUALIDADE_RESPONSE = {
    "latitude": -8.05,
    "longitude": -34.9,
    "timezone": "America/Recife",
    "hourly_units": {"time": "iso8601", "pm10": "µg/m³"},
    "hourly": {
        "time": ["2026-09-10T00:00", "2026-09-10T01:00", "2026-09-10T02:00"],
        "pm10": [12.3, 11.9, 10.5],
        "pm2_5": [6.1, 5.8, 5.2],
        "carbon_monoxide": [180.0, 175.0, 170.0],
        "nitrogen_dioxide": [8.4, 8.1, 7.9],
        "ozone": [40.2, 41.0, 39.5],
    },
}


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        # devolve uma cópia para simular uma nova resposta HTTP a cada chamada
        return dict(self._payload)


def fake_requests_get(url, params=None):
    if "air-quality" in url:
        return FakeResponse(FAKE_QUALIDADE_RESPONSE)
    return FakeResponse(FAKE_CLIMA_RESPONSE)


# --- teste ---------------------------------------------------------------

# Em produção, várias instâncias de MongoClient com a mesma
# MONGODB_URI apontam para o mesmo servidor Mongo real e por isso
# enxergam os mesmos dados. O mongomock, por padrão, isola o estado por
# instância — então, só para este teste local, forçamos todas as
# instâncias de MongoClient a devolverem o MESMO cliente fake, para que
# Extract e Load "conversem" com o mesmo banco em memória.
_fake_client = mongomock.MongoClient("mongodb://fake-uri-para-teste")

with mock.patch("pymongo.MongoClient", return_value=_fake_client), \
     mock.patch("requests.get", side_effect=fake_requests_get):

    from src.extract import Extract
    from src.load import Load
    from src.transform import Transform

    ext = Extract()
    transformer = Transform()

    # validação de cidade inválida deve levantar ValueError
    try:
        ext.clima(cidade="Cidade Que Não Existe")
        raise AssertionError("Deveria ter levantado ValueError para cidade inválida")
    except ValueError:
        print("OK: ValueError levantado corretamente para cidade inválida")

    # validação de variável inválida deve levantar ValueError
    try:
        ext.clima(cidade="Recife", variaveis=["variavel_invalida"])
        raise AssertionError("Deveria ter levantado ValueError para variável inválida")
    except ValueError:
        print("OK: ValueError levantado corretamente para variável climática inválida")

    cidade = "Recife"

    clima_bruto = ext.clima(cidade=cidade)
    assert clima_bruto["cidade"] == cidade
    Load().load_mongo(clima_bruto, "SmartCity", "Clima")
    print("OK: clima bruto inserido no Mongo (fake)")

    qualidade_bruta = ext.qualidade_ar(cidade=cidade)
    Load().load_mongo(qualidade_bruta, "SmartCity", "QualidadeAr")
    print("OK: qualidade do ar bruta inserida no Mongo (fake)")

    clima_docs = ext.extract_collection_from_mongo("SmartCity", "Clima")
    assert len(clima_docs) == 1
    df_clima = transformer.transform_clima(clima_docs[-1])
    print(df_clima)
    assert list(df_clima.columns) == [
        "cidade", "data_hora", "temperature_2m",
        "relative_humidity_2m", "precipitation", "wind_speed_10m",
    ]
    assert len(df_clima) == 3
    assert str(df_clima["data_hora"].dtype).startswith("datetime64")

    qualidade_docs = ext.extract_collection_from_mongo("SmartCity", "QualidadeAr")
    df_qualidade = transformer.transform_qualidade_ar(qualidade_docs[-1])
    print(df_qualidade)
    assert len(df_qualidade) == 3

    ld = Load()
    ld.load_sqlite(df=df_clima, nome_banco="/tmp/smart_city_test.db", nome_tabela="clima")
    ld.load_sqlite(df=df_qualidade, nome_banco="/tmp/smart_city_test.db", nome_tabela="qualidade_ar")
    ld.close()

    ext.close()

# confere se as tabelas realmente chegaram no SQLite
conn = sqlite3.connect("/tmp/smart_city_test.db")
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM clima")
n_clima = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM qualidade_ar")
n_qualidade = cur.fetchone()[0]
conn.close()

assert n_clima == 3
assert n_qualidade == 3

print(f"\nOK: {n_clima} linhas na tabela 'clima' e {n_qualidade} linhas na tabela 'qualidade_ar' no SQLite")
print("\nTODOS OS TESTES PASSARAM!")
