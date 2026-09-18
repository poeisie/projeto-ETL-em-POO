### Equipe

- Caliel Feijó
- Giulia Ferreira
- Joana Farias
- Juliana Comparoto
- Paulo Marrocos
- Pedro Vinicius
- Sarah Cyrne

# Pipeline de ETL - Smart City (Open-Meteo)

Pipeline de ETL que extrai dados de clima e de qualidade do ar da
[Open-Meteo](https://open-meteo.com) (APIs públicas, sem necessidade de
cadastro ou chave de acesso), salva o resultado bruto em coleções do
MongoDB Atlas, transforma esses dados com pandas e carrega o resultado
final em tabelas do NeonDB.

A estrutura segue o mesmo padrão do projeto original de PNAD Contínua/IBGE
(`Extract` / `Transform` / `Load`), mas adaptado para a entrega da
disciplina com foco em dados em nuvem e no fluxo obrigatório:
`API → MongoDB Atlas → Transformação → NeonDB`.

## Estrutura do projeto

```
src/
  extract.py    # Extract: busca dados de clima (clima()) e qualidade do ar (qualidade_ar())
                # na Open-Meteo, e relê dados já carregados no MongoDB Atlas
  transform.py  # Transform: transforma os dados brutos em DataFrames prontos para o NeonDB
  load.py       # Load: salva em JSON local, no MongoDB Atlas e no NeonDB
run_etl.py      # ponto de entrada do pipeline: API -> MongoDB Atlas -> Transform -> NeonDB
jsons/          # saídas de exemplo em JSON
```

### `Extract`

- `clima(cidade, variaveis=None, dias_previsao=1)`: busca, na Forecast
  API da Open-Meteo, a série horária de variáveis climáticas (ver
  `Extract.VARIAVEIS_CLIMA`) para uma cidade.
- `qualidade_ar(cidade, poluentes=None, dias_previsao=1)`: busca, na Air
  Quality API da Open-Meteo, a série horária de concentração de
  poluentes (ver `Extract.POLUENTES`) para uma cidade.
- `extract_collection_from_mongo(db_name, collection_name)`: relê todos
  os documentos de uma coleção do MongoDB Atlas, para alimentar a etapa
  de transformação.
- `Extract.CIDADES`, `Extract.VARIAVEIS_CLIMA` e `Extract.POLUENTES`:
  dicionários com os conjuntos fechados de cidades, variáveis
  climáticas e poluentes suportados. `cidade`, cada item de
  `variaveis` e cada item de `poluentes` são validados contra esses
  dicionários — um valor inválido gera `ValueError`.
- A conexão com o MongoDB (`self.client`) é criada uma única vez, no
  `__init__`, e encerrada com `close()`.

### `Transform`

- `transform_clima(data)`: recebe o dicionário bruto retornado pela
  Forecast API (o mesmo salvo no MongoDB) e devolve um `DataFrame` com
  uma linha por hora (cidade, data_hora, variáveis climáticas), pronto
  para carga em tabela relacional.
- `transform_qualidade_ar(data)`: mesma lógica, para o dicionário bruto
  retornado pela Air Quality API.

### `Load`

- `load_json(nome_arquivo, data)`: salva os dados extraídos em
  `jsons/<nome_arquivo>.json`.
- `load_mongo(data, db_name, collection_name)`: insere os dados
  (dicionário único ou lista de dicionários) na coleção informada do
  MongoDB Atlas e fecha a conexão logo em seguida.
- `load_neon(df, nome_tabela, schema="public")`: salva um `DataFrame`
  transformado em uma tabela do NeonDB, criando a estrutura com base nos
  tipos das colunas e carregando os registros em massa.
- `load_sqlite(...)`: mantém suporte local para fins de validação,
  porém o fluxo principal da entrega é o carregamento no NeonDB e a
  arquitetura da solução foi ajustada para a nuvem.

## Configuração do Ambiente

### Windows

Criação do venv

```
python -m venv .venv
```

Ativação do venv

```
.venv\Scripts\activate
```

### Linux/Mac

Criação do venv

```
python3 -m venv .venv
```

Ativação do venv

```
source .venv/bin/activate
```

### Dependências

```
pip install -r requirements.txt
```

### Variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto com as strings de conexão:

```
MONGODB_URI=<sua_connection_string_mongodb_atlas>
NEON_DB_URL=postgresql://<usuario>:<senha>@<host>:5432/<database>?sslmode=require
```

Os valores reais devem permanecer locais e fora do controle de versão.
O arquivo `.env.example` contém um template seguro para orientar a
configuração da máquina de cada aluno ou desenvolvedor.

## Executando o pipeline

```
python run_etl.py
```

O pipeline roda em quatro etapas obrigatórias:

1. Extrai os dados de clima e de qualidade do ar de uma cidade via
   Open-Meteo.
2. Insere o resultado bruto de cada consulta em coleções próprias
   (`Clima` e `QualidadeAr`) do banco `SmartCity` no MongoDB Atlas.
3. Relê esses mesmos dados do MongoDB Atlas e os transforma em
   DataFrames (uma linha por hora).
4. Salva os DataFrames transformados nas tabelas `clima` e
   `qualidade_ar` no NeonDB, cumprindo o fluxo
   `API → MongoDB Atlas → Transformação → NeonDB`.

Para validar a entrega localmente, também foi incluída uma suíte de
testes automatizados (`test_pipeline.py`) que verifica a lógica de
extração, transformação e persistência com dados simulados.

## Ideias para quem quiser ir além

- Trocar a cidade/variáveis/poluentes fixos em `run_etl.py` por
  parâmetros de linha de comando.
- Adicionar outras APIs de smart city (ex.: mobilidade urbana, energia)
  seguindo o mesmo padrão de `Extract`/`Transform`/`Load`.
- Como `load_mongo` fecha a conexão ao final de cada chamada, quando o
  pipeline precisa popular mais de uma coleção na mesma execução (como
  aqui, com `Clima` e `QualidadeAr`), a solução mais simples é criar
  uma instância de `Load` por chamada, como feito em `run_etl.py`. Uma
  alternativa mais avançada é gerenciar a conexão de forma "preguiçosa"
  (lazy), reaproveitando-a entre chamadas.
