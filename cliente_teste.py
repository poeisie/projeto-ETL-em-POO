"""Cliente de teste do servidor MCP pelo terminal: python cliente_teste.py"""
import asyncio

from fastmcp import Client

from servidor import mcp


async def main():
    # Conecta direto no objeto do servidor (em memoria)
    async with Client(mcp) as cliente:
        ferramentas = await cliente.list_tools()
        print("Ferramentas disponiveis:")
        for ferramenta in ferramentas:
            print(f" - {ferramenta.name}: {ferramenta.description}")

        tabelas = await cliente.call_tool("listar_tabelas", {})
        print("\nTabelas:", tabelas.data)

        for tabela in tabelas.data:
            total = await cliente.call_tool("contar_linhas", {"tabela": tabela})
            print(f"  {tabela}: {total.data} linhas")

        pergunta = input("\nFaca uma pergunta sobre o banco (ou Enter para sair): ")
        if pergunta:
            resultado = await cliente.call_tool("perguntar_ao_banco", {"pergunta": pergunta})
            print("\nSQL gerado:", resultado.data["sql"])
            print("Resposta:", resultado.data["resposta"])


if __name__ == "__main__":
    asyncio.run(main())
