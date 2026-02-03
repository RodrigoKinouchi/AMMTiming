import pandas as pd
from functions.constants import piloto_modelo, modelo_cor, pilotos_cor_amattheis
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib as mpl
import streamlit as st
from pandas.io.formats.style import Styler
from fpdf import FPDF
import os
import tempfile
import plotly.io as pio
import numpy as np
import base64
from io import BytesIO
from PIL import Image


def normalizar_coluna_velocidade(df):
    """
    Renomeia a coluna 'SPT' para 'ST' se necessário, mantendo compatibilidade com o restante do código.
    """
    colunas = [col.strip().upper() for col in df.columns]
    if 'SPT' in colunas:
        original_name = df.columns[colunas.index('SPT')]
        df.rename(columns={original_name: 'ST'}, inplace=True)
    elif 'ST' not in colunas:
        raise ValueError(
            "Coluna de velocidade final ('ST' ou 'SPT') não encontrada no CSV.")
    return df


def separar_pilotos_por_volta(df):
    """Separa os dados por piloto, com base na linha que contém 'Stock' no Time of Day."""
    driver_info = {}
    current_driver = None

    # Identifica linhas com nome dos pilotos
    piloto_mask = df['Time of Day'].str.contains('Stock', na=False)

    for i, row in df.iterrows():
        if piloto_mask[i]:
            current_driver = (
                row['Time of Day']
                .replace(' - Stock Car PRO 2024', '')
                .replace(' - Stock Car Pro Rookie', '')
                .replace(' - Stock Car Pro', '')
                .strip()
                .title()
            )
            driver_info[current_driver] = []
        elif current_driver:
            driver_info[current_driver].append(row)

    # Converte listas de linhas em DataFrames com colunas específicas
    for driver in driver_info:
        temp_df = pd.DataFrame(driver_info[driver])
        driver_info[driver] = temp_df[['Lap', 'Lap Tm',
                                       'S1 Tm', 'S2 Tm', 'S3 Tm', 'ST']].copy()

    return driver_info


def maior_velocidade_por_piloto(driver_info):
    """Calcula a maior velocidade (ST) para cada piloto."""
    top_speed = {}

    for piloto, data in driver_info.items():
        # A maior velocidade do piloto
        max_speed = data['ST'].max()  # A maior velocidade do piloto
        top_speed[piloto] = max_speed

    return top_speed


def gerar_ranking_st(driver_info: dict, modelo_cor: dict, piloto_modelo: dict, top_n: int = 30) -> pd.DataFrame:
    """
    Gera o ranking de ST para todos os pilotos registrados e ordena do maior para o menor.

    Args:
        driver_info (dict): Dicionário contendo os dados de cada piloto com tempos ST.
        modelo_cor (dict): Dicionário contendo a cor associada a cada modelo de carro.
        piloto_modelo (dict): Dicionário contendo a associação de pilotos com seus respectivos modelos de carro.
        top_n (int): Número de linhas a exibir (padrão é 30).

    Returns:
        pd.DataFrame: DataFrame com a coluna de rank, nome do piloto, tempo ST e montadora, limitado a `top_n` linhas.
    """
    # Criar uma lista para armazenar todos os tempos ST de todos os pilotos
    all_st_data = []

    # Para cada piloto, adicionar todos os seus tempos ST à lista
    for piloto, data in driver_info.items():
        for st in data['ST']:
            # Ignorar valores 'NaN' ou 'inf' ao adicionar à lista
            # Usando np.isfinite para verificar valores válidos
            if pd.notna(st) and np.isfinite(st):
                all_st_data.append({'Piloto': piloto, 'ST': st})

    # Criar DataFrame com todos os tempos ST registrados
    df_st = pd.DataFrame(all_st_data)

    # Ordenar os tempos ST do maior para o menor
    df_st_sorted = df_st.sort_values(by='ST', ascending=False)

    # Adicionar coluna de Rank baseado no ST
    df_st_sorted['ST Rank'] = df_st_sorted['ST'].rank(
        # 'Int64' para permitir NaN
        ascending=False, method='min').astype('Int64')

    # Adicionar a coluna 'Montadora' com base no dicionário piloto_modelo
    df_st_sorted['Montadora'] = df_st_sorted['Piloto'].map(piloto_modelo)

    # Adicionar a coluna 'Cor' com base na montadora do piloto
    df_st_sorted['Cor'] = df_st_sorted['Montadora'].map(modelo_cor)

    # Limitar a exibição para as `top_n` melhores linhas
    df_top = df_st_sorted[['ST Rank', 'Piloto', 'ST', 'Montadora']].head(top_n)

    # Arredondar a coluna ST para 1 casa decimal (ou a quantidade que preferir)
    df_top['ST'] = df_top['ST'].round(1)

    # Estilizando o DataFrame: aplicando cores nas linhas com base na montadora
    def colorir_linhas(val):
        # Pega a cor da montadora ou branco como fallback
        cor = modelo_cor.get(val, 'white')
        return f'background-color: {cor}'

    # Aplicando a estilização
    df_styled = df_top.style.applymap(colorir_linhas, subset=['Montadora'])

    return df_styled


