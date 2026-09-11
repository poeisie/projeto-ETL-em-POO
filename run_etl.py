from src.extract import Extract
from src.load import Load
from src.transform import Transform


def main():
    ext = Extract()
    transformer = Transform()

    cidade = "Recife"

    print("Etapa 1: Extração das APIs da Open-Meteo!")
    clima_bruto = ext.clima(cidade=cidade)
    # Cada chamada a load_mongo fecha a própria conexão ao final (mesmo
    # padrão do projeto do IBGE); por isso usamos uma instância de Load
    # por chamada, já que aqui carregamos duas coleções diferentes.
    Load().load_mongo(clima_bruto, "SmartCity", "Clima")

    qualidade_bruta = ext.qualidade_ar(cidade=cidade)
    Load().load_mongo(qualidade_bruta, "SmartCity", "QualidadeAr")

    print("Etapa 2: Transformando os dados!")
    clima_docs = ext.extract_collection_from_mongo("SmartCity", "Clima")
    df_clima = transformer.transform_clima(clima_docs[-1])

    qualidade_docs = ext.extract_collection_from_mongo("SmartCity", "QualidadeAr")
    df_qualidade = transformer.transform_qualidade_ar(qualidade_docs[-1])

    print("Etapa 3: Salvando no SQLite!")
    ld = Load()
    ld.load_sqlite(df=df_clima, nome_banco="smart_city.db", nome_tabela="clima")
    ld.load_sqlite(df=df_qualidade, nome_banco="smart_city.db", nome_tabela="qualidade_ar")
    ld.close()

    ext.close()


if __name__ == "__main__":
    main()
