import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
# NEON e o nome usado na Aula 10; NEON_DB_URL e o nome usado pelo restante do projeto.
NEON_DB_URL = os.getenv("NEON_DB_URL") or os.getenv("NEON")
DB_MONGO = "SmartCity"

# --- Servidor MCP / assistente GPT (Aula 10) ---------------------------------
# Chave da API do GPT (ou de um servico compativel com a biblioteca openai).
GPT_API_KEY = os.getenv("GPT") or os.getenv("OPENAI_API_KEY")
# Endereco de um servico compativel com a OpenAI (opcional). Vazio = OpenAI.
GPT_BASE_URL = os.getenv("GPT_BASE_URL") or None
# Exercicio 2: modelo lido do .env, com gpt-6-luna como padrao.
MODELO = os.getenv("MODELO", "gpt-6-luna")