def convert_time_to_seconds(time_str):
    try:
        if pd.isna(time_str):
            return None
        if ':' in time_str:
            minutes, seconds = time_str.split(':')
            seconds, milliseconds = seconds.split('.')
            return int(minutes) * 60 + int(seconds) + int(milliseconds.ljust(3, '0')) / 1000
        else:
            seconds, milliseconds = time_str.split('.')
            return int(seconds) + int(milliseconds.ljust(3, '0')) / 1000
    except Exception:
        return None


def processar_resultado_csv(df):
    from .utils import separar_pilotos_por_volta  # Se estiver em outro arquivo

    driver_info = separar_pilotos_por_volta(df)

    resultados = []

    for piloto, dados in driver_info.items():
        dados = dados.copy()
        dados['Lap_Tm_Segundos'] = dados['Lap Tm'].apply(
            convert_time_to_seconds)
        dados = dados.dropna(subset=['Lap_Tm_Segundos'])

        if not dados.empty:
            melhor_volta = dados.loc[dados['Lap_Tm_Segundos'].idxmin()]
            resultados.append({
                'Piloto': piloto,
                'Numeral': piloto.split(' - ')[0],
                'Melhor_Volta': melhor_volta['Lap Tm'],
                'S1 Tm': melhor_volta['S1 Tm'],
                'S2 Tm': melhor_volta['S2 Tm'],
                'S3 Tm': melhor_volta['S3 Tm'],
                'Lap_Tm_Segundos': melhor_volta['Lap_Tm_Segundos']
            })

    df_resultado = pd.DataFrame(resultados)

    df_resultado = df_resultado.sort_values(
        by='Lap_Tm_Segundos').reset_index(drop=True)
    df_resultado['Posição'] = df_resultado.index + 1

    df_resultado['Melhor_Volta'] = df_resultado['Lap_Tm_Segundos'].apply(
        lambda x: f"{int(x // 60)}:{int(x % 60):02d}.{int((x * 1000) % 1000):03d}" if pd.notna(x) else ''
    )

    df_resultado = df_resultado[[
        'Posição', 'Numeral', 'Piloto', 'Melhor_Volta', 'S1 Tm', 'S2 Tm', 'S3 Tm']]
    df_resultado['Piloto'] = df_resultado['Piloto']
    return df_resultado

# Função para montar um dataframe com todos os dados, já com a montadora associada


def montar_dataframe_completo(driver_info: dict) -> pd.DataFrame:
    """Gera um DataFrame com todas as voltas e setores, junto com a montadora e piloto."""
    lista_dfs = []

    for piloto, df_piloto in driver_info.items():
        df_temp = df_piloto.copy()
        df_temp['Piloto'] = piloto
        df_temp['Lap_seconds'] = df_temp['Lap Tm'].apply(
            convert_time_to_seconds)
        modelo = piloto_modelo.get(piloto, 'Desconhecido')
        df_temp['Montadora'] = modelo
        lista_dfs.append(df_temp)

    return pd.concat(lista_dfs, ignore_index=True)

# Função para gerar boxplot de setores (S1, S2, S3 ou volta completa)


def gerar_boxplot_setor(df: pd.DataFrame, coluna_tempo: str, titulo: str, margem: float = 0.02, agrupador: str = 'Montadora') -> go.Figure:
    df[coluna_tempo] = pd.to_numeric(df[coluna_tempo], errors='coerce')
    df[coluna_tempo] = df[coluna_tempo].fillna(float('inf'))

    melhores = df.groupby(agrupador)[coluna_tempo].min()
    limites = melhores * (1 + margem)

    filtrado = df[df.apply(lambda x: x[coluna_tempo] <=
                           limites.get(x[agrupador], float('inf')), axis=1)]

    fig = px.box(
        filtrado,
        x=agrupador,
        y=coluna_tempo,
        title=titulo,
        color=agrupador,
        labels={coluna_tempo: f'Tempo ({coluna_tempo})'},
        color_discrete_map=modelo_cor if agrupador == 'Montadora' else None
    )

    fig.update_layout(
        title=dict(text=titulo, font=dict(size=24), x=0.5, xanchor='center'),
        xaxis_title=agrupador,
        yaxis_title=f'Tempo {titulo}'
    )
    return fig


