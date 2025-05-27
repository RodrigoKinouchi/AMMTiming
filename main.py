import pandas as pd
import streamlit as st
import plotly.express as px
from PIL import Image
import re
from functions.utils import normalizar_coluna_velocidade, separar_pilotos_por_volta, maior_velocidade_por_piloto,  convert_time_to_seconds, processar_resultado_csv, montar_dataframe_completo, gerar_boxplot_setor, processar_gap_st, gerar_grafico_gap_vs_st, gerar_grafico_gap_vs_volta, montar_dataframe_resultado_corrida, colorir_piloto, criar_matriz_velocidades, formatar_st_com_cores_interativo, preparar_dados_boxplot, gerar_boxplot_st, calcular_st_maior_e_media, plotar_maior_st, plotar_media_top_5_st, gerar_relatorio_completo_speed_report, gerar_ranking_st, gerar_boxplot_laptimes_sem_cor, gerar_boxplot_laptimes, gerar_grafico_laptimes_por_volta, gerar_grafico_gap_para_piloto_referencia, gerar_ranking_por_volta, imagem_base64, criar_matriz_velocidades_numeral, filtrar_gap
from functions.constants import pilotos_cor, equipes_pilotos, equipes_cor, modelo_cor, piloto_modelo
import plotly.graph_objects as go

# Configurando o título da página URL
st.set_page_config(
    page_title="AMM Timing",
    page_icon="⏱️",
    layout="wide",
    initial_sidebar_state="expanded")

# Carrega e converte imagem do carro
carro_b64 = imagem_base64("images/carro.png")

# === CSS das faixas e do carro ===
st.markdown(f"""
    <style>
    /* Container com as faixas e imagem */
    .decoration-container {{
        position: fixed;
        bottom: 0;
        right: 0;
        width: 300px;
        height: 300px;
        z-index: 0;  /* IMPORTANTE: manter baixo */
        pointer-events: none; /* permite clique nos elementos do app */
    }}

    .faixas {{
        position: absolute;
        bottom: 0;
        right: 0;
        width: 100%;
        height: 100%;
        background: linear-gradient(135deg,
            #0047BA 0%,
            #0047BA 33%,
            #FF6600 33%,
            #FF6600 66%,
            #FFCC00 66%,
            #FFCC00 100%);
        clip-path: polygon(100% 100%, 0% 100%, 100% 0%);
        opacity: 0.5;
    }}

    .carro-img {{
        position: absolute;
        bottom: 0;
        right: 0;
        width: 240px;
        opacity: 0.95;
    }}
    </style>

    <div class="decoration-container">
        <div class="faixas"></div>
        <img src="data:image/png;base64,{carro_b64}" class="carro-img">
    </div>
""", unsafe_allow_html=True)
# Carregando uma imagem
image = Image.open('images/capa.png')

# Inserindo a imagem na página utilizando os comandos do stremalit
st.image(image, use_container_width=True)
st.write("")

opcao = st.radio("Selecione uma opção:", ("Corrida", "Treino"))

uploaded_file = st.file_uploader("Escolha um arquivo CSV", type="csv")

