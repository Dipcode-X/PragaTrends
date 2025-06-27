# -*- coding: utf-8 -*-

"""
Script para visualizar os dados de tendências de pragas coletados do Google Trends
e armazenados no banco de dados SQLite.
"""

import sqlite3
import pandas as pd
import sys
import matplotlib.pyplot as plt
import os

# --- Configuração ---
DB_FILE = 'tendencias_pragas.db'

def listar_categorias(db_file):
    """Conecta-se ao banco e retorna uma lista de categorias de pragas únicas."""
    try:
        conn = sqlite3.connect(db_file)
        # Usamos 'DISTINCT' para obter cada categoria apenas uma vez
        categorias = pd.read_sql_query("SELECT DISTINCT categoria FROM trends ORDER BY categoria", conn)
        conn.close()
        return categorias['categoria'].tolist()
    except Exception as e:
        print(f"Erro ao listar categorias: {e}")
        return []

def gerar_grafico_categoria(df, categoria):
    """Gera e salva um gráfico de linhas a partir de um DataFrame de tendências."""
    if df.empty:
        print("DataFrame vazio, não é possível gerar o gráfico.")
        return

    try:
        output_dir = "graficos"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        plt.style.use('seaborn-v0_8-whitegrid')
        fig, ax = plt.subplots(figsize=(15, 7))

        # Garante que a coluna 'data' seja do tipo datetime para o plot
        df['data'] = pd.to_datetime(df['data'])

        # Plota uma linha para cada termo de busca na categoria
        for termo in df['termo_busca'].unique():
            df_termo = df[df['termo_busca'] == termo]
            ax.plot(df_termo['data'], df_termo['interesse'], label=termo.capitalize(), marker='o', linestyle='-')

        # Formatação do gráfico
        ax.set_title(f'Tendência de Busca para: {categoria}', fontsize=16)
        ax.set_xlabel('Data', fontsize=12)
        ax.set_ylabel('Nível de Interesse (0-100)', fontsize=12)
        ax.legend(title='Termos de Busca')
        ax.grid(True, which='both', linestyle='--', linewidth=0.5)
        plt.xticks(rotation=45)
        plt.tight_layout()

        # Salva o gráfico em um arquivo
        nome_arquivo = os.path.join(output_dir, f"grafico_{categoria.replace(' ', '_')}.png")
        plt.savefig(nome_arquivo)
        plt.close(fig) # Fecha a figura para liberar memória

        print(f"\nGráfico salvo com sucesso em: {nome_arquivo}")

    except Exception as e:
        print(f"Ocorreu um erro ao gerar o gráfico: {e}")

def buscar_dados_categoria(categoria, db_file):
    """Busca os dados de tendência para uma categoria específica e retorna um DataFrame."""
    try:
        conn = sqlite3.connect(db_file)
        query = "SELECT data, termo_busca, interesse FROM trends WHERE categoria = ? ORDER BY data"
        df = pd.read_sql_query(query, conn, params=(categoria,))
        conn.close()
        return df
    except Exception as e:
        print(f"Erro ao buscar dados para a categoria {categoria}: {e}")
        return pd.DataFrame()

def visualizar_dados_por_categoria(categoria, db_file):
    """Busca, exibe e gera gráfico para os dados de tendência de uma categoria."""
    df = buscar_dados_categoria(categoria, db_file)

    if df.empty:
        print(f"Nenhum dado encontrado para a categoria '{categoria}'.")
    else:
        print(f"\n--- Exibindo dados para: {categoria} ---")
        with pd.option_context('display.max_rows', None):
            print(df)
        
        # Após exibir a tabela, gera o gráfico
        gerar_grafico_categoria(df.copy(), categoria)

    

# --- Bloco de Execução Principal ---
if __name__ == "__main__":
    print("--- Visualizador de Tendências de Pragas ---")
    categorias_disponiveis = listar_categorias(DB_FILE)

    # Modo 1: Direto (via argumento de linha de comando)
    if len(sys.argv) > 1:
        categoria_escolhida = sys.argv[1]
        categoria_valida = next((cat for cat in categorias_disponiveis if cat.lower() == categoria_escolhida.lower()), None)
        
        if categoria_valida:
            visualizar_dados_por_categoria(categoria_valida, DB_FILE)
        else:
            print(f"\nErro: Categoria '{categoria_escolhida}' não encontrada.")
            print("Categorias disponíveis:", ", ".join(categorias_disponiveis))
    
    # Modo 2: Interativo (se nenhum argumento for passado)
    else:
        if not categorias_disponiveis:
            print("Nenhuma categoria encontrada no banco de dados. Execute o coletor primeiro.")
        else:
            while True:
                print("\nCategorias disponíveis:")
                for cat in categorias_disponiveis:
                    print(f"- {cat}")
                
                print("\n(Digite 'sair' para encerrar)")
                try:
                    escolha = input("Digite o nome da categoria que deseja visualizar: ")
                except EOFError:
                    # Se o script for executado em um ambiente não interativo sem argumentos
                    print("\nEntrada não interativa detectada. Encerrando.")
                    break

                if escolha.lower() == 'sair':
                    break

                categoria_valida = next((cat for cat in categorias_disponiveis if cat.lower() == escolha.lower()), None)

                if categoria_valida:
                    visualizar_dados_por_categoria(categoria_valida, DB_FILE)
                else:
                    print(f"\nErro: Categoria '{escolha}' não encontrada. Por favor, tente novamente.")
    
    print("\nVisualizador encerrado.")
