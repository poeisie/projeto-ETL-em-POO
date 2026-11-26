"""
Servidor MCP (FastMCP) que consulta o banco NeonDB da pipeline ETL Smart City
e usa o GPT para responder perguntas em portugues.

Uso:
    python servidor.py                      # transporte stdio (Claude Desktop, VS Code)
    fastmcp dev inspector servidor.py       # interface visual para testar as ferramentas
    python cliente_teste.py                 # cliente de teste pelo terminal
"""
import os
import sys

# Permite rodar o servidor a partir de qualquer pasta (ex.: Claude Desktop).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastmcp import FastMCP  # noqa: E402

from src.assistente import AssistenteGPT  # noqa: E402
from src.banco import BancoComLimite  # noqa: E402
from src.config import GPT_API_KEY, GPT_BASE_URL, MODELO, NEON_DB_URL  # noqa: E402

# Limite de referencia da OMS (2021) para PM2.5 em 24 horas, em ug/m3.
LIMITE_OMS_PM25 = 15.0

# 1) Cria os objetos que fazem o trabalho de verdade.
#    Exercicio 3: BancoComLimite no lugar de BancoNeon (no maximo 10 linhas por consulta).
banco = BancoComLimite(NEON_DB_URL)
#    Exercicio 2: o modelo vem do .env (variavel MODELO), com gpt-6-luna como padrao.
gpt = AssistenteGPT(GPT_API_KEY, MODELO, base_url=GPT_BASE_URL)

# 2) Cria o servidor MCP
mcp = FastMCP("Smart City - Neon + GPT")


# 3) Cada funcao com @mcp.tool vira uma ferramenta disponivel para a IA.
#    A docstring e a descricao que a IA le para saber quando usar a ferramenta.

@mcp.tool
def listar_tabelas() -> list[str]:
    """Lista as tabelas existentes no banco de dados."""
    return banco.listar_tabelas()


@mcp.tool
def descrever_tabela(tabela: str) -> list[dict]:
    """Mostra as colunas e os tipos de uma tabela."""
    return banco.descrever_tabela(tabela)


@mcp.tool
def contar_linhas(tabela: str) -> int:
    """Conta quantas linhas uma tabela possui."""
    return banco.contar_linhas(tabela)


@mcp.tool
def executar_select(sql: str) -> list[dict]:
    """Executa um comando SELECT no banco e devolve as linhas (no maximo 10)."""
    return banco.consultar(sql)


@mcp.tool
def perguntar_ao_banco(pergunta: str) -> dict:
    """Responde uma pergunta em portugues: o GPT gera o SQL, o banco executa e o GPT explica."""
    return gpt.responder(pergunta, banco)


# --- Ferramentas do produto de dados (Desafio da Disciplina) -----------------

@mcp.tool
def cidades_disponiveis() -> list[str]:
    """Lista as cidades que ja tem dados de clima ou de qualidade do ar no banco."""
    linhas = banco._executar(
        "SELECT cidade FROM clima UNION SELECT cidade FROM qualidade_ar ORDER BY cidade"
    )
    return [linha["cidade"] for linha in linhas]


@mcp.tool
def resumo_cidade(cidade: str) -> dict:
    """Resumo do clima e da qualidade do ar de uma cidade: medias, extremos,
    chuva acumulada e quantas horas o PM2.5 passou do limite da OMS."""
    clima = banco.consultar(
        """
        SELECT MIN(data_hora) AS inicio, MAX(data_hora) AS fim,
               ROUND(AVG(temperature_2m)::numeric, 1) AS temperatura_media,
               MAX(temperature_2m) AS temperatura_maxima,
               MIN(temperature_2m) AS temperatura_minima,
               ROUND(AVG(relative_humidity_2m)::numeric, 0) AS umidade_media,
               ROUND(SUM(precipitation)::numeric, 1) AS chuva_acumulada_mm,
               ROUND(AVG(wind_speed_10m)::numeric, 1) AS vento_medio_kmh
        FROM clima WHERE cidade = %s
        """,
        (cidade,),
    )[0]
    ar = banco.consultar(
        """
        SELECT ROUND(AVG(pm2_5)::numeric, 1) AS pm25_medio,
               MAX(pm2_5) AS pm25_maximo,
               ROUND(AVG(pm10)::numeric, 1) AS pm10_medio,
               ROUND(AVG(ozone)::numeric, 1) AS ozonio_medio,
               COUNT(*) FILTER (WHERE pm2_5 > %s) AS horas_pm25_acima_oms
        FROM qualidade_ar WHERE cidade = %s
        """,
        (LIMITE_OMS_PM25, cidade),
    )[0]
    if clima["inicio"] is None and ar["pm25_medio"] is None:
        raise ValueError(
            f"Nao ha dados para '{cidade}'. Use cidades_disponiveis para ver as opcoes."
        )
    return {"cidade": cidade, "clima": clima, "qualidade_ar": ar, "limite_oms_pm25": LIMITE_OMS_PM25}


@mcp.tool
def ranking_qualidade_ar() -> list[dict]:
    """Ranking das cidades pela media de PM2.5, da pior para a melhor qualidade do ar."""
    return banco.consultar(
        """
        SELECT cidade,
               ROUND(AVG(pm2_5)::numeric, 1) AS pm25_medio,
               ROUND(AVG(pm10)::numeric, 1) AS pm10_medio,
               COUNT(*) FILTER (WHERE pm2_5 > %s) AS horas_pm25_acima_oms
        FROM qualidade_ar
        GROUP BY cidade
        ORDER BY pm25_medio DESC NULLS LAST
        """,
        (LIMITE_OMS_PM25,),
    )


if __name__ == "__main__":
    mcp.run()  # padrao: transporte stdio
