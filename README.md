# ETL Smart City

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
|-- run_etl.py           # Ponto de entrada do pipeline em nuvem
|-- test_pipeline.py     # Teste local com APIs e MongoDB simulados
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

## Equipe

Caliel Feijo, Giulia Ferreira, Joana Farias, Juliana Comparoto, Paulo Marrocos, Pedro Vinicius e Sarah Cyrne.

## Links

- [Open-Meteo](https://open-meteo.com/)
- [MongoDB Atlas](https://www.mongodb.com/atlas)
- [NeonDB](https://neon.tech/)
- [Branch de entrega](https://github.com/poeisie/projeto-ETL-em-POO/tree/entrega-etl-neon)