if uploaded_file is not None:
    try:
        # Leitura do arquivo CSV
        df = pd.read_csv(uploaded_file)

    except Exception as e:
        st.error(f"Ocorreu um erro ao processar o arquivo: {e}")

    try:
        df = normalizar_coluna_velocidade(df)
    except ValueError as e:
        st.error(str(e))
        st.stop()

    df = df[['Time of Day', 'Lap', 'Lap Tm', 'S1 Tm', 'S2 Tm', 'S3 Tm', 'ST']]
    # Trocando virgula por ponto e transformando os tempos de volta em float
    df['ST'] = df['ST'].str.replace(',', '.').astype(float)
    driver_info = separar_pilotos_por_volta(df)
    top_speed = maior_velocidade_por_piloto(driver_info)

    if opcao == "Treino":

        tabs = st.tabs(
            ['Resultado', 'Speed', 'Laptimes', 'Manufacturer', 'Teams', 'Speed x GAP'])

        with tabs[0]:
            # Processa o resultado do Qualy
            df_resultado = processar_resultado_csv(df)

            # Exibe o DataFrame no Streamlit
            st.dataframe(df_resultado, hide_index=True)

        with tabs[1]:
            # Criação das colunas para ordenação e filtro de GAP
            col1, col2, col3 = st.columns([6, 2, 1])

            with col1:
                sort_order = st.radio(
                    "Ordenar por:", ('Resultado', 'Maior Velocidade'))

            with col2:
                is_filtrar_gap = st.checkbox(
                    "Filtrar ST para GAP < x", value=False)

            limite_gap = 0.0
            if is_filtrar_gap:
                limite_gap = st.number_input(
                    "Digite o limite de GAP (em segundos):", min_value=0.0, value=1.0, step=0.1)

            # Processa o DataFrame para incluir o GAP entre voltas
            df_gap = processar_gap_st(df)

            # Aplica o filtro de GAP se ativado
            if is_filtrar_gap:
                df_gap = filtrar_gap(df_gap, limite_gap)
                st.caption(
                    f"{len(df_gap)} voltas consideradas após remover STs com GAP ≤ {limite_gap:.1f}s")

            # Separar pilotos normalmente usando o DataFrame bruto
            driver_info = separar_pilotos_por_volta(df)

            # Se o filtro estiver ativado, manter apenas as voltas cujos tempos estão em df_gap
            if is_filtrar_gap:
                # Criar novo driver_info apenas com voltas filtradas
                driver_info_filtrado = {
                    piloto: voltas[voltas['Lap'].isin(
                        df_gap[df_gap['Piloto'] == piloto]['Lap'])]
                    for piloto, voltas in driver_info.items()
                    if piloto in df_gap['Piloto'].unique()
                }
            else:
                driver_info_filtrado = driver_info

            # Calcula as maiores velocidades com os dados filtrados
            top_speed = maior_velocidade_por_piloto(driver_info_filtrado)

            # Limpa os nomes dos pilotos
            pilotos_limpos = {re.sub(r' - Stock Car Pro( Rookie|)', '', piloto): velocidade
                              for piloto, velocidade in top_speed.items()}

            pilotos = list(pilotos_limpos.keys())
            velocidades_max = list(pilotos_limpos.values())

            # Ordena os dados conforme seleção
            if sort_order == 'Maior Velocidade':
                sorted_pilotos = sorted(
                    zip(pilotos, velocidades_max), key=lambda x: x[1], reverse=True)
            else:
                sorted_pilotos = zip(pilotos, velocidades_max)

            pilotos, velocidades_max = zip(*sorted_pilotos)

            # Escala eixo Y
            y_max = max(velocidades_max) * 1.01
            y_min = y_max - 15

            # Cores por equipe
            cores = []
            legendas = []
            for piloto in pilotos:
                equipe = equipes_pilotos.get(piloto)
                cor = equipes_cor.get(equipe, 'gray')
                cores.append(cor)
                legendas.append(equipe)

            # Gráfico por equipe
            fig = go.Figure()
            barras_adicionadas = set()
            for piloto, velocidade, equipe, cor in zip(pilotos, velocidades_max, legendas, cores):
                show_legend = equipe not in barras_adicionadas
                barras_adicionadas.add(equipe)
                fig.add_trace(go.Bar(
                    x=[piloto],
                    y=[velocidade],
                    name=equipe if show_legend else None,
                    marker_color=cor,
                    width=[0.6],
                    showlegend=show_legend
                ))

            fig.update_layout(
                title="<b>Top speed</b><br><span style='font-size:12px; color:gray;'>Clique e arraste o eixo Y para alterar a escala</span>",
                title_x=0.4,
                xaxis_title='Piloto',
                yaxis_title='Velocidade Máxima (km/h)',
                yaxis=dict(range=[y_min, y_max]),
                height=600,
                barmode='group',
                legend_title_text='Equipe'
            )
            st.plotly_chart(fig)

            # Gráfico por modelo de carro
            cores_modelo = []
            modelos_carro = []
            for piloto in pilotos:
                modelo = piloto_modelo.get(piloto, 'Desconhecido')
                cor = modelo_cor.get(modelo, 'gray')
                cores_modelo.append(cor)
                modelos_carro.append(modelo)

            fig_modelo = go.Figure()
            barras_adicionadas_modelo = set()
            for piloto, velocidade, modelo, cor in zip(pilotos, velocidades_max, modelos_carro, cores_modelo):
                show_legend = modelo not in barras_adicionadas_modelo
                barras_adicionadas_modelo.add(modelo)
                fig_modelo.add_trace(go.Bar(
                    x=[piloto],
                    y=[velocidade],
                    name=modelo if show_legend else None,
                    marker_color=cor,
                    width=[0.6],
                    showlegend=show_legend
                ))

            fig_modelo.update_layout(
                title="<b>Top speed por marca</b><br><span style='font-size:12px; color:gray;'>Clique e arraste o eixo Y para alterar a escala</span>",
                title_x=0.4,
                xaxis_title='Piloto',
                yaxis_title='Velocidade Máxima (km/h)',
                yaxis=dict(range=[y_min, y_max]),
                height=600,
                barmode='group',
                legend_title_text='Marca'
            )
            st.plotly_chart(fig_modelo)

            # Obter os dados de ST por piloto (todos os tempos registrados, não só o maior)
            driver_info = separar_pilotos_por_volta(
                df)  # Separando os dados por piloto

            # Chama a função para gerar o ranking ST
            df_ranking_st = gerar_ranking_st(
                driver_info, modelo_cor, piloto_modelo, top_n=30)

            df_ranking_st = df_ranking_st.format({'ST': '{:.1f}'})

            # Exibir o ranking de ST no Streamlit
            st.dataframe(df_ranking_st, use_container_width=False,
                         hide_index=True)

            # Cria 3 colunas: vazia, vazia, checkbox à direita
            col1, col2, col3 = st.columns([6, 1, 1])

            with col3:
                mostrar_numerais = st.checkbox(
                    "Somente numerais", value=False)

            # Criando a matriz conforme escolha
            if mostrar_numerais:
                df_matriz_st = criar_matriz_velocidades_numeral(driver_info)
            else:
                df_matriz_st = criar_matriz_velocidades(driver_info)

            # Aplicando a formatação condicional
            df_st_formatado = formatar_st_com_cores_interativo(df_matriz_st)

            # Exibe a matriz com largura total
            st.dataframe(df_st_formatado, use_container_width=True,
                         hide_index=True)

        with tabs[2]:
            piloto_selecionado = st.selectbox(
                "Selecione o piloto", list(driver_info.keys()))

            if piloto_selecionado:
                df_piloto = driver_info[piloto_selecionado].copy()
                df_piloto['Lap_seconds'] = df_piloto['Lap Tm'].apply(
                    convert_time_to_seconds)
                # Cria uma cópia do DataFrame apenas com as colunas que quero exibir
                df_piloto_show = df_piloto.drop(columns=['Lap_seconds'])

                st.dataframe(df_piloto_show, hide_index=True)

                # Filtrar voltas "válidas" (exclui voltas muito lentas como box ou erro)
                valid_laps = df_piloto[(df_piloto['Lap_seconds'] > 60) & (
                    df_piloto['Lap_seconds'] < 200)]

                # Definir valores para o eixo Y com base nas voltas válidas
                if not valid_laps.empty:
                    y_min = valid_laps['Lap_seconds'].min() * 0.98
                    y_max = valid_laps['Lap_seconds'].max() * 1.02
                else:
                    # fallback se todas as voltas forem inválidas
                    y_min, y_max = 80, 200

                fig = px.line(
                    df_piloto,
                    x='Lap',
                    y='Lap_seconds',
                    markers=True,
                    title=f"Tempos de Volta - {piloto_selecionado}",
                    labels={'Lap_seconds': 'Tempo (s)', 'Lap': 'Volta'}
                )

                # Atualiza o layout com o range ajustado
                fig.update_layout(
                    yaxis=dict(range=[y_min, y_max]),
                    title_x=0.4,
                    annotations=[
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
                st.plotly_chart(fig)

        with tabs[3]:
            # Slider para o usuário ajustar o fator de limite de outliers
            limit_factor = st.slider(
                'Selecione o fator de limite (%) acima da melhor volta/setor para filtras os outliers (sugestão baseado em estudos: 2%)',
                min_value=1.01,
                max_value=1.05,
                value=1.02,
                step=0.01,
                format="%.2f"
            )

            # Monta o DataFrame completo com os dados dos pilotos e suas montadoras
            df_completo = montar_dataframe_completo(driver_info)

            setores = {
                'S1 Tm': 'Setor 1',
                'S2 Tm': 'Setor 2',
                'S3 Tm': 'Setor 3',
                'Lap_seconds': 'Laptimes'
            }

            # Gera e exibe os boxplots por setor com base no limit_factor
            for coluna, titulo in setores.items():
                fig = gerar_boxplot_setor(
                    df_completo, coluna, titulo, margem=limit_factor - 1)
                st.plotly_chart(fig, use_container_width=True)

        with tabs[4]:
            # Slider para o limite
            team_limit_factor = st.slider(
                'Selecione o fator de limite (%) acima da melhor volta/setor para filtras os outliers (sugestão baseado em estudos: 2%)',
                min_value=1.01,
                max_value=1.05,
                value=1.02,
                step=0.01,
                format="%.2f",
                key="team_limit_slider"
            )
            st.caption(
                "Voltas acima do limite em relação ao melhor tempo de cada equipe são removidas.")

            # Monta o DataFrame completo com as colunas e adiciona coluna de equipe
            df_teams = montar_dataframe_completo(driver_info)

            df_teams['Equipe'] = df_teams['Piloto'].map(equipes_pilotos)
            df_teams = df_teams.dropna(subset=['Equipe'])

            setores = {
                'S1 Tm': 'Setor 1',
                'S2 Tm': 'Setor 2',
                'S3 Tm': 'Setor 3',
                'Lap_seconds': 'Laptimes'
            }

            for coluna, titulo in setores.items():
                fig = gerar_boxplot_setor(
                    df_teams, coluna, titulo, margem=team_limit_factor - 1, agrupador='Equipe')
                st.plotly_chart(fig, use_container_width=True)

        with tabs[5]:
            # Processa o DataFrame para análise GAP x Speed
            cleaned_df = processar_gap_st(df)

            # Interface Streamlit
            pilotos = cleaned_df['Piloto'].unique().tolist()
            pilotos.insert(0, "")  # Adiciona opção vazia
            selected_pilot = st.selectbox('Selecione um piloto:', pilotos)

            if selected_pilot:
                pilot_data = cleaned_df[cleaned_df['Piloto'] == selected_pilot]
                filtered_data = pilot_data[pilot_data['ST_next'] > 200]

                fig_gap_speed = gerar_grafico_gap_vs_st(
                    filtered_data, selected_pilot)
                st.plotly_chart(fig_gap_speed)

                fig_gap_lap = gerar_grafico_gap_vs_volta(
                    filtered_data, selected_pilot)
                st.plotly_chart(fig_gap_lap)
            else:
                st.warning('Por favor, selecione um piloto.')

    if opcao == "Corrida":

        tabs = st.tabs(['Resultado', 'Speed Report', 'Laptimes', 'Gap Analysis',
                        'Speed x GAP', 'Ranking by lap'])

        with tabs[0]:
            df_resultado_corrida = montar_dataframe_resultado_corrida(
                driver_info, equipes_pilotos)

            st.subheader("Resultado da Corrida")

            # Converte a coluna Voltas para inteiro
            df_resultado_corrida['Voltas'] = df_resultado_corrida['Voltas'].astype(
                int)
            # Aplica o estilo com cor para pilotos específicos
            styled_df = df_resultado_corrida.style.apply(
                colorir_piloto, axis=1)

            # Exibe o DataFrame com cor
            st.dataframe(styled_df, hide_index=True)

        with tabs[1]:
            st.subheader("Speed Report - Matriz de Velocidades (ST)")

            # Criando a matriz
            df_matriz_st = criar_matriz_velocidades(driver_info)

            # Cria 3 colunas: vazia, vazia, checkbox à direita
            col1, col2, col3 = st.columns([6, 1, 1])

            with col3:
                mostrar_numerais = st.checkbox(
                    "Somente numerais", value=False)

            # Criando a matriz conforme escolha
            if mostrar_numerais:
                df_matriz_st = criar_matriz_velocidades_numeral(driver_info)
            else:
                df_matriz_st = criar_matriz_velocidades(driver_info)

            # Aplicando a formatação condicional
            df_st_formatado = formatar_st_com_cores_interativo(df_matriz_st)

            # Exibindo o DataFrame estilizado
            st.dataframe(df_st_formatado,
                         use_container_width=False, hide_index=True)

            # 1. Processa os dados
            df_boxplot = preparar_dados_boxplot(driver_info, piloto_modelo)

            # 2. Cria o gráfico
            fig_box = gerar_boxplot_st(df_boxplot)

            # 3. Mostra no Streamlit
            st.plotly_chart(fig_box, use_container_width=True)

            # Calcular o maior ST e a média dos 5 maiores ST
            df_st = calcular_st_maior_e_media(driver_info)

            # Gerar o gráfico para o maior ST
            fig_maior_st = plotar_maior_st(df_st, modelo_cor)

            # Gerar o gráfico para a média dos 5 maiores ST
            fig_media_top_5_st = plotar_media_top_5_st(df_st, modelo_cor)

            # Exibir os gráficos no Streamlit (se estiver usando Streamlit)
            st.plotly_chart(fig_maior_st)
            st.plotly_chart(fig_media_top_5_st)

            if st.button("📄 Gerar relatório em PDF"):
                caminho_pdf = gerar_relatorio_completo_speed_report(
                    df_st=df_st,
                    df_matriz_st=df_matriz_st,
                    fig_box=fig_box,
                    fig_maior_st=fig_maior_st,
                    fig_media_top_5_st=fig_media_top_5_st
                )
                st.success(f"Relatório gerado com sucesso: {caminho_pdf}")
                with open(caminho_pdf, "rb") as f:
                    st.download_button("📥 Baixar PDF", f,
                                       file_name="relatorio_speed_report.pdf")

        with tabs[2]:
            # Montar o dataframe completo com os tempos de volta
            df_completo = montar_dataframe_completo(driver_info)

            # Adicionar o slider para o multiplicador de outliers (default 1.08)
            multiplicador_outlier = st.slider(
                'Filtro de Outliers (Multiplicador para o Melhor Tempo)',
                min_value=1.0,
                max_value=1.2,
                value=1.05,  # Valor inicial
                step=0.01,
                help="Ajuste o multiplicador para filtrar os outliers. (exemplo: 1.08 significa 8% acima do melhor tempo)"
            )

            # Gerar o box plot com os laptimes e o filtro interativo de outliers
            fig_laptimes_com_cor = gerar_boxplot_laptimes(
                df_completo, modelo_cor, multiplicador_outlier)
            fig_laptimes_sem_cor = gerar_boxplot_laptimes_sem_cor(
                df_completo, multiplicador_outlier)

            # Exibir as opções de gráfico: com ou sem cor por montadora
            escolha_grafico = st.radio(
                "Defina como o gráfico será colorido:",
                ('Montadora', 'Colocação')
            )

            if escolha_grafico == 'Montadora':
                st.plotly_chart(fig_laptimes_com_cor, use_container_width=True)
            else:
                st.plotly_chart(fig_laptimes_sem_cor, use_container_width=True)

            # Carregar os dados dos pilotos usando a função existente
            driver_info = separar_pilotos_por_volta(df)

            # Gerar o gráfico de linha com todos os pilotos
            fig_laptimes_linha = gerar_grafico_laptimes_por_volta(driver_info)

            # Exibir no Streamlit
            st.plotly_chart(fig_laptimes_linha, use_container_width=True)

        with tabs[3]:
            # Usando a função adaptada
            gerar_figura_para_piloto_referencia, pilotos = gerar_grafico_gap_para_piloto_referencia(
                df_completo)

            # Seleção do piloto de referência no Streamlit
            reference_pilot = st.selectbox(
                'Selecione o piloto de referência:',
                pilotos
            )

            # Gerar e exibir o gráfico quando o piloto for selecionado
            if reference_pilot:
                fig = gerar_figura_para_piloto_referencia(reference_pilot)
                if fig:
                    st.plotly_chart(fig)
                else:
                    st.warning(
                        f'O piloto {reference_pilot} não possui dados suficientes para análise.')

            with tabs[4]:
                # Processa o DataFrame para análise GAP x Speed
                cleaned_df = processar_gap_st(df)

                # Interface Streamlit
                pilotos = cleaned_df['Piloto'].unique().tolist()
                pilotos.insert(0, "")  # Adiciona opção vazia
                selected_pilot = st.selectbox('Selecione um piloto:', pilotos)

                show_trend = st.checkbox("Mostrar linha de tendência")

                if selected_pilot:
                    pilot_data = cleaned_df[cleaned_df['Piloto']
                                            == selected_pilot]
                    filtered_data = pilot_data[pilot_data['ST_next'] > 200]

                    fig_gap_speed = gerar_grafico_gap_vs_st(
                        filtered_data, selected_pilot, show_trend=show_trend)
                    st.plotly_chart(fig_gap_speed)

                    fig_gap_lap = gerar_grafico_gap_vs_volta(
                        filtered_data, selected_pilot)
                    st.plotly_chart(fig_gap_lap)
                else:
                    st.warning('Por favor, selecione um piloto.')

            with tabs[5]:
                st.header("🏁 Ranking por Volta")

                # df_completo já deve estar carregado com 'Piloto', 'Lap', 'Lap_seconds'
                ranked_df = gerar_ranking_por_volta(df_completo)

                # Slider para selecionar a volta
                selected_lap = st.slider(
                    "Selecione a volta:",
                    int(ranked_df['Lap'].min()),
                    int(ranked_df['Lap'].max()),
                    step=1
                )

                # Pilotos do time para destacar
                team_pilots = ['21 - Thiago Camilo', '30 - Cesar Ramos']

                # Dados da volta selecionada
                lap_data = ranked_df[ranked_df['Lap'] == selected_lap].copy()
                lap_data['Destaque'] = lap_data['Piloto'].apply(
                    lambda x: 'Time' if x in team_pilots else 'Outro'
                )

                best_time = lap_data['Lap_seconds'].min()
                min_y_value = best_time * 0.98

                # Gráfico de barras
                fig_bar = px.bar(
                    lap_data,
                    x='Piloto',
                    y='Lap_seconds',
                    text='Rank',
                    title=f'Ranking da Volta {selected_lap}',
                    labels={'Piloto': 'Piloto',
                            'Lap_seconds': 'Tempo de Volta (s)'}
                )

                fig_bar.update_traces(
                    texttemplate='%{text}',
                    textposition='outside',
                    marker=dict(
                        color=lap_data['Destaque'].apply(
                            lambda x: 'rgba(255, 0, 0, 0.8)' if x == 'Time' else 'rgba(31, 119, 180, 0.7)'
                        )
                    )
                )

                fig_bar.update_layout(
                    title_x=0.4,
                    xaxis_tickangle=-45,
                    yaxis=dict(range=[min_y_value, None]),
                    showlegend=False
                )

                st.plotly_chart(fig_bar)

                st.write(f"📋 Tabela de Ranking da Volta {selected_lap}")
                st.dataframe(lap_data[['Piloto', 'Lap_seconds', 'Rank']].rename(
                    columns={'Lap_seconds': 'Tempo (s)'}), hide_index=True)

                # Histórico de ranking do piloto selecionado
                selected_pilot = st.selectbox(
                    "Selecione o piloto para ver histórico de ranking:", ranked_df['Piloto'].unique())

                piloto_data = ranked_df[ranked_df['Piloto'] == selected_pilot]

                fig_line = px.line(
                    piloto_data,
                    x='Lap',
                    y='Rank',
                    markers=True,
                    title=f'Histórico de Ranking - {selected_pilot}',
                    labels={'Lap': 'Volta', 'Rank': 'Ranking'}
                )

                fig_line.update_layout(
                    title_x=0.38
                )

                st.plotly_chart(fig_line)
