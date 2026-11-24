"""
Teste local do servidor MCP, sem NeonDB e sem chave do GPT: o banco e o GPT
sao substituidos por dubles. Uso: python test_mcp.py
"""
import asyncio
import importlib
import os
from unittest import mock

os.environ.pop("MODELO", None)

from fastmcp import Client  # noqa: E402
from fastmcp.exceptions import ToolError  # noqa: E402

import servidor  # noqa: E402
from src import config  # noqa: E402
from src.banco import BancoComLimite, BancoNeon  # noqa: E402

TABELAS = ["clima", "qualidade_ar"]
LINHAS = {"clima": 240, "qualidade_ar": 240}


def banco_falso(sql, parametros=None):
    """Responde as consultas que o servidor faz, sem banco real."""
    if "information_schema.tables" in sql:
        return [{"table_name": t} for t in TABELAS]
    if "information_schema.columns" in sql:
        return [{"column_name": "cidade", "data_type": "text"}]
    if "COUNT(*) AS total" in sql:
        tabela = sql.split('FROM "')[1].rstrip('"')
        return [{"total": LINHAS[tabela]}]
    if "FROM clima WHERE cidade" in sql:
        tem = parametros[0] == "Recife"
        return [{"inicio": "2026-11-24T00:00:00" if tem else None, "temperatura_media": 27.1}]
    if "FROM qualidade_ar WHERE cidade" in sql:
        tem = parametros[1] == "Recife"
        return [{"pm25_medio": 8.2 if tem else None, "horas_pm25_acima_oms": 0}]
    return [{"n": i} for i in range(25)]


def teste_ferramentas(cliente):
    nomes = {f.name for f in asyncio.run(_listar(cliente))}
    esperadas = {
        "listar_tabelas", "descrever_tabela", "contar_linhas", "executar_select",
        "perguntar_ao_banco", "cidades_disponiveis", "resumo_cidade", "ranking_qualidade_ar",
    }
    assert esperadas <= nomes, esperadas - nomes
    print("ok  ferramentas registradas:", sorted(nomes))


async def _listar(cliente):
    async with cliente:
        return await cliente.list_tools()


async def _chamar(nome, args):
    async with Client(servidor.mcp) as cliente:
        return await cliente.call_tool(nome, args)


def main():
    with mock.patch.object(servidor.banco, "_executar", side_effect=banco_falso):
        teste_ferramentas(Client(servidor.mcp))

        # Exercicio 1: contar_linhas
        assert asyncio.run(_chamar("contar_linhas", {"tabela": "clima"})).data == 240
        try:
            asyncio.run(_chamar("contar_linhas", {"tabela": "clima; DROP TABLE clima"}))
            raise AssertionError("contar_linhas aceitou uma tabela inexistente")
        except ToolError as e:
            assert "não existe" in str(e) or "nao existe" in str(e)
        print("ok  exercicio 1: contar_linhas conta e recusa tabela inexistente")

        # Exercicio 3: BancoComLimite (servidor usa no maximo 10 linhas)
        assert isinstance(servidor.banco, BancoComLimite)
        assert isinstance(servidor.banco, BancoNeon)
        linhas = asyncio.run(_chamar("executar_select", {"sql": "SELECT * FROM clima"})).data
        assert len(linhas) == 10, len(linhas)
        print("ok  exercicio 3: BancoComLimite devolve no maximo 10 linhas")

        # Produto: resumo da cidade
        resumo = asyncio.run(_chamar("resumo_cidade", {"cidade": "Recife"})).data
        assert resumo["clima"]["temperatura_media"] == 27.1
        try:
            asyncio.run(_chamar("resumo_cidade", {"cidade": "Gotham"}))
            raise AssertionError("resumo_cidade aceitou cidade sem dados")
        except ToolError:
            pass
        print("ok  resumo_cidade responde e recusa cidade sem dados")

        # perguntar_ao_banco com GPT falso
        respostas = iter(["```sql\nSELECT COUNT(*) FROM clima\n```", "A tabela clima tem 240 linhas."])
        with mock.patch.object(servidor.gpt, "perguntar", side_effect=lambda *a: next(respostas)):
            r = asyncio.run(_chamar("perguntar_ao_banco", {"pergunta": "Quantas linhas tem clima?"})).data
        assert r["sql"] == "SELECT COUNT(*) FROM clima", r["sql"]
        assert r["resposta"] == "A tabela clima tem 240 linhas."
        print("ok  perguntar_ao_banco: gera SQL, consulta e explica")

    # Exercicio 2: MODELO vindo do .env, com gpt-6-luna como padrao
    with mock.patch("dotenv.load_dotenv"):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MODELO", None)
            assert importlib.reload(config).MODELO == "gpt-6-luna"
        with mock.patch.dict(os.environ, {"MODELO": "outro-modelo"}):
            assert importlib.reload(config).MODELO == "outro-modelo"
    importlib.reload(config)
    print("ok  exercicio 2: MODELO lido do ambiente, padrao gpt-6-luna")

    # Conexao somente leitura e sempre fechada
    conexao = mock.MagicMock()
    conexao.cursor.return_value.__enter__.return_value.description = [("x",)]
    conexao.cursor.return_value.__enter__.return_value.fetchall.return_value = [(1,)]
    with mock.patch("src.banco.psycopg2.connect", return_value=conexao):
        assert BancoNeon("postgresql://falso").consultar("SELECT 1 AS x") == [{"x": 1}]
    conexao.set_session.assert_called_once_with(readonly=True)
    conexao.close.assert_called_once()
    print("ok  conexao em modo somente leitura e fechada apos a consulta")

    print("\nTodos os testes passaram.")


if __name__ == "__main__":
    main()