def processar_gap_st(df):
    """
    Processa o DataFrame bruto para gerar um novo com colunas:
    Piloto, Time of Day, ST, GAP, ST_next, Lap

    GAP: diferença em segundos para o piloto imediatamente mais rápido na mesma volta.
    """

    results = []
    current_pilot = None

    # Extrair linhas com dados válidos (tempo e ST) e piloto
    for index, row in df.iterrows():
        if isinstance(row[0], str) and "Stock" in row[0]:
            current_pilot = row[0]
        elif isinstance(row[0], str) and ':' in row[0]:
            try:
                time_str = row[0]
                st_value = row[6]  # índice da coluna ST na linha
                lap = row[1]       # número da volta

                results.append((current_pilot, time_str, st_value, lap))
            except Exception:
                continue

    # Criar DataFrame limpo
    cleaned_df = pd.DataFrame(
        results, columns=['Piloto', 'Time of Day', 'ST', 'Lap'])

    # Limpar nome do piloto
    cleaned_df['Piloto'] = (
        cleaned_df['Piloto']
        .str.replace(' - Stock Car PRO 2024', '', regex=False)
        .str.replace(' - Stock Car Pro Rookie', '', regex=False)
        .str.replace(' - Stock Car Pro', '', regex=False)
        .str.strip()
        .str.title()
    )

    # Converter 'Time of Day' para datetime
    cleaned_df['Time of Day'] = pd.to_datetime(
        cleaned_df['Time of Day'], errors='coerce')

    # Remover linhas inválidas
    cleaned_df = cleaned_df.dropna(subset=['Time of Day'])

    # Ordenar por volta e tempo para calcular GAP entre pilotos na mesma volta
    cleaned_df = cleaned_df.sort_values(
        ['Lap', 'Time of Day']).reset_index(drop=True)

    # Calcular GAP: diferença para o piloto anterior na mesma volta
    # Usamos groupby em 'Lap' e ordenamos por 'Time of Day'
    cleaned_df['GAP'] = cleaned_df.groupby(
        'Lap')['Time of Day'].diff().dt.total_seconds()

    # Preencher GAP da primeira posição de cada volta com zero
    cleaned_df['GAP'] = cleaned_df['GAP'].fillna(0)

    # Agora ordenar por piloto e tempo para calcular ST_next (velocidade próxima volta)
    cleaned_df = cleaned_df.sort_values(
        ['Piloto', 'Lap']).reset_index(drop=True)
    cleaned_df['ST_next'] = cleaned_df.groupby('Piloto')['ST'].shift(-1)

    # Remover última volta que não tem ST_next
    cleaned_df = cleaned_df.dropna(subset=['ST_next']).reset_index(drop=True)

    # Número da volta já está na coluna 'Lap', mas pode garantir sequencial para cada piloto
    cleaned_df['Lap'] = cleaned_df['Lap'].astype(int)

    return cleaned_df


def gerar_grafico_gap_vs_st(filtered_data, piloto, show_trend=False):
    fig = go.Figure()

    # Scatter dos dados
    fig.add_trace(go.Scatter(
        x=filtered_data['GAP'],
        y=filtered_data['ST_next'],
        mode='markers',
        marker=dict(size=10, opacity=0.7, line=dict(
            width=1, color='DarkSlateGrey')),
        name='Dados'
    ))

    # Adiciona trend line se checkbox estiver marcado
    if show_trend and not filtered_data.empty:
        # Regressão linear simples
        x = filtered_data['GAP']
        y = filtered_data['ST_next']
        coeffs = np.polyfit(x, y, 1)
        trend_y = np.polyval(coeffs, x)

        fig.add_trace(go.Scatter(
            x=x,
            y=trend_y,
            mode='lines',
            name='Trend Line',
            line=dict(color='red', width=2, dash='dash')
        ))

    fig.update_layout(
        title='GAP x Velocidade',
        title_x=0.45,
        xaxis_title='GAP (s)',
        yaxis_title='Velocidade (ST) (km/h)',
        annotations=[
            dict(
                text=f"{piloto} | Apenas voltas com velocidade ST > 200 km/h",
                xref="paper", yref="paper",
                x=0.5, y=1.08,
                showarrow=False,
                font=dict(size=12, color="gray"),
                align="center"
            )
        ],
        title_font=dict(size=24)
    )
    return fig


def gerar_grafico_gap_vs_volta(filtered_data, piloto):
    fig = go.Figure(data=go.Scatter(
        x=filtered_data['Lap'],
        y=filtered_data['GAP'],
        mode='markers',
        marker=dict(size=8, opacity=0.7, line=dict(
            width=1, color='DarkSlateGrey'))
    ))

    fig.update_layout(
        title='GAP x Número da Volta',
        title_x=0.45,
        xaxis_title='Número da Volta',
        yaxis_title='GAP (s)',
        title_font=dict(size=24)  # Definindo o tamanho do título aqui
    )
    return fig


def montar_dataframe_resultado_corrida(driver_info, equipes_pilotos):
    """Gera o dataframe final do resultado da corrida com base nas voltas de cada piloto."""
    dados_resultado = []

    for piloto, df_piloto in driver_info.items():
        if not df_piloto.empty:
            ultima_volta = df_piloto['Lap'].max()
            equipe = equipes_pilotos.get(piloto, 'Desconhecida')
            dados_resultado.append(
                {'Piloto': piloto, 'Equipe': equipe, 'Voltas': ultima_volta})

    df_resultado = pd.DataFrame(dados_resultado)

    # Ordena do maior para menor número de voltas
    df_resultado = df_resultado.sort_values(
        by='Voltas', ascending=False).reset_index(drop=True)

    # Adiciona coluna de posição
    df_resultado.insert(0, 'Posição', df_resultado.index + 1)

    return df_resultado


