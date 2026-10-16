"""
Teste local do flow do Prefect (flow_etl.py).

Substitui a Open-Meteo, o MongoDB Atlas e o NeonDB por dublês para
validar a ORQUESTRAÇÃO sem rede externa nem credenciais:

1. Execução com sucesso: todas as tasks terminam como "Completed", na
   ordem certa, e os dados chegam ao "NeonDB" (simulado com SQLite).
2. Execução com falha: se a API de clima cair, a task de extração é
   tentada de novo, as tasks dependentes não rodam e o flow termina
   como "Failed".

Roda num servidor temporário do Prefect (prefect_test_harness), então
não aparece na interface do Prefect da demonstração.
"""
import os
import sqlite3
import sys
from unittest import mock

os.environ["MONGODB_URI"] = "mongodb://fake-uri-para-teste"
os.environ["NEON_DB_URL"] = "postgresql://fake-uri-para-teste"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mongomock  # noqa: E402
import requests  # noqa: E402
from prefect.testing.utilities import prefect_test_harness  # noqa: E402

import flow_etl  # noqa: E402
from src.load import Load  # noqa: E402

FAKE_CLIMA_RESPONSE = {
    "latitude": -8.05,
    "longitude": -34.9,
    "timezone": "America/Recife",
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
        return dict(self._payload)


def fake_requests_get(url, params=None):
    if "air-quality" in url:
        return FakeResponse(FAKE_QUALIDADE_RESPONSE)
    return FakeResponse(FAKE_CLIMA_RESPONSE)


TEST_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "neon_fake_test.db")


def fake_load_neon(self, df, nome_tabela, schema="public"):
    """Simula o NeonDB gravando a tabela num SQLite local."""
    self.load_sqlite(df=df, nome_banco=TEST_DB, nome_tabela=nome_tabela)


def patches(requests_get):
    fake_client = mongomock.MongoClient("mongodb://fake-uri-para-teste")
    return [
        mock.patch("src.extract.MongoClient", return_value=fake_client),
        mock.patch("src.load.MongoClient", return_value=fake_client),
        mock.patch("src.extract.requests.get", side_effect=requests_get),
        mock.patch.object(Load, "load_neon", fake_load_neon),
    ]


def run_with(requests_get, **params):
    ativos = patches(requests_get)
    for p in ativos:
        p.start()
    try:
        return flow_etl.etl_smart_city(return_state=True, **params)
    finally:
        for p in reversed(ativos):
            p.stop()


def contar(tabela):
    conn = sqlite3.connect(TEST_DB)
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
    finally:
        conn.close()


def main():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    with prefect_test_harness():
        # Sem esperar entre novas tentativas, para o teste ser rápido.
        flow_etl.extrair_clima.retry_delay_seconds = 0
        flow_etl.extrair_qualidade_ar.retry_delay_seconds = 0

        # 1. Sucesso -------------------------------------------------------
        estado = run_with(fake_requests_get, cidade="Recife")
        assert estado.is_completed(), f"Flow deveria completar, terminou como {estado.name}"
        resumo = estado.result()
        n_esperado = len(FAKE_CLIMA_RESPONSE["hourly"]["time"])
        assert resumo == {
            "cidade": "Recife",
            "linhas_clima": n_esperado,
            "linhas_qualidade_ar": len(FAKE_QUALIDADE_RESPONSE["hourly"]["time"]),
        }, resumo
        assert contar("clima") == n_esperado
        assert contar("qualidade_ar") == n_esperado
        print(f"OK: flow completou e carregou {resumo['linhas_clima']} + {resumo['linhas_qualidade_ar']} linhas")

        # 2. Falha na API de clima ----------------------------------------
        chamadas_clima = []

        def api_clima_fora(url, params=None):
            if "air-quality" in url:
                return fake_requests_get(url, params)
            chamadas_clima.append(url)
            raise requests.ConnectionError("Open-Meteo indisponível (simulado)")

        estado = run_with(api_clima_fora, cidade="Recife")
        assert estado.is_failed(), f"Flow deveria falhar, terminou como {estado.name}"
        assert len(chamadas_clima) == 1 + flow_etl.extrair_clima.retries, chamadas_clima
        print(f"OK: falha na API detectada, {len(chamadas_clima)} tentativas, flow terminou como '{estado.name}'")

        # 3. Parâmetro inválido -------------------------------------------
        estado = run_with(fake_requests_get, cidade="Cidade Que Não Existe")
        assert estado.is_failed()
        print("OK: cidade inválida faz o flow falhar antes de chamar a API")

    os.remove(TEST_DB)
    print("\nTODOS OS TESTES DO FLOW PASSARAM!")


if __name__ == "__main__":
    main()
