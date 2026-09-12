### Equipe

Caliel Feijó
Giulia Ferreira
Joana Farias
Juliana Comparoto
Paulo Marrocos
Pedro Vinicius
Sarah Cyrne

# Pipeline de ETL - Smart City (Open-Meteo)

Pipeline de ETL que extrai dados de clima e de qualidade do ar da
[Open-Meteo](https://open-meteo.com) (APIs públicas, sem necessidade de
cadastro ou chave de acesso), carrega o resultado bruto em coleções do
MongoDB, transforma esses dados com pandas e carrega o resultado final
em tabelas SQLite.

Segue o mesmo padrão do projeto original de PNAD Contínua/IBGE
(`Extract` / `Transform` / `Load`), adaptado para uma fonte de dados de
smart city.

## Estrutura do projeto

```
src/
  extract.py    # Extract: busca dados de clima (clima()) e qualidade do ar (qualidade_ar())
                # na Open-Meteo, e relê dados já carregados no MongoDB
  transform.py  # Transform: transforma os dados brutos em DataFrames prontos para o SQLite
  load.py       # Load: salva em JSON local (load_json), no MongoDB (load_mongo) ou em SQLite (load_sqlite)
run_etl.py      # ponto de entrada do pipeline (Extract -> Load -> Extract -> Transform -> Load), em main()
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
  os documentos de uma coleção do MongoDB (por exemplo, a que
  `Load.load_mongo` acabou de popular), para alimentar a etapa de
  transformação.
- `Extract.CIDADES`, `Extract.VARIAVEIS_CLIMA` e `Extract.POLUENTES`:
  dicionários com os conjuntos fechados de cidades, variáveis
  climáticas e poluentes suportados. `cidade`, cada item de
  `variaveis` e cada item de `poluentes` são validados contra esses
  dicionários — um valor inválido gera `ValueError`.
- As URLs base de cada API (`self.base_url_clima` e
  `self.base_url_qualidade_ar`) são definidas uma única vez, no
  `__init__`, e não aparecem soltas dentro dos métodos.
- A conexão com o MongoDB (`self.client`) é criada uma única vez, no
  `__init__`, e encerrada com `close()`.

### `Transform`

- `transform_clima(data)`: recebe o dicionário bruto retornado pela
  Forecast API (o mesmo salvo no MongoDB) e devolve um `DataFrame` com
  uma linha por hora (cidade, data_hora, variáveis climáticas), pronto
  para carga no SQLite.
- `transform_qualidade_ar(data)`: mesma lógica, para o dicionário bruto
  retornado pela Air Quality API.

### `Load`

- `load_json(nome_arquivo, data)`: salva os dados extraídos em
  `jsons/<nome_arquivo>.json`.
- `load_mongo(data, db_name, collection_name)`: insere os dados
  (dicionário único ou lista de dicionários) na coleção informada e
  fecha a conexão com o MongoDB (`close()`) logo em seguida.
- `load_sqlite(df, nome_banco="smart_city.db", nome_tabela="clima")`:
  salva um `DataFrame` (já transformado) em uma tabela de um banco
  SQLite local.
- A conexão com o MongoDB (`self.client`) é criada uma única vez, no
  `__init__` da classe.

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

Crie um arquivo `.env` na raiz do projeto com a string de conexão do
MongoDB (veja `.env.example`):

```
MONGODB_URI=<sua_connection_string>
```

## Executando o pipeline

```
python run_etl.py
```

O pipeline roda em três etapas:

1. Extrai os dados de clima e de qualidade do ar de uma cidade via
   Open-Meteo, e insere o resultado bruto de cada consulta em uma
   coleção própria (`Clima` e `QualidadeAr`) do banco `SmartCity` no
   MongoDB configurado.
2. Relê esses mesmos dados do MongoDB e os transforma em DataFrames
   (uma linha por hora).
3. Salva os DataFrames transformados nas tabelas `clima` e
   `qualidade_ar` do banco SQLite local `smart_city.db` (arquivo
   gerado na raiz do projeto, não versionado).

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
