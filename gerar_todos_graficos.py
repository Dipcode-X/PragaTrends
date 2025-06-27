# -*- coding: utf-8 -*-

"""
Script para gerar automaticamente um gráfico para cada categoria de praga
disponível no banco de dados.
"""

# Importa as funções reutilizáveis do nosso script visualizador
from visualizador import (
    listar_categorias,
    buscar_dados_categoria,
    gerar_grafico_categoria,
    DB_FILE
)

def main():
    """Função principal para orquestrar a geração de todos os gráficos."""
    print("--- Iniciando geração de todos os gráficos de tendências ---")

    # 1. Obter a lista de todas as categorias do banco de dados
    categorias = listar_categorias(DB_FILE)

    if not categorias:
        print("Nenhuma categoria encontrada. Execute o 'coletor_trends.py' primeiro.")
        return

    print(f"Encontradas {len(categorias)} categorias. Gerando gráficos...")

    # 2. Iterar sobre cada categoria e gerar o gráfico correspondente
    for i, categoria in enumerate(categorias):
        print(f"\n({i+1}/{len(categorias)}) Processando categoria: {categoria}...")
        
        # Busca os dados do banco
        dados_df = buscar_dados_categoria(categoria, DB_FILE)
        
        # Gera e salva o gráfico
        if not dados_df.empty:
            gerar_grafico_categoria(dados_df, categoria)
        else:
            print(f"  - Nenhum dado encontrado para '{categoria}', gráfico não gerado.")

    print("\n--- Processo concluído. Todos os gráficos foram gerados. ---")

# --- Bloco de Execução Principal ---
if __name__ == "__main__":
    main()
