# ETL Smart City

## Equipe

- Caliel Feijo
- Giulia Ferreira
- Joana Farias
- Juliana Comparoto
- Paulo Marrocos
- Pedro Vinicius
- Sarah Cyrne
- Vinicius Gabriel

Pipeline de ETL desenvolvido em Python com orientacao a objetos para coletar dados de clima e qualidade do ar, armazenar os dados brutos no MongoDB Atlas e carregar os dados transformados no NeonDB.

> Fluxo obrigatorio da entrega: **API -> MongoDB Atlas -> Transformacao -> NeonDB**

## Visao geral

| Etapa | Tecnologia | Resultado |
| --- | --- | --- |
| Extracao | Open-Meteo API | Dados horarios de clima e qualidade do ar |
| Armazenamento bruto | MongoDB Atlas | Colecoes `SmartCity.Clima` e `SmartCity.QualidadeAr` |
| Transformacao | Python + pandas | DataFrames prontos para carga relacional |
| Armazenamento final | NeonDB | Tabelas `clima` e `qualidade_ar` |

## Fluxo da ETL

```text
Open-Meteo
    |
    v
Extract.clima() / Extract.qualidade_ar()
    |
    v
MongoDB Atlas
    |  dados brutos
    v
Transform.transform_clima() / transform_qualidade_ar()
    |
    v
NeonDB (PostgreSQL)
```

## Organizacao do projeto

```text
.
|-- src/
|   |-- config.py        # Centralizador de configuracoes e leitura do .env
|   |-- extract.py       # Extracao das APIs e leitura do MongoDB Atlas
|   |-- transform.py     # Transformacao dos documentos em DataFrames
|   |-- load.py          # Carga no MongoDB Atlas e no NeonDB
|   |-- dashboard_data.py # Consultas otimizadas e aggregations do NeonDB
|   |-- banco.py         # BancoNeon / BancoComLimite: acesso somente leitura ao NeonDB
|   |-- assistente.py    # AssistenteGPT: pergunta em portugues -> SQL -> resposta
|   `-- style.css        # Design System e estilizacao CSS profissional
|-- dashboard/
|   `-- app.py           # Dashboard analitico interativo em Streamlit
|-- flow_etl.py          # Orquestracao da pipeline com Prefect (tasks + flow)
|-- run_etl.py           # Execucao sequencial da pipeline, sem orquestrador
|-- test_pipeline.py     # Teste local com APIs e MongoDB simulados
|-- test_flow.py         # Teste local do flow do Prefect (sucesso e falha)
|-- servidor.py          # Servidor MCP (FastMCP) com o banco do projeto
|-- cliente_teste.py     # Cliente de teste do servidor MCP
|-- test_mcp.py          # Teste local do servidor MCP, sem banco e sem GPT
|-- requirements.txt     # Dependencias Python
`-- README.md
```

As classes principais seguem o padrao `Extract`, `Transform` e `Load`.

## Para executar o projeto

Os itens abaixo sao condicoes tecnicas para executar a ETL em nuvem. Eles nao representam requisitos adicionais da atividade:

- Python 3.10 ou superior
- Conta no MongoDB Atlas com um cluster acessivel
- Conta no NeonDB com um banco PostgreSQL criado
- Acesso de rede configurado no MongoDB Atlas para o seu IP

## Instalacao

### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Linux ou macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuracao

Crie um arquivo `.env` na raiz do projeto. Nunca publique esse arquivo:

```dotenv
MONGODB_URI=mongodb+srv://<usuario>:<senha>@<cluster>.mongodb.net/?appName=<nome>
NEON_DB_URL=postgresql://<usuario>:<senha>@<host>/<database>?sslmode=require
```

O `.env` esta incluido no `.gitignore`. Se a senha tiver caracteres especiais, use URL encoding na string de conexao.

## Execucao

Com as variaveis configuradas, execute o fluxo completo:

```powershell
python run_etl.py
```

O programa executa quatro etapas:

1. Consulta a Open-Meteo para a cidade configurada.
2. Grava as respostas brutas nas colecoes do MongoDB Atlas.
3. Le os documentos do Atlas e transforma os dados com pandas.
4. Recria e carrega as tabelas transformadas no NeonDB.

Durante a demonstracao, verifique:

- MongoDB Atlas: banco `SmartCity`, colecoes `Clima` e `QualidadeAr`.
- NeonDB: tabelas `public.clima` e `public.qualidade_ar`.

## Orquestracao com Prefect

O arquivo `flow_etl.py` transforma a pipeline em um fluxo orquestrado pelo [Prefect](https://www.prefect.io/). Cada etapa e uma task e o flow `ETL Smart City` organiza a execucao respeitando as dependencias:

```text
              +--> Extrair clima ----------> Salvar no MongoDB --> Ler do MongoDB --> Transformar clima ----------> Carregar no NeonDB (clima)
 ETL Smart ---|
   City       +--> Extrair qualidade do ar -> Salvar no MongoDB --> Ler do MongoDB --> Transformar qualidade do ar -> Carregar no NeonDB (qualidade_ar)
