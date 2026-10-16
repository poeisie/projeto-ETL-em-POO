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
|   |-- extract.py       # Extracao das APIs e leitura do MongoDB Atlas
|   |-- transform.py     # Transformacao dos documentos em DataFrames
|   `-- load.py          # Carga no MongoDB Atlas e no NeonDB
|-- flow_etl.py          # Orquestracao da pipeline com Prefect (tasks + flow)
|-- run_etl.py           # Execucao sequencial da pipeline, sem orquestrador
|-- test_pipeline.py     # Teste local com APIs e MongoDB simulados
|-- test_flow.py         # Teste local do flow do Prefect (sucesso e falha)
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

## Seguranca

- Nunca compartilhe o arquivo `.env` ou strings de conexao com senhas.
- Use usuarios com apenas as permissoes necessarias no MongoDB Atlas e no NeonDB.
- Se uma credencial for exposta, revogue-a e gere outra imediatamente.

## Links

- [Open-Meteo](https://open-meteo.com/)
- [MongoDB Atlas](https://www.mongodb.com/atlas)
- [NeonDB](https://neon.tech/)
- [Branch de entrega](https://github.com/poeisie/projeto-ETL-em-POO/tree/entrega-etl-neon)
