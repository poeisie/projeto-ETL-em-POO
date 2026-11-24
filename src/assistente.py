"""
Assistente que usa o GPT para transformar perguntas em portugues em SQL
e para explicar o resultado das consultas.
"""
from openai import OpenAI

CONTEXTO_DADOS = (
    "Os dados vem da Open-Meteo e foram tratados pela pipeline ETL Smart City. "
    "A tabela clima tem a serie horaria de temperatura (temperature_2m, em C), "
    "umidade (relative_humidity_2m, %), chuva (precipitation, mm) e vento "
    "(wind_speed_10m, km/h). A tabela qualidade_ar tem a serie horaria de "
    "poluentes em ug/m3 (pm10, pm2_5, carbon_monoxide, nitrogen_dioxide, ozone). "
    "As duas tabelas se ligam por cidade e data_hora. Os nomes de cidade são "
    "gravados com acento (ex.: 'São Paulo', 'Brasília')."
)


class AssistenteGPT:
    def __init__(self, chave_api, modelo="gpt-6-luna", base_url=None):
        self.chave_api = chave_api
        self.modelo = modelo
        self.base_url = base_url  # para servicos compativeis com a OpenAI
        self._cliente = None

    @property
    def cliente(self):
        # O cliente da OpenAI so e criado no primeiro uso. Assim o servidor MCP
        # sobe mesmo sem chave, e as ferramentas que so usam o banco funcionam.
        if self._cliente is None:
            if not self.chave_api:
                raise ValueError("Chave do GPT nao configurada (variavel GPT no .env).")
            self._cliente = OpenAI(api_key=self.chave_api, base_url=self.base_url)
        return self._cliente

    def perguntar(self, instrucao, pergunta):
        """Envia uma pergunta ao GPT e devolve o texto da resposta."""
        resposta = self.cliente.chat.completions.create(
            model=self.modelo,
            messages=[
                {"role": "system", "content": instrucao},
                {"role": "user", "content": pergunta},
            ],
        )
        return resposta.choices[0].message.content.strip()

    def gerar_sql(self, pergunta, esquema):
        """Transforma uma pergunta em portugues em um comando SELECT."""
        instrucao = (
            "Voce e especialista em PostgreSQL. "
            "Com base nas tabelas abaixo, escreva UM comando SELECT que responda a pergunta. "
            "Responda somente com o SQL, sem explicacoes e sem ```.\n\n"
            f"Contexto: {CONTEXTO_DADOS}\n\n"
            f"Tabelas:\n{esquema}"
        )
        sql = self.perguntar(instrucao, pergunta)
        # Remove ``` caso o modelo coloque mesmo assim
        return sql.replace("```sql", "").replace("```", "").strip()

    def explicar_resultado(self, pergunta, dados):
        """Escreve uma resposta amigavel a partir dos dados do banco."""
        instrucao = (
            "Responda a pergunta do usuario em portugues, de forma curta, "
            "usando apenas os dados fornecidos."
        )
        return self.perguntar(instrucao, f"Pergunta: {pergunta}\nDados: {dados}")

    def responder(self, pergunta, banco):
        """Fluxo completo: o GPT gera o SQL, o banco executa e o GPT explica."""
        sql = self.gerar_sql(pergunta, banco.esquema_completo())
        dados = banco.consultar(sql)
        resposta = self.explicar_resultado(pergunta, dados)
        return {"sql": sql, "dados": dados, "resposta": resposta}