```

| Task | Etapa | Novas tentativas |
| --- | --- | --- |
| Extrair clima / Extrair qualidade do ar | Chamada a Open-Meteo | 3 (a cada 10 s) |
| Salvar dados brutos no MongoDB Atlas | Grava a resposta bruta | 2 (a cada 5 s) |
| Ler dados brutos do MongoDB Atlas | Le o documento mais recente | 2 (a cada 5 s) |
| Transformar clima / qualidade do ar | Gera o DataFrame com pandas | - |
| Carregar no NeonDB | Recria e carrega a tabela | 2 (a cada 10 s) |

- Os ramos de clima e de qualidade do ar sao independentes e rodam em paralelo.
- Dentro de cada ramo, uma task so comeca quando a anterior termina com sucesso. A leitura do MongoDB depende explicitamente da gravacao (`wait_for`), ja que nao recebe dados dela.
- Se uma task falhar depois das novas tentativas, as tasks seguintes daquele ramo nao rodam (ficam como `NotReady`) e o flow termina como `Failed` com o erro original, o que facilita identificar onde a pipeline quebrou.
- Cada task registra no log do Prefect o que fez (quantidade de registros extraidos, linhas carregadas etc.).

### Acompanhando as execucoes na interface do Prefect

1. Em um terminal, suba o servidor local do Prefect:

   ```bash
   prefect server start
   ```

   A interface fica em http://127.0.0.1:4200.

2. Em outro terminal (com o ambiente virtual ativo), aponte para esse servidor e execute o flow:

   ```bash
   prefect config set PREFECT_API_URL=http://127.0.0.1:4200/api
   python flow_etl.py
   ```

   Para outra cidade ou mais dias de previsao: `python flow_etl.py --cidade Fortaleza --dias 3`.

3. Na interface, abra **Runs** para ver a execucao do flow, o grafo de tasks com o estado de cada uma (`Completed`, `Failed`, `NotReady`), a duracao e os logs.

### Execucao agendada (opcional)

Para automatizar a execucao, o flow pode ficar disponivel como deployment agendado de hora em hora:

```bash
python flow_etl.py --serve
```

O deployment `etl-smart-city-horaria` aparece em **Deployments** na interface. Por la tambem da para disparar uma execucao manual com **Quick run**. O processo precisa continuar aberto para as execucoes acontecerem; encerre com `Ctrl+C`.

### Testando o flow sem credenciais

```bash
python test_flow.py
```

O teste usa um servidor temporario do Prefect e dubles da Open-Meteo, do MongoDB e do NeonDB para verificar tres cenarios: execucao completa com sucesso, falha da API de clima (com as novas tentativas e o flow terminando como `Failed`) e cidade invalida.

## Validacao local

O teste local nao depende da API, do MongoDB Atlas ou do NeonDB. Ele usa respostas simuladas, `mongomock` para o MongoDB e SQLite apenas como apoio para conferir a persistencia:

```powershell
python test_pipeline.py
```

Esse teste valida a extracao, as validacoes de entrada, a gravacao e leitura do MongoDB simulado, a transformacao em DataFrames e a disponibilidade do metodo de carga no NeonDB.

## Melhorias de Engenharia de Dados (Pipeline PNADC Reference)

Em conformidade com as diretrizes da disciplina:

1. **Centralizacao de Configuracao (`src/config.py`)**:
   - As variaveis de ambiente (`MONGODB_URI`, `NEON_DB_URL`, `DB_MONGO`) sao carregadas uma unica vez pelo `src/config.py` via `python-dotenv`.
   - Nenhum outro modulo do pipeline realiza chamadas repetidas a `os.getenv`.

2. **Rastreabilidade e Versionamento Temporal (`data_extracao`)**:
   - Cada carga bruta salva no MongoDB Atlas contem o metadado `data_extracao` (em timestamp ISO 8601 UTC).
   - A leitura do MongoDB pelo `extract_collection_from_mongo` ordena os documentos por `data_extracao`, garantindo que o processamento transforme e alimente a carga mais recente sem descartar o historico bruto.

3. **Integridade da Camada Bronze vs Tabela Final (NeonDB)**:
   - A classe `Transform` nao utiliza indices fixos (como `[0]`) que descartem itens da lista horaria retornada pela Open-Meteo.
   - O volume de linhas da camada bronze (24 registros/dia na chave `hourly`) e integralmente preservado no DataFrame e persistido nas tabelas `clima` e `qualidade_ar` do NeonDB.

4. **Tratamento de Dados Ausentes (Nulos vs Zero)**:
   - A API publica Open-Meteo representa dados ausentes ou estacoes inoperantes como `null` nativo no JSON (convertido para `None` pelo `requests` e `NaN` pelo `pandas`).
   - Esses valores sao gravados estritamente como `NULL` no PostgreSQL do NeonDB (e nao mascarados como `0`), evitando distorcoes estatisticas em medias termicas e de poluicao.

## Dashboard Interativo (Streamlit)

O dashboard analitico consome os dados transformados diretamente do **NeonDB** e pode ser executado a partir da raiz com:

```powershell
python -m streamlit run dashboard/app.py
```

### Funcionalidades do Dashboard:
- **Filtros**: Seletor dinamico de metropolis brasileiras com dados persistidos.
- **Indicadores Chave (`st.metric`)**: Temperatura, Umidade, Chuva Acumulada, Vento e Indice PM2.5 com deltas e classificacoes da OMS.
- **Visualizacoes Graficas (Plotly)**: Series temporais de clima, concentracao de gases e particulas inalaveis ($PM_{10}$ vs $PM_{2.5}$).
- **Benchmarking & Geolocalizacao**: Ranking de qualidade do ar entre capitais brasileiras e mapa metropolitano interativo.

## Servidor MCP com o banco do projeto (Aula 10)

O arquivo `servidor.py` expoe o banco NeonDB da pipeline como um servidor MCP ([FastMCP](https://gofastmcp.com/)). Um app de IA (Claude Desktop, VS Code) se conecta a ele e passa a consultar os dados de clima e qualidade do ar, inclusive com perguntas em portugues respondidas pelo GPT.

```text
App de IA (Claude Desktop, VS Code)
    |  chama uma ferramenta
    v