def colorir_piloto(row):
    color_map = {
        '83 - Gabriel Casagrande': 'background-color: purple; color: white;',
        '12 - Lucas Foresti': 'background-color: gray; color: white;',
        '30 - Cesar Ramos': 'background-color: yellow; color: black;',
        '21 - Thiago Camilo': 'background-color: red; color: white;',
    }

    piloto = row['Piloto']
    style = color_map.get(piloto, '')
    return [style] * len(row)


def criar_matriz_velocidades(driver_info: dict) -> pd.DataFrame:
    """
    Cria um DataFrame onde cada coluna representa um piloto
    e cada linha representa uma velocidade ST, ordenadas do maior para o menor.
    """
    colunas = []

    for piloto, df in driver_info.items():
        if 'ST' in df.columns:
            st_sorted = df['ST'].dropna().astype(float).sort_values(
                ascending=False).reset_index(drop=True)
            # renomeia a Series com o nome do piloto
            colunas.append(st_sorted.rename(piloto))

    # Junta todas as colunas em um DataFrame, alinhando por índice
    df_velocidades = pd.concat(colunas, axis=1)

    # Ordena as colunas pelo número do carro (antes do ' - ')
    def extrair_numero(piloto):
        try:
            return int(piloto.split(' - ')[0])
        except:
            return float('inf')

    df_velocidades = df_velocidades[sorted(
        df_velocidades.columns, key=extrair_numero)]

    return df_velocidades


def formatar_st_com_cores_interativo(df: pd.DataFrame) -> Styler:
    """
    Aplica formatação condicional em uma matriz de velocidades ST:
    - O valor máximo (verde claro) é fixo (maior valor do DataFrame).
    - O valor mínimo (vermelho escuro) pode ser ajustado pelo usuário.
    - Exibe os valores com uma casa decimal mantendo tipo float.
    """
    # Define o valor máximo absoluto
    max_val = df.max().max()

    # Input para o valor mínimo (usuário ajusta)
    min_val = st.number_input(
        "Defina o valor mínimo de destaque (vermelho escuro)",
        min_value=0.0,
        max_value=max_val - 1,
        value=max_val - 20,
        step=0.5
    )

    # Função de normalização baseada em min_val fixo e max_val fixo
    def normalize_val(x):
        if pd.isna(x):
            return None
        if x < min_val:
            return 0.0
        if x > max_val:
            return 1.0
        return (x - min_val) / (max_val - min_val)

    # Aplica a normalização a cada elemento do DataFrame usando map
    gmap = df.apply(lambda col: col.map(normalize_val))

    # Colormap padrão
    cmap = plt.cm.get_cmap('RdYlGn')

    # Aplica estilo e retorna
    styled = df.style.background_gradient(
        cmap=cmap, gmap=gmap, axis=None).format(precision=1)
    return styled


def preparar_dados_boxplot(driver_info: dict, piloto_modelo: dict) -> pd.DataFrame:
    """
    Prepara um DataFrame longo para boxplot, removendo outliers com ST < max(ST) * 0.85.
    """
    registros = []

    for piloto, df_piloto in driver_info.items():
        modelo = piloto_modelo.get(piloto, 'Desconhecido')
        for st in df_piloto['ST']:
            registros.append({'Piloto': piloto, 'ST': st, 'Montadora': modelo})

    df = pd.DataFrame(registros)

    # Remove valores ST considerados muito baixos (outliers)
    max_st = df['ST'].max()
    limite_minimo = max_st * 0.85
    df_filtrado = df[df['ST'] >= limite_minimo]

    return df_filtrado


def gerar_boxplot_st(df_filtrado: pd.DataFrame) -> px.box:
    """
    Gera boxplot de ST por piloto, colorido pela montadora com cores fixas.
    """
    fig = px.box(
        df_filtrado,
        x='Piloto',
        y='ST',
        color='Montadora',
        title='Distribuição de Velocidade por Piloto',
        labels={'ST': 'Velocidade (ST)', 'Piloto': 'Piloto'},
        points='all',
        color_discrete_map=modelo_cor  # Aplica as cores fixas
    )

    fig.update_layout(
        title_x=0.38,
        annotations=[  # Adicionando a anotação
            dict(
                text="Clique e arraste o eixo Y para alterar a escala",
                xref="paper", yref="paper",
                x=0.5, y=1.08,
                showarrow=False,
                font=dict(size=12, color="gray"),
                align="center"
            )
        ]
    )

    return fig


def calcular_st_maior_e_media(df: dict) -> pd.DataFrame:
    """
    Calcula o maior ST e a média dos 5 maiores ST registrados para cada piloto.

    :param df: Dicionário contendo os dados dos pilotos, organizado por piloto.
    :return: DataFrame com as colunas 'Piloto', 'Maior ST' e 'Média dos 5 maiores ST'.
    """
    dados = []

    for piloto, info in df.items():
        st_values = info['ST'].dropna().values

        if len(st_values) > 0:
            maior_st = st_values.max()
            top_5 = sorted(st_values, reverse=True)[:5]
            media_top_5 = np.mean(top_5)

            dados.append({
                'Piloto': piloto,
                'Maior ST': maior_st,
                'Média dos 5 maiores ST': media_top_5
            })

    return pd.DataFrame(dados)


