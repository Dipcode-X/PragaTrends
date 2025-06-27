# -*- coding: utf-8 -*-

"""
Script para coletar dados de tendências de busca do Google Trends sobre pragas
e armazenar em um banco de dados SQLite.
"""

import sqlite3
import pandas as pd
from pytrends.request import TrendReq
import requests
import time

# Desabilita os avisos de SSL para ambientes com proxy corporativo
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

# --- Seção de Configuração ---
# Configure as categorias e os termos de busca.
# A chave do dicionário é a categoria, e o valor é a lista de termos a serem pesquisados.
CATEGORIAS_PRAGAS = {
    'Lesmas': ['lesma', 'lesmas', 'caracol', 'caracois'],
    'Ratos': ['rato', 'ratos', 'ratazana', 'ratazanas'],
    'Baratas': ['barata', 'baratas', 'barata de esgoto', 'baratas de esgoto'],
    'Formigas': ['formiga', 'formigas', 'formiga cortadeira', 'formigas cortadeiras'],
    'Escorpiões': ['escorpião', 'escorpiões', 'escorpião amarelo', 'escorpião marrom'],
    'Aranhas': ['aranha', 'aranhas', 'aranha marrom', 'armadeira']
}
GEOLOCATION = 'BR'
TIMEFRAME = '2020-01-01 2025-06-27' # Período de tempo (dados semanais de 2020 até hoje) para uma análise mais ampla
DB_FILE = 'tendencias_pragas_v4.db' # Força a recriação do banco de dados

def iniciar_banco(db_file):
    """Cria e configura o banco de dados SQLite e a tabela 'trends'."""
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        # Adicionada a coluna 'categoria' e atualizada a chave primária
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trends (
                data TEXT,
                termo_busca TEXT,
                interesse INTEGER,
                geolocalizacao TEXT,
                categoria TEXT,
                PRIMARY KEY (data, termo_busca, geolocalizacao, categoria)
            )
        ''')
        conn.commit()
        conn.close()
        print(f"Banco de dados '{db_file}' pronto para uso.")
    except sqlite3.Error as e:
        print(f"Erro ao iniciar o banco de dados: {e}")

def buscar_dados_trends(termos, geo, timeframe, retries=3, initial_delay=10):
    """Busca dados no Google Trends com tratamento de erros e retentativas (backoff exponencial).
    Isso ajuda a lidar com erros de limite de requisição (código 429).
    """
    for attempt in range(retries):
        try:
            # Conecta-se ao Google e constrói o payload
            pytrends = TrendReq(hl='pt-BR', tz=360, requests_args={'verify': False})
            pytrends.build_payload(kw_list=termos, cat=0, timeframe=timeframe, geo=geo, gprop='')
            
            # Obtém os dados de interesse ao longo do tempo
            df = pytrends.interest_over_time()
            
            if df.empty:
                return None # Se não há dados, não adianta tentar de novo
            
            if 'isPartial' in df.columns:
                df = df.drop(columns=['isPartial'])
            
            return df # Sucesso!

        except Exception as e:
            if '429' in str(e):
                if attempt < retries - 1:
                    delay = initial_delay * (2 ** attempt) # Espera progressiva
                    print(f"Erro 429 (Too Many Requests). Tentando novamente em {delay} segundos...")
                    time.sleep(delay)
                else:
                    print(f"Ocorreu um erro ao buscar os dados no Google Trends: {e}")
                    return None # Falhou em todas as tentativas
            else:
                # Para outros tipos de erro, não tenta novamente
                print(f"Ocorreu um erro inesperado ao buscar os dados no Google Trends: {e}")
                return None
    return None

def salvar_dados_no_banco(df, categoria, geolocation, db_file):
    """Salva os dados do DataFrame no banco de dados SQLite."""
    try:
        df_long = df.reset_index().melt(
            id_vars='date',
            var_name='termo_busca',
            value_name='interesse'
        )
        df_long['geolocalizacao'] = geolocation
        df_long['categoria'] = categoria # Adiciona a categoria
        df_long['data'] = df_long['date'].dt.strftime('%Y-%m-%d')

        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        dados_para_salvar = [
            (row['data'], row['termo_busca'], row['interesse'], row['geolocalizacao'], row['categoria'])
            for index, row in df_long.iterrows()
        ]

        cursor.executemany('''
            INSERT OR REPLACE INTO trends (data, termo_busca, interesse, geolocalizacao, categoria)
            VALUES (?, ?, ?, ?, ?)
        ''', dados_para_salvar)

        conn.commit()
        conn.close()
        print(f"{len(dados_para_salvar)} registros da categoria '{categoria}' foram salvos/atualizados.")
    except Exception as e:
        print(f"Ocorreu um erro ao salvar os dados da categoria '{categoria}': {e}")

def main():
    """Função principal que orquestra todo o processo de coleta de dados."""
    print("Iniciando processo de coleta de dados de pragas...")
    print("\n1. Configurando o banco de dados...")
    iniciar_banco(DB_FILE)

    try:
        # Loop para buscar dados para cada categoria de praga
        for categoria, keywords in CATEGORIAS_PRAGAS.items():
            print(f"\n--- Processando categoria: {categoria} ---")
            
            print(f"2. Buscando dados para os termos: {keywords}...")
            trends_df = buscar_dados_trends(keywords, GEOLOCATION, TIMEFRAME)

            if trends_df is not None and not trends_df.empty:
                print("3. Salvando dados no banco...")
                salvar_dados_no_banco(trends_df, categoria, GEOLOCATION, DB_FILE)
            else:
                print(f"Nenhum dado encontrado para a categoria '{categoria}'. Pulando para a próxima.")
            
            # Adiciona uma pausa para não sobrecarregar a API do Google
            print("Aguardando 5 segundos antes da próxima requisição...")
            time.sleep(5)

        print("\nProcesso de coleta concluído.")
    except Exception as e:
        print(f"ERRO FATAL DURANTE A COLETA: {e}")
        # Re-levanta a exceção para que o dashboard possa capturá-la e exibi-la.
        raise e

# --- Bloco de Execução Principal ---
if __name__ == "__main__":
    main()
