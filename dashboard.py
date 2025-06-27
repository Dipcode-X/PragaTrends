# -*- coding: utf-8 -*-

"""
Dashboard interativo para visualização de tendências de pragas usando Streamlit e Plotly.
Permite ao usuário selecionar a categoria da praga e o período de análise.
"""

import streamlit as st
import plotly.express as px
import pandas as pd
import os

# Importa a função de coleta e o nome do arquivo do banco de dados
import coletor_trends
# Mantém as funções de visualização, mas agora o DB_FILE vem do coletor
from visualizador import listar_categorias, buscar_dados_categoria

# --- Função para garantir que os dados existem ---
def garantir_dados_locais():
    """Verifica se o banco de dados existe. Se não, executa a coleta."""
    # Usa a variável DB_FILE do script coletor como fonte da verdade
    if not os.path.exists(coletor_trends.DB_FILE):
        st.info("Primeira execução ou banco de dados não encontrado.")
        st.warning("Iniciando a coleta de dados do Google Trends. Isso pode levar alguns minutos...")
        with st.spinner('Coletando e salvando dados... Por favor, aguarde.'):
            coletor_trends.main() # Executa a função de coleta
        st.success("Coleta de dados concluída!")
        st.balloons()
        st.rerun() # Recarrega o script para exibir o dashboard com os dados

# --- Configuração da Página do Dashboard ---
st.set_page_config(
    page_title="Dashboard de Tendências de Pragas",
    page_icon="🦟",
    layout="wide"
)

# Garante que os dados existem antes de tentar desenhar o dashboard
garantir_dados_locais()

# --- Funções do Dashboard ---
def carregar_dados(categoria):
    """Carrega os dados para uma categoria e os armazena em cache para performance."""
    df = buscar_dados_categoria(categoria, coletor_trends.DB_FILE)
    if not df.empty:
        df['data'] = pd.to_datetime(df['data'])
    return df

# --- Interface do Usuário (UI) ---
st.title("📈 Dashboard de Tendências de Pragas")
st.markdown("Explore o interesse de busca por diferentes pragas no Brasil ao longo do tempo.")

# --- Barra Lateral com Controles ---
st.sidebar.header("Filtros")

# 1. Seleção de Categoria
categorias_disponiveis = listar_categorias(coletor_trends.DB_FILE)
if not categorias_disponiveis:
    st.warning("Nenhuma categoria encontrada no banco de dados. Execute o `coletor_trends.py`.")
    st.stop()

categoria_selecionada = st.sidebar.selectbox(
    "Selecione a Categoria da Praga:",
    options=categorias_disponiveis
)

# Carrega os dados para a categoria escolhida
df_dados = carregar_dados(categoria_selecionada)

if df_dados.empty:
    st.error(f"Não foram encontrados dados para a categoria '{categoria_selecionada}'.")
else:
    # 2. Seleção de Período
    data_min = df_dados['data'].min().date()
    data_max = df_dados['data'].max().date()

    periodo_selecionado = st.sidebar.date_input(
        'Selecione o Período:',
        value=(data_min, data_max),
        min_value=data_min,
        max_value=data_max,
        format="DD/MM/YYYY"
    )

    # Garante que temos um início e um fim para o período
    if len(periodo_selecionado) == 2:
        start_date, end_date = periodo_selecionado
        
        # Filtra o DataFrame com base no período selecionado
        df_filtrado = df_dados[
            (df_dados['data'].dt.date >= start_date) & 
            (df_dados['data'].dt.date <= end_date)
        ]

        # Agrega os dados: agrupa por data e soma os interesses dos termos
        df_agregado = df_filtrado.groupby('data')['interesse'].sum().reset_index()

        # --- Lógica de Granularidade Mista ---
        df_final = pd.DataFrame()
        if not df_agregado.empty:
            # Encontra a data mais recente para definir o "mês atual"
            last_date = df_agregado['data'].max()
            start_of_last_month = last_date.to_period('M').to_timestamp()

            # Separa os dados históricos dos dados do último mês
            df_historico = df_agregado[df_agregado['data'] < start_of_last_month]
            df_recente = df_agregado[df_agregado['data'] >= start_of_last_month]

            # Processa dados históricos com granularidade MENSAL
            df_mensal = df_historico.set_index('data').resample('MS').mean().reset_index() if not df_historico.empty else pd.DataFrame(columns=['data', 'interesse'])

            # Processa dados recentes com granularidade SEMANAL
            df_semanal = df_recente.set_index('data').resample('W').mean().reset_index() if not df_recente.empty else pd.DataFrame(columns=['data', 'interesse'])

            # Combina os dois dataframes
            df_final = pd.concat([df_mensal, df_semanal], ignore_index=True)
            df_final.dropna(inplace=True)
            df_final.sort_values(by='data', inplace=True)

            # Re-normaliza o interesse consolidado para a escala 0-100
            if not df_final.empty:
                max_interesse = df_final['interesse'].max()
                if max_interesse > 0:
                    df_final['interesse'] = (df_final['interesse'] / max_interesse) * 100

        # --- Visualizações ---
        st.header(f"Análise para: {categoria_selecionada}")

        # 3. Gráfico Interativo com Plotly (usando dados re-normalizados)
        fig = px.line(
            df_final,
            x='data',
            y='interesse',
            title=f'Interesse Consolidado Normalizado para {categoria_selecionada}',
            labels={'data': 'Data (Visão Mensal/Semanal)', 'interesse': 'Nível de Interesse Normalizado (0-100)'},
            markers=True
        )
        st.plotly_chart(fig, use_container_width=True)

        # 4. Tabela de Dados Brutos (opcional, mostrando dados originais)
        with st.expander("Ver dados detalhados por termo"):
            st.dataframe(df_filtrado)
    else:
        st.warning("Por favor, selecione um período de início e fim.")