def plotar_maior_st(df: pd.DataFrame, modelo_cor: dict, esquema_cores: str = 'Montadora') -> go.Figure:
    """
    Cria o gráfico de barras para o maior ST registrado de cada piloto, colorido por montadora ou padrão Amattheis.

    :param df: DataFrame com as colunas 'Piloto' e 'Maior ST'.
    :param modelo_cor: Dicionário de cores por montadora.
    :param esquema_cores: Esquema de cores ('Montadora' ou 'Padrão Amattheis').
    :return: Gráfico de barras.
    """
    # Ordena os dados do maior para o menor
    df = df.sort_values(by='Maior ST', ascending=False)

    # Calcular o valor máximo e o valor mínimo para o eixo Y
    y_max = max(df['Maior ST']) * 1.01  # Margem de 1% sobre o maior valor
    y_min = y_max - 15  # Subtrair 15 unidades do valor máximo

    fig = go.Figure()

    # Determinar cores conforme o esquema selecionado
    if esquema_cores == 'Padrão Amattheis':
        # Padrão Amattheis: todos em silver, exceto os pilotos Amattheis destacados
        cores = [pilotos_cor_amattheis.get(piloto, 'silver') for piloto in df['Piloto']]
    else:
        # Padrão: cores por montadora
        cores = [modelo_cor.get(modelo, 'gray') for modelo in df['Piloto'].apply(
            lambda x: piloto_modelo.get(x, 'Desconhecido'))]

    # Adicionar barra para o maior ST
    fig.add_trace(go.Bar(
        x=df['Piloto'],
        y=df['Maior ST'],
        name='Maior ST',
        marker_color=cores,
        text=df['Maior ST'],
        hoverinfo='text',
        width=0.7
    ))

    # Atualizar layout com a escala do eixo Y
    fig.update_layout(
        title='Maior ST Registrado para Cada Piloto',
        xaxis_title='Piloto',
        title_x=0.41,
        yaxis_title='ST (km/h)',
        yaxis=dict(
            range=[y_min, y_max]  # Define a escala do eixo Y
        ),
        height=500,
        xaxis_tickangle=-45,
        showlegend=False,
        margin=dict(t=40, b=100, l=60, r=40),
        annotations=[  # Adicionando a anotação
            dict(
                text="Clique e arraste o eixo Y para alterar a escala",
                xref="paper", yref="paper",
                x=0.5, y=1.05,
                showarrow=False,
                font=dict(size=12, color="gray"),
                align="center"
            )
        ]
    )

    return fig


def plotar_media_top_5_st(df: pd.DataFrame, modelo_cor: dict, esquema_cores: str = 'Montadora') -> go.Figure:
    """
    Cria o gráfico de barras para a média dos 5 maiores ST registrados de cada piloto, colorido por montadora ou padrão Amattheis.

    :param df: DataFrame com as colunas 'Piloto' e 'Média dos 5 maiores ST'.
    :param modelo_cor: Dicionário de cores por montadora.
    :param esquema_cores: Esquema de cores ('Montadora' ou 'Padrão Amattheis').
    :return: Gráfico de barras.
    """
    # Arredondar a média dos 5 maiores ST para 1 casa decimal
    df['Média dos 5 maiores ST'] = df['Média dos 5 maiores ST'].round(1)

    # Ordena os dados do maior para o menor
    df = df.sort_values(by='Média dos 5 maiores ST', ascending=False)

    # Calcular o valor máximo e o valor mínimo para o eixo Y
    y_max = max(df['Média dos 5 maiores ST']) * \
        1.01  # Margem de 1% sobre o maior valor
    y_min = y_max - 15  # Subtrair 15 unidades do valor máximo

    fig = go.Figure()

    # Determinar cores conforme o esquema selecionado
    if esquema_cores == 'Padrão Amattheis':
        # Padrão Amattheis: todos em silver, exceto os pilotos Amattheis destacados
        cores = [pilotos_cor_amattheis.get(piloto, 'silver') for piloto in df['Piloto']]
    else:
        # Padrão: cores por montadora
        cores = [modelo_cor.get(modelo, 'gray') for modelo in df['Piloto'].apply(
            lambda x: piloto_modelo.get(x, 'Desconhecido'))]

    # Adicionar barra para a média dos 5 maiores ST
    fig.add_trace(go.Bar(
        x=df['Piloto'],
        y=df['Média dos 5 maiores ST'],
        name='Média dos 5 Maiores ST',
        marker_color=cores,
        text=df['Média dos 5 maiores ST'],
        hoverinfo='text',
        width=0.7
    ))

    # Atualizar layout com a escala do eixo Y
    fig.update_layout(
        title='Média dos 5 Maiores ST Registrados para Cada Piloto',
        xaxis_title='Piloto',
        title_x=0.38,
        yaxis_title='ST (km/h)',
        yaxis=dict(
            range=[y_min, y_max]  # Define a escala do eixo Y
        ),
        height=500,
        xaxis_tickangle=-45,
        showlegend=False,
        margin=dict(t=40, b=100, l=60, r=40),
        annotations=[  # Adicionando a anotação
            dict(
                text="Clique e arraste o eixo Y para alterar a escala",
                xref="paper", yref="paper",
                x=0.5, y=1.05,
                showarrow=False,
                font=dict(size=12, color="gray"),
                align="center"
            )
        ]
    )

    return fig


