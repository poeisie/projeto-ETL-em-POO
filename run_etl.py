from src.extract import Extract
from src.load import Load
from src.transform import Transform


def main():
    ext = Extract()
    transformer = Transform()

    cidade = "Recife"

    print("Etapa 1: Extração da API e persistência no MongoDB Atlas!")
    clima_bruto = ext.clima(cidade=cidade)
    # Cada chamada a load_mongo fecha a própria conexão ao final.
    Load().load_mongo(clima_bruto, "SmartCity", "Clima")

    qualidade_bruta = ext.qualidade_ar(cidade=cidade)
    Load().load_mongo(qualidade_bruta, "SmartCity", "QualidadeAr")

    print("Etapa 2: Recuperando do MongoDB e transformando os dados!")
    clima_docs = ext.extract_collection_from_mongo("SmartCity", "Clima")
    if not clima_docs:
        raise RuntimeError("A coleção 'Clima' do MongoDB Atlas está vazia.")
    df_clima = transformer.transform_clima(clima_docs[-1])

    qualidade_docs = ext.extract_collection_from_mongo("SmartCity", "QualidadeAr")
    if not qualidade_docs:
        raise RuntimeError("A coleção 'QualidadeAr' do MongoDB Atlas está vazia.")
    df_qualidade = transformer.transform_qualidade_ar(qualidade_docs[-1])

    print("Etapa 3: Salvando os dados transformados no NeonDB!")
    ld = Load()
    ld.load_neon(df=df_clima, nome_tabela="clima")
    ld.load_neon(df=df_qualidade, nome_tabela="qualidade_ar")
    ld.close()

    ext.close()


if __name__ == "__main__":
    main()
