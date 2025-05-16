import pandas as pd
from functions.constants import piloto_modelo, modelo_cor
import plotly.express as px
import plotly.graph_objects as go


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
    """
    results = []
    current_pilot = None

    # Itera sobre as linhas
    for index, row in df.iterrows():
        if "Stock" in row[0]:  # Nome do piloto na coluna 'Time of Day'
            current_pilot = row[0]
        elif isinstance(row[0], str) and ':' in row[0]:  # Se for um tempo válido
            try:
                time = pd.to_timedelta(row[0])
                st_value = row[6]  # Corrigido para coluna 6
                results.append((current_pilot, time, st_value))
            except Exception:
                continue

    # Criar DataFrame limpo
    cleaned_df = pd.DataFrame(results, columns=['Piloto', 'Time of Day', 'ST'])

    # Limpar nome do piloto
    cleaned_df['Piloto'] = cleaned_df['Piloto'].str.replace(
        ' - Stock Car PRO 2024', '', regex=False
    ).str.replace(
        ' - Stock Car Pro Rookie', '', regex=False
    ).str.replace(
        ' - Stock Car Pro', '', regex=False
    ).str.strip().str.title()

    # Ordenar e calcular GAP
    cleaned_df = cleaned_df.sort_values(
        by='Time of Day').reset_index(drop=True)
    cleaned_df['GAP'] = cleaned_df['Time of Day'].diff().dt.total_seconds()

    # Sinalizar velocidade da próxima volta
    cleaned_df['ST_next'] = cleaned_df['ST'].shift(-1)

    # Remover última linha (sem ST_next)
    cleaned_df.dropna(subset=['ST_next'], inplace=True)

    # GAP inicial como zero
    cleaned_df['GAP'].fillna(0, inplace=True)

    # Número da volta
    cleaned_df['Lap'] = cleaned_df.groupby('Piloto').cumcount() + 1

    return cleaned_df


def gerar_grafico_gap_vs_st(filtered_data, piloto):
    fig = go.Figure(data=go.Scatter(
        x=filtered_data['GAP'],
        y=filtered_data['ST_next'],
        mode='markers',
        marker=dict(size=10, opacity=0.7, line=dict(
            width=1, color='DarkSlateGrey'))
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
        title_font=dict(size=24)  # Definindo o tamanho do título aqui
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
        title_font=dict(size=24)  # Definindo o tamanho do título aqui
    )
    return fig