servidor.py (FastMCP) --> AssistenteGPT (src/assistente.py) --> API do GPT
    |
    v
BancoComLimite / BancoNeon (src/banco.py, somente leitura)
    |
    v
NeonDB: tabelas clima e qualidade_ar (carregadas pela pipeline)
```

| Arquivo | Conteudo |
| --- | --- |
| `src/banco.py` | `BancoNeon` (conexao somente leitura, `consultar`, `listar_tabelas`, `descrever_tabela`, `esquema_completo`, `contar_linhas`) e `BancoComLimite` |
| `src/assistente.py` | `AssistenteGPT` (`perguntar`, `gerar_sql`, `explicar_resultado`, `responder`) |
| `servidor.py` | Servidor MCP com as ferramentas |
| `cliente_teste.py` | Cliente de teste pelo terminal |
| `test_mcp.py` | Teste local sem banco e sem chave do GPT |

### Ferramentas

| Ferramenta | O que faz |
| --- | --- |
| `listar_tabelas()` | Lista as tabelas do banco |
| `descrever_tabela(tabela)` | Colunas e tipos de uma tabela |
| `contar_linhas(tabela)` | Quantas linhas a tabela tem (Exercicio 1) |
| `executar_select(sql)` | Executa um SELECT (no maximo 10 linhas) |
| `perguntar_ao_banco(pergunta)` | O GPT gera o SQL, o banco executa e o GPT explica |
| `cidades_disponiveis()` | Cidades com dados no banco |
| `resumo_cidade(cidade)` | Medias e extremos de clima e poluentes, e horas com PM2.5 acima do limite da OMS |
| `ranking_qualidade_ar()` | Cidades ordenadas pela media de PM2.5 |

### Exercicios da Aula 10

1. **Nova ferramenta**: `contar_linhas(tabela: str) -> int`. Como nome de tabela nao pode ir no `%s`, o nome e conferido com a lista de tabelas reais antes da consulta (evita SQL Injection).
2. **Modelo configuravel**: `src/config.py` le a variavel `MODELO` do `.env`, com `gpt-6-luna` como padrao, e o servidor passa esse valor ao `AssistenteGPT`.
3. **Heranca**: `BancoComLimite(BancoNeon)` sobrescreve `consultar` e devolve no maximo 10 linhas, reaproveitando o construtor e o metodo do pai com `super()`. O servidor usa `BancoComLimite` no lugar de `BancoNeon`. As consultas de catalogo (`listar_tabelas`, `descrever_tabela`) nao passam pelo limite, para nenhuma tabela ficar de fora do esquema enviado ao GPT.

### Configuracao

Alem das variaveis da pipeline, o `.env` recebe:

```dotenv
GPT=sk-...
# Opcional: servico gratuito compativel com a biblioteca openai
# GPT_BASE_URL=https://...
# Opcional: modelo (padrao gpt-6-luna)
# MODELO=gpt-6-luna
```

A conexao com o NeonDB usa `NEON_DB_URL` (o nome `NEON`, usado na aula, tambem e aceito). Ela e aberta em modo somente leitura: o banco recusa `INSERT`, `UPDATE`, `DELETE` e `DROP`, mesmo se o GPT gerar esse SQL.

### Executando

```powershell
pip install -r requirements.txt
python cliente_teste.py                 # lista as ferramentas, conta as linhas e faz uma pergunta
fastmcp dev inspector servidor.py       # interface visual para testar cada ferramenta
python test_mcp.py                      # teste local, sem banco e sem chave do GPT
```

Para usar no Claude Desktop ou no VS Code, adicione ao arquivo de configuracao de MCP do aplicativo:

```json
{
  "mcpServers": {
    "smart-city": {
      "command": "C:\\caminho\\do\\projeto\\.venv\\Scripts\\python.exe",
      "args": ["C:\\caminho\\do\\projeto\\servidor.py"]
    }
  }
}
```

Exemplos de perguntas: "Qual cidade tem o pior ar?", "Qual foi a hora mais quente em Recife?", "Choveu em Curitiba?".

## Produto de dados (Desafio da Disciplina)

O produto le **somente do NeonDB**, nunca direto da API. O caminho do dado:

```text
Open-Meteo (APIs publicas de clima e qualidade do ar)
    |  Extract (flow_etl.py / run_etl.py, orquestrado e agendado pelo Prefect)
    v
