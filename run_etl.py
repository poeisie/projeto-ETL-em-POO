import argparse
from src.config import DB_MONGO
from src.extract import Extract
from src.load import Load
from src.transform import Transform


def executar_etl_cidade(cidade: str = "Recife") -> dict:
    """Executa a pipeline ETL (API -> Mongo -> Transform -> Neon) para a metrópole solicitada."""
    if cidade not in Extract.CIDADES:
        raise ValueError(f"Cidade '{cidade}' não suportada. Opções: {list(Extract.CIDADES.keys())}")

    print(f"\n[ETL - {cidade}] Etapa 1: Extração da API Open-Meteo e gravação no MongoDB...")
    ext = Extract()
    transformer = Transform()

    clima_bruto = ext.clima(cidade=cidade)
    Load().load_mongo(clima_bruto, DB_MONGO, "Clima")

    qualidade_bruta = ext.qualidade_ar(cidade=cidade)
    Load().load_mongo(qualidade_bruta, DB_MONGO, "QualidadeAr")

    print(f"[ETL - {cidade}] Etapa 2: Recuperando última carga do MongoDB e transformando dados...")
    clima_docs = ext.extract_collection_from_mongo(DB_MONGO, "Clima", cidade=cidade)
    if not clima_docs:
        raise RuntimeError(f"A coleção 'Clima' não contém registros para a cidade {cidade}.")
    df_clima = transformer.transform_clima(clima_docs[-1])

    qualidade_docs = ext.extract_collection_from_mongo(DB_MONGO, "QualidadeAr", cidade=cidade)
    if not qualidade_docs:
        raise RuntimeError(f"A coleção 'QualidadeAr' não contém registros para a cidade {cidade}.")
    df_qualidade = transformer.transform_qualidade_ar(qualidade_docs[-1])

    print(f"[ETL - {cidade}] Etapa 3: Salvando dados no NeonDB...")
    ld = Load()
    ld.load_neon(df=df_clima, nome_tabela="clima")
    ld.load_neon(df=df_qualidade, nome_tabela="qualidade_ar")
    ld.close()
    ext.close()

    print(f"[ETL - {cidade}] Concluído com sucesso! ({len(df_clima)} linhas clima, {len(df_qualidade)} linhas qualidade do ar)\n")
    return {"cidade": cidade, "linhas_clima": len(df_clima), "linhas_qualidade": len(df_qualidade)}


def main():
    parser = argparse.ArgumentParser(description="Executa o pipeline ETL para uma metrópole.")
    parser.add_argument("--cidade", default="Recife", help="Nome da cidade (padrão: Recife)")
    args = parser.parse_args()
    executar_etl_cidade(cidade=args.cidade)


if __name__ == "__main__":
    main()

