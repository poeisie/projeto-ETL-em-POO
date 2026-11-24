"""
Acesso somente leitura ao banco NeonDB (camada prata da pipeline).

Usado pelo servidor MCP (servidor.py) e pela pagina "Assistente" do dashboard.
"""
from datetime import date, datetime
from decimal import Decimal

import psycopg2


def _para_json(valor):
    """Converte tipos do PostgreSQL em tipos simples (numero, texto)."""
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    return valor


class BancoNeon:
    def __init__(self, url_conexao):
        # Guarda a URL de conexao (vem do arquivo .env)
        self.url_conexao = url_conexao

    def _conectar(self):
        # Abre uma conexao nova com o banco
        if not self.url_conexao:
            raise ValueError("NEON_DB_URL (ou NEON) nao configurada no arquivo .env.")
        conexao = psycopg2.connect(self.url_conexao, connect_timeout=15)
        # Modo somente leitura: o banco recusa INSERT, UPDATE, DELETE, DROP...
        conexao.set_session(readonly=True)
        return conexao

    def _executar(self, sql, parametros=None):
        """Executa um SELECT e devolve uma lista de dicionarios {coluna: valor}."""
        conexao = self._conectar()
        try:
            with conexao.cursor() as cursor:
                cursor.execute(sql, parametros)
                colunas = [coluna[0] for coluna in cursor.description]
                linhas = cursor.fetchall()
        finally:
            conexao.close()
        return [
            {coluna: _para_json(valor) for coluna, valor in zip(colunas, linha)}
            for linha in linhas
        ]

    def consultar(self, sql, parametros=None):
        """Executa um SELECT e devolve uma lista de dicionarios."""
        return self._executar(sql, parametros)

    def listar_tabelas(self):
        """Retorna o nome de todas as tabelas do schema public."""
        sql = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """
        # Usa _executar (e nao consultar) para que um limite de linhas,
        # como o de BancoComLimite, nunca esconda tabelas.
        return [linha["table_name"] for linha in self._executar(sql)]

    def descrever_tabela(self, tabela):
        """Retorna as colunas e os tipos de uma tabela."""
        # O %s evita SQL Injection: o psycopg2 trata o valor com seguranca
        linhas = self._executar(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
            """,
            (tabela,),
        )
        return [{"coluna": l["column_name"], "tipo": l["data_type"]} for l in linhas]

    def esquema_completo(self):
        """Monta um texto com todas as tabelas e colunas (usado pelo GPT)."""
        texto = ""
        for tabela in self.listar_tabelas():
            colunas = self.descrever_tabela(tabela)
            lista = ", ".join(f"{c['coluna']} ({c['tipo']})" for c in colunas)
            texto += f"- {tabela}: {lista}\n"
        return texto

    def contar_linhas(self, tabela):
        """Conta quantas linhas uma tabela possui."""
        # Nome de tabela nao pode ir no %s, entao validamos com a lista de tabelas reais.
        if tabela not in self.listar_tabelas():
            raise ValueError(f"Tabela '{tabela}' nao existe")
        return self._executar(f'SELECT COUNT(*) AS total FROM "{tabela}"')[0]["total"]


class BancoComLimite(BancoNeon):
    """Exercicio 3: igual ao BancoNeon, mas consultar devolve no maximo `limite` linhas."""

    def __init__(self, url_conexao, limite=10):
        super().__init__(url_conexao)  # reaproveita o construtor do pai
        self.limite = limite

    def consultar(self, sql, parametros=None):
        linhas = super().consultar(sql, parametros)  # reaproveita o metodo do pai
        return linhas[: self.limite]