MongoDB Atlas - camada bronze (resposta bruta + data_extracao)
    |  Transform (pandas)
    v
NeonDB - camada prata (tabelas clima e qualidade_ar, carga sem duplicar por cidade)
    |
    +--> Dashboard Streamlit (dashboard/app.py), com a secao "Pergunte aos Dados"
    +--> Servidor MCP (servidor.py), usado por apps de IA
```

- **Dashboard**: indicadores, graficos, ranking e mapa, todos a partir do NeonDB. A secao **Pergunte aos Dados** usa as mesmas classes do servidor MCP (`AssistenteGPT` + `BancoComLimite`) e mostra o SQL gerado e os dados usados.
- **Sincronizar cidade**: o botao do dashboard roda a pipeline completa (`run_etl.executar_etl_cidade`), passando pelo MongoDB antes do NeonDB.
- **Servidor MCP**: as ferramentas `resumo_cidade` e `ranking_qualidade_ar` entregam os indicadores prontos para um agente de IA.
- **Credenciais**: todas lidas uma unica vez em `src/config.py`, a partir do `.env` (fora do codigo).

## Seguranca

- Nunca compartilhe o arquivo `.env` ou strings de conexao com senhas.
- Use usuarios com apenas as permissoes necessarias no MongoDB Atlas e no NeonDB.
- Se uma credencial for exposta, revogue-a e gere outra imediatamente.

## Links

- [Open-Meteo](https://open-meteo.com/)
- [MongoDB Atlas](https://www.mongodb.com/atlas)
- [NeonDB](https://neon.tech/)
- [Branch de entrega](https://github.com/poeisie/projeto-ETL-em-POO/tree/entrega-etl-neon)