def gerar_relatorio_completo_speed_report(df_st, df_matriz_st, fig_box, fig_maior_st, fig_media_top_5_st,
                                          nome_arquivo="relatorio_speed_report_completo.pdf"):
    """
    Gera um relatório PDF com título, tabela, e gráficos do Speed Report.

    Args:
        df_st (pd.DataFrame): DataFrame com maior e média ST.
        df_matriz_st (pd.DataFrame): Matriz de ST.
        fig_box: Boxplot gerado com Plotly.
        fig_maior_st: Gráfico com maior ST.
        fig_media_top_5_st: Gráfico com média das 5 maiores ST.
        nome_arquivo (str): Nome do arquivo gerado (padrão: relatorio_speed_report_completo.pdf).

    Returns:
        str: Caminho do arquivo PDF gerado.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        box_path = os.path.join(temp_dir, "boxplot.png")
        maior_path = os.path.join(temp_dir, "maior_st.png")
        media_path = os.path.join(temp_dir, "media_top5_st.png")

        pio.write_image(fig_box, box_path, format='png', scale=2)
        pio.write_image(fig_maior_st, maior_path, format='png', scale=2)
        pio.write_image(fig_media_top_5_st, media_path, format='png', scale=2)

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "Speed Report - Relatório Completo", ln=True, align='C')

        pdf.set_font("Arial", size=12)
        pdf.ln(8)
        pdf.multi_cell(
            0, 10, "Este relatório contém uma análise detalhada das velocidades ST registradas na corrida.")

        pdf.ln(8)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Resumo de ST por Piloto", ln=True)
        pdf.set_font("Arial", size=10)
        for idx, row in df_st.iterrows():
            pdf.cell(
                0, 8, f"{row['Piloto']}: Maior ST = {row['Maior ST']:.1f}, Média Top 5 ST = {row['Média dos 5 maiores ST']:.1f}", ln=True)

        pdf.ln(10)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Boxplot por Montadora", ln=True)
        pdf.image(box_path, w=180)

        pdf.ln(10)
        pdf.cell(0, 10, "Maior ST por Piloto", ln=True)
        pdf.image(maior_path, w=180)

        pdf.ln(10)
        pdf.cell(0, 10, "Média das 5 maiores ST por Piloto", ln=True)
        pdf.image(media_path, w=180)

        output_path = os.path.join(os.getcwd(), nome_arquivo)
        pdf.output(output_path)
        return output_path


def gerar_boxplot_laptimes(df: pd.DataFrame, modelo_cor: dict, multiplicador_outlier: float):
    """Gera o boxplot dos laptimes dos pilotos, com filtragem interativa de outliers.

    Argumentos:
        df (pd.DataFrame): DataFrame com os tempos de volta dos pilotos.
        modelo_cor (dict): Dicionário com as cores associadas a cada montadora.
        multiplicador_outlier (float): Fator de multiplicação para definir o limite do outlier.

    Retorno:
        go.Figure: Gráfico box plot gerado com Plotly.
    """
    # Converte os tempos de volta para segundos, caso não tenha sido feito
    if 'Lap_seconds' not in df.columns:
        df['Lap_seconds'] = df['Lap Tm'].apply(convert_time_to_seconds)

    # Verifica se há valores NaN e os descarta
    df = df.dropna(subset=['Lap_seconds'])

    # Calcula o melhor tempo por montadora
    melhores = df.groupby('Montadora')['Lap_seconds'].min()
    limites = melhores * multiplicador_outlier

    # Filtra os dados, removendo os outliers
    filtrado = df[df.apply(lambda x: x['Lap_seconds'] <=
                           limites.get(x['Montadora'], float('inf')), axis=1)]

    # Cria o boxplot
    fig = px.box(
        filtrado,
        x='Piloto',
        y='Lap_seconds',  # Usando a coluna 'Lap_seconds' no eixo Y
        title="Box Plot - Laptimes por Piloto",
        color='Montadora',
        color_discrete_map=modelo_cor,
        labels={'Lap_seconds': 'Tempo de Volta (s)', 'Piloto': 'Piloto'}
    )

    fig.update_layout(
        title=dict(text="Box Plot - Laptimes por Piloto",
                   font=dict(size=24), x=0.5, xanchor='center'),
        xaxis_title="Piloto",
        yaxis_title="Tempo de Volta (s)",
        showlegend=True,
        height=600
    )

    return fig


def gerar_boxplot_laptimes_sem_cor(df: pd.DataFrame, multiplicador_outlier: float):
    """Gera o boxplot dos laptimes dos pilotos, com filtragem interativa de outliers, sem coloração por montadora.

    Argumentos:
        df (pd.DataFrame): DataFrame com os tempos de volta dos pilotos.
        multiplicador_outlier (float): Fator de multiplicação para definir o limite do outlier.

    Retorno:
        go.Figure: Gráfico box plot gerado com Plotly.
    """
    # Converte os tempos de volta para segundos, caso não tenha sido feito
    if 'Lap_seconds' not in df.columns:
        df['Lap_seconds'] = df['Lap Tm'].apply(convert_time_to_seconds)

    # Verifica se há valores NaN e os descarta
    df = df.dropna(subset=['Lap_seconds'])

    # Calcula o melhor tempo por montadora
    melhores = df.groupby('Montadora')['Lap_seconds'].min()
    limites = melhores * multiplicador_outlier

    # Filtra os dados, removendo os outliers
    filtrado = df[df.apply(lambda x: x['Lap_seconds'] <=
                           limites.get(x['Montadora'], float('inf')), axis=1)]

    # Cria o boxplot sem coloração por montadora
    fig = px.box(
        filtrado,
        x='Piloto',
        y='Lap_seconds',  # Usando a coluna 'Lap_seconds' no eixo Y
        title="Box Plot - Laptimes por Piloto (Sem Cor por Montadora)",
        labels={'Lap_seconds': 'Tempo de Volta (s)', 'Piloto': 'Piloto'},
        color='Piloto'
    )

    fig.update_layout(
        title=dict(text="Box Plot - Laptimes por Piloto (Sem Cor)",
                   font=dict(size=24), x=0.5, xanchor='center'),
        xaxis_title="Piloto",
        yaxis_title="Tempo de Volta (s)",
        showlegend=False,
        height=600
    )

    return fig


def gerar_grafico_laptimes_por_volta(driver_info: dict) -> go.Figure:
    """
    Gera um gráfico de linha com o tempo de volta (em segundos) por volta para cada piloto.

    Args:
        driver_info (dict): Dicionário com dados dos pilotos extraído pela função `separar_pilotos_por_volta`.

    Returns:
        go.Figure: Gráfico de linha (Plotly) com voltas no eixo X e tempo de volta no eixo Y.
    """
    fig = go.Figure()

    for piloto, df_piloto in driver_info.items():
        df_temp = df_piloto.copy()
        df_temp['Lap_Tm_Segundos'] = df_temp['Lap Tm'].apply(
            convert_time_to_seconds)
        df_temp = df_temp.dropna(subset=['Lap_Tm_Segundos'])

        fig.add_trace(go.Scatter(
            x=df_temp['Lap'],
            y=df_temp['Lap_Tm_Segundos'],
            mode='lines+markers',
            name=piloto
        ))

    fig.update_layout(
        title="Ritmo de Corrida por Volta",
        xaxis_title='Volta',
        yaxis_title='Tempo de Volta (s)',
        height=600,
        hovermode='x unified',
        title_x=0.38,
        annotations=[
            dict(
                text=f"Clique e arraste o eixo Y para alterar a escala",
                xref="paper", yref="paper",
                x=0.5, y=1.08,
                showarrow=False,
                font=dict(size=12, color="gray"),
                align="center"
            )
        ]
    )

    return fig


def gerar_grafico_gap_para_piloto_referencia(df_completo: pd.DataFrame, piloto_modelo: dict = None):
    """
    Gera gráfico de linha com o GAP por volta de cada piloto em relação a um piloto de referência.

    Args:
        df_completo (pd.DataFrame): DataFrame com todas as voltas e tempos de cada piloto.
        piloto_modelo (dict, opcional): Dicionário com mapeamento de pilotos e suas montadoras (para uso futuro).

    Returns:
        fig (go.Figure): Gráfico Plotly com o GAP entre os pilotos e o piloto de referência.
        pilotos (list): Lista de pilotos para seleção externa (usado no Streamlit).
    """
    # Lista de pilotos disponíveis
    pilotos = df_completo['Piloto'].unique().tolist()

    # Função interna para gerar o gráfico do GAP para o piloto de referência selecionado
    def gerar_figura_para_piloto_referencia(reference_pilot: str):
        if not reference_pilot or reference_pilot not in pilotos:
            return None

        # Filtra os dados do piloto de referência
        reference_times = df_completo[df_completo['Piloto'] == reference_pilot]
        if reference_times.empty:
            return None

        # Mapeia os tempos do piloto de referência por volta
        reference_time_dict = reference_times.set_index(
            'Lap')['Lap_seconds'].to_dict()

        # Calcula o GAP para todos os pilotos em relação ao piloto de referência
        df_copy = df_completo.copy()
        df_copy['Reference Time'] = df_copy['Lap'].map(reference_time_dict)
        df_copy['GAP to Reference'] = df_copy['Lap_seconds'] - \
            df_copy['Reference Time']

        # Cria o gráfico de linha para o GAP
        fig = px.line(
            df_copy,
            x='Lap',
            y='GAP to Reference',
            color='Piloto',
            title=f'GAP por Volta em Relação a {reference_pilot}',
            labels={'Lap': 'Volta', 'GAP to Reference': 'GAP (s)'},
            markers=True
        )

        # Personaliza o layout do gráfico
        fig.update_layout(title_x=0.38)
        fig.update_traces(mode='lines+markers',
                          marker=dict(size=6, opacity=0.7))

        return fig

    # Retorna a função para o gráfico e a lista de pilotos
    return gerar_figura_para_piloto_referencia, pilotos


def gerar_ranking_por_volta(df: pd.DataFrame) -> pd.DataFrame:
    """
    Gera o ranking por volta com base na coluna 'Lap_seconds'.

    Args:
        df (pd.DataFrame): DataFrame com colunas ['Piloto', 'Lap', 'Lap_seconds'].

    Returns:
        pd.DataFrame: Ranking por volta com colunas ['Piloto', 'Lap', 'Lap_seconds', 'Rank'].
    """
    rankings = []
    for lap in sorted(df['Lap'].dropna().unique()):
        lap_df = df[df['Lap'] == lap].copy()
        lap_df = lap_df.sort_values(by='Lap_seconds')
        lap_df['Rank'] = range(1, len(lap_df) + 1)
        rankings.append(lap_df[['Piloto', 'Lap', 'Lap_seconds', 'Rank']])

    return pd.concat(rankings, ignore_index=True)


def imagem_base64(imagem_path):
    img = Image.open(imagem_path)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    img_b64 = base64.b64encode(buffer.getvalue()).decode()
    return img_b64


def criar_matriz_velocidades_numeral(driver_info: dict) -> pd.DataFrame:
    """
    Cria um DataFrame onde cada coluna representa um piloto,
    e cada linha representa uma velocidade ST, ordenadas do maior para o menor.
    Os cabeçalhos das colunas terão apenas o numeral do piloto.
    """
    colunas = []

    for piloto, df in driver_info.items():
        if 'ST' in df.columns:
            st_sorted = df['ST'].dropna().astype(float).sort_values(
                ascending=False).reset_index(drop=True)

            # Extrai apenas o número do piloto (antes do ' - ')
            try:
                numeral = int(piloto.split(' - ')[0])
            except:
                numeral = piloto  # fallback, em caso de formato inesperado

            colunas.append(st_sorted.rename(numeral))

    # Junta todas as colunas em um DataFrame, alinhando por índice
    df_velocidades = pd.concat(colunas, axis=1)

    # Ordena as colunas pelo número do carro
    df_velocidades = df_velocidades[sorted(df_velocidades.columns)]

    return df_velocidades


def filtrar_gap(df, limite_gap):
    """Filtra os dados para mostrar apenas os pilotos com GAP menor que o limite especificado."""
    # Filtra os dados com base no limite de GAP
    df_filtrado = df[df['GAP'] > limite_gap]
    return df_filtrado


def calcular_raising_average_st(driver_info: dict) -> dict:
    """
    Calcula o raising average de ST (Speed Trap) para cada piloto.

    :param driver_info: Dicionário com os dados de cada piloto.
    :return: Dicionário com piloto como chave e lista de médias progressivas como valor.
    """
    resultado = {}

    for piloto, df in driver_info.items():
        st_vals = pd.to_numeric(df['ST'], errors='coerce').dropna()
        if len(st_vals) == 0:
            continue
        st_ordenado = st_vals.sort_values(
            ascending=False).reset_index(drop=True)
        medias = [st_ordenado[:i].mean() for i in range(1, len(st_ordenado)+1)]
        resultado[piloto] = medias

    return resultado


def plotar_raising_average_st(
    raising_dict: dict,
    piloto_modelo: dict,
    modelo_cor: dict,
    colorir_por: str = "montadora",
    pilotos_cor: dict = None
) -> go.Figure:
    """
    Plota o gráfico de raising average de ST para todos os pilotos.

    :param raising_dict: Dicionário {piloto: lista de médias}.
    :param piloto_modelo: Dicionário com modelo de carro por piloto.
    :param modelo_cor: Dicionário com cores por modelo de carro.
    :param colorir_por: 'padrão amattheis', 'montadora' ou 'piloto'.
    :param pilotos_cor: Dicionário com cores por piloto.
    :return: Gráfico Plotly.
    """
    fig = go.Figure()

    for piloto, medias in raising_dict.items():
        if colorir_por == "padrão amattheis":
            # Padrão Amattheis: todos em silver, exceto os pilotos Amattheis destacados
            cor = pilotos_cor_amattheis.get(piloto, 'silver')
        elif colorir_por == "montadora":
            modelo = piloto_modelo.get(piloto, "Desconhecido")
            cor = modelo_cor.get(modelo, 'gray')
        else:  # "piloto"
            cor = pilotos_cor.get(piloto, 'gray') if pilotos_cor else 'gray'

        fig.add_trace(go.Scatter(
            x=list(range(1, len(medias)+1)),
            y=medias,
            mode='lines+markers',
            name=piloto,
            line=dict(color=cor),
            hovertemplate=f'Voltas: %{{x}}<br>Média ST: %{{y:.1f}}<extra>{piloto}</extra>'
        ))

    fig.update_layout(
        title='Raising Average de ST por Piloto',
        title_x=0.4,
        yaxis_title='Média das X Maiores Velocidades (km/h)',
        height=600,
        legend=dict(title='Piloto'),
        margin=dict(t=50, b=80, l=60, r=60)
    )

    return fig
