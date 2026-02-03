import pandas as pd
import streamlit as st
import plotly.express as px
from PIL import Image
import re
from functions.utils import normalizar_coluna_velocidade, validar_csv, separar_pilotos_por_volta, maior_velocidade_por_piloto,  convert_time_to_seconds, processar_resultado_csv, montar_dataframe_completo, gerar_boxplot_setor, processar_gap_st, gerar_grafico_gap_vs_st, gerar_grafico_gap_vs_volta, montar_dataframe_resultado_corrida, colorir_piloto, criar_matriz_velocidades, formatar_st_com_cores_interativo, preparar_dados_boxplot, gerar_boxplot_st, calcular_st_maior_e_media, plotar_maior_st, plotar_media_top_5_st, gerar_relatorio_completo_speed_report, gerar_ranking_st, gerar_boxplot_laptimes_sem_cor, gerar_boxplot_laptimes, gerar_grafico_laptimes_por_volta, gerar_grafico_gap_para_piloto_referencia, gerar_ranking_por_volta, imagem_base64, criar_matriz_velocidades_numeral, filtrar_gap, plotar_raising_average_st, calcular_raising_average_st
from functions.constants import pilotos_cor, equipes_pilotos, equipes_cor, modelo_cor, piloto_modelo, pilotos_cor_amattheis
from functions.database import salvar_sessao, listar_sessoes, buscar_sessao_por_id, excluir_sessao, obter_estatisticas
import plotly.graph_objects as go
import io

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

# Menu principal: Nova Sessão ou Consultar Sessões
# Usar session_state para manter o modo quando uma sessão é carregada
if 'modo_app' not in st.session_state:
    st.session_state['modo_app'] = "📊 Nova Sessão"

modo_app = st.radio(
    "Escolha o modo:",
    ("📊 Nova Sessão", "🗄️ Consultar Sessões Salvas"),
    horizontal=True,
    index=0 if st.session_state['modo_app'] == "📊 Nova Sessão" else 1,
    key="modo_app_radio"
)

# Atualizar session_state quando o usuário muda o modo manualmente
if modo_app != st.session_state.get('modo_app'):
    st.session_state['modo_app'] = modo_app
    # Limpar sessão carregada se mudar de modo manualmente
    if 'sessao_carregada' in st.session_state:
        st.session_state.pop('sessao_carregada', None)
        st.session_state.pop('modo_visualizacao', None)

if modo_app == "🗄️ Consultar Sessões Salvas":
    # ========== MODO CONSULTA ==========
    st.header("🗄️ Consultar Sessões Salvas")
    
    # Se houver sessão carregada, mostrar aviso e botão para visualizar
    if 'sessao_carregada' in st.session_state and st.session_state.get('modo_visualizacao', False):
        sessao = st.session_state['sessao_carregada']
        st.success(f"✅ Sessão carregada: **{sessao.get('evento', 'Sem evento')}** | {sessao.get('data', 'Sem data')} | {sessao.get('circuito', 'Sem circuito')}")
        col_btn1, col_btn2 = st.columns([1, 4])
        with col_btn1:
            if st.button("👁️ Visualizar Dados da Sessão", type="primary"):
                st.session_state['modo_app'] = "📊 Nova Sessão"
                st.rerun()
        with col_btn2:
            if st.button("🔄 Limpar Sessão Carregada"):
                st.session_state.pop('sessao_carregada', None)
                st.session_state.pop('modo_visualizacao', None)
                st.rerun()
        st.markdown("---")
    
    # Estatísticas
    stats = obter_estatisticas()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total de Sessões", stats['total_sessoes'])
    with col2:
        st.metric("Eventos Únicos", stats['eventos_unicos'])
    with col3:
        st.metric("Circuitos Únicos", stats['circuitos_unicos'])
    with col4:
        treino_count = stats['sessoes_por_tipo'].get('Treino', 0)
        corrida_count = stats['sessoes_por_tipo'].get('Corrida', 0)
        st.metric("Treino/Corrida", f"{treino_count}/{corrida_count}")
    
    st.markdown("---")
    
    # Filtros
    st.subheader("🔍 Filtros de Busca")
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    
    with col_f1:
        filtro_evento = st.text_input("Evento", placeholder="Ex: Stock Car 2024")
    with col_f2:
        filtro_ano = st.text_input("Ano", placeholder="Ex: 2024")
    with col_f3:
        filtro_circuito = st.text_input("Circuito", placeholder="Ex: Interlagos")
    with col_f4:
        filtro_tipo = st.selectbox("Tipo", ["Todos", "Treino", "Corrida"])
    
    # Buscar sessões
    tipo_filtro = None if filtro_tipo == "Todos" else filtro_tipo
    sessoes_df = listar_sessoes(
        filtro_evento=filtro_evento if filtro_evento else None,
        filtro_ano=filtro_ano if filtro_ano else None,
        filtro_circuito=filtro_circuito if filtro_circuito else None,
        filtro_tipo=tipo_filtro
    )
    
    if sessoes_df.empty:
        st.info("📭 Nenhuma sessão encontrada com os filtros aplicados.")
    else:
        st.subheader(f"📋 Sessões Encontradas ({len(sessoes_df)})")
        
        # Exibir tabela de sessões
        sessoes_display = sessoes_df[['id', 'evento', 'data', 'circuito', 'tipo_sessao', 'tipo_opcao', 'data_criacao']].copy()
        sessoes_display.columns = ['ID', 'Evento', 'Data', 'Circuito', 'Sessão', 'Tipo', 'Data Criação']
        sessoes_display['Data Criação'] = pd.to_datetime(sessoes_display['Data Criação']).dt.strftime('%d/%m/%Y %H:%M')
        
        st.dataframe(sessoes_display, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.subheader("👁️ Visualizar Sessão")
        
        # Seleção de sessão
        sessoes_ids = sessoes_df['id'].tolist()
        sessoes_labels = [
            f"ID {row['id']} - {row['evento'] or 'Sem evento'} | {row['data'] or 'Sem data'} | {row['circuito'] or 'Sem circuito'}"
            for _, row in sessoes_df.iterrows()
        ]
        
        sessao_selecionada_idx = st.selectbox(
            "Selecione uma sessão para visualizar:",
            range(len(sessoes_ids)),
            format_func=lambda x: sessoes_labels[x]
        )
        
        if st.button("🔍 Carregar e Visualizar Sessão", type="primary"):
            sessao_id = sessoes_ids[sessao_selecionada_idx]
            sessao = buscar_sessao_por_id(sessao_id)
            
            if sessao:
                st.session_state['sessao_carregada'] = sessao
                st.session_state['modo_visualizacao'] = True
                # Mudar automaticamente para o modo "Nova Sessão" para visualizar os dados
                st.session_state['modo_app'] = "📊 Nova Sessão"
                st.success(f"✅ Sessão ID {sessao_id} carregada! Redirecionando para visualização...")
                st.rerun()
        
        st.markdown("---")
        st.subheader("🗑️ Excluir Sessão")
        
        sessao_excluir_idx = st.selectbox(
            "Selecione uma sessão para excluir:",
            range(len(sessoes_ids)),
            format_func=lambda x: sessoes_labels[x],
            key="excluir_select"
        )
        
        if st.button("🗑️ Excluir Sessão", type="primary"):
            sessao_id = sessoes_ids[sessao_excluir_idx]
            sessao_info = sessoes_df[sessoes_df['id'] == sessao_id].iloc[0]
            
            if excluir_sessao(sessao_id):
                st.success(f"✅ Sessão ID {sessao_id} excluída com sucesso!")
                st.rerun()
            else:
                st.error("❌ Erro ao excluir sessão.")

else:
    # ========== MODO NOVA SESSÃO ==========
    opcao = st.radio("Selecione uma opção:", ("Corrida", "Treino"))

    uploaded_file = st.file_uploader("Escolha um arquivo CSV", type="csv")

# Verificar se há sessão carregada ou arquivo novo
tem_dados = False

# Se estiver no modo consulta E não houver sessão carregada, não processar dados
if modo_app == "🗄️ Consultar Sessões Salvas" and not ('sessao_carregada' in st.session_state and st.session_state.get('modo_visualizacao', False)):
    # Modo consulta - não processar dados aqui, apenas exibir interface de consulta
    pass
elif 'sessao_carregada' in st.session_state and st.session_state.get('modo_visualizacao', False):
    # Sessão carregada do banco de dados
    tem_dados = True
    sessao = st.session_state['sessao_carregada']
    dados_processados = sessao.get('dados_processados', {})
    
    # Recriar objetos necessários
    if 'df_original' in dados_processados:
        df = dados_processados['df_original']
        if not isinstance(df, pd.DataFrame):
            st.error("❌ Erro ao carregar dados da sessão. Formato inválido.")
            st.stop()
    else:
        st.error("❌ Dados originais não encontrados na sessão.")
        st.stop()
    
    if 'driver_info' in dados_processados:
        driver_info = dados_processados['driver_info']
        if isinstance(driver_info, dict):
            # Reconstruir driver_info
            driver_info_reconstruido = {}
            for key, value in driver_info.items():
                if isinstance(value, pd.DataFrame):
                    driver_info_reconstruido[key] = value
                elif isinstance(value, list):
                    driver_info_reconstruido[key] = pd.DataFrame(value)
                else:
                    driver_info_reconstruido[key] = value
            driver_info = driver_info_reconstruido
        else:
            driver_info = separar_pilotos_por_volta(df)
    else:
        driver_info = separar_pilotos_por_volta(df)
    
    top_speed = maior_velocidade_por_piloto(driver_info)
    opcao = sessao.get('tipo_opcao', opcao)
    
    # Mostrar informações da sessão
    st.info(f"📂 Sessão carregada: **{sessao.get('evento', 'Sem evento')}** | {sessao.get('data', 'Sem data')} | {sessao.get('circuito', 'Sem circuito')}")
    
    col_voltar1, col_voltar2 = st.columns([1, 4])
    with col_voltar1:
        if st.button("🔄 Voltar para Nova Sessão"):
            st.session_state.pop('sessao_carregada', None)
            st.session_state.pop('modo_visualizacao', None)
            st.rerun()
elif modo_app == "📊 Nova Sessão" and uploaded_file is not None:
    # Arquivo novo carregado
    tem_dados = True
    try:
        # Leitura do arquivo CSV
        df = pd.read_csv(uploaded_file)

    except Exception as e:
        st.error(f"❌ Erro ao ler o arquivo CSV: {e}")
        st.info("Verifique se o arquivo é um CSV válido e tente novamente.")
        st.stop()

    # Validação robusta do CSV
    is_valid, error_message = validar_csv(df)
    if not is_valid:
        st.error(f"❌ Erro na validação do CSV: {error_message}")
        st.info("O arquivo CSV deve conter as seguintes colunas: 'Time of Day', 'Lap', 'Lap Tm', 'S1 Tm', 'S2 Tm', 'S3 Tm', e 'ST' ou 'SPT'.")
        st.stop()

    try:
        df = normalizar_coluna_velocidade(df)
    except ValueError as e:
        st.error(f"❌ Erro ao normalizar coluna de velocidade: {e}")
        st.stop()

    # Verificar se todas as colunas necessárias existem após normalização
    colunas_necessarias = ['Time of Day', 'Lap', 'Lap Tm', 'S1 Tm', 'S2 Tm', 'S3 Tm', 'ST']
    colunas_faltando = [col for col in colunas_necessarias if col not in df.columns]
    if colunas_faltando:
        st.error(f"❌ Colunas não encontradas após processamento: {', '.join(colunas_faltando)}")
        st.stop()

    try:
        df = df[colunas_necessarias]
        # Trocando virgula por ponto e transformando os tempos de volta em float
        df['ST'] = df['ST'].astype(str).str.replace(',', '.').astype(float)
    except (ValueError, KeyError) as e:
        st.error(f"❌ Erro ao processar dados: {e}")
        st.info("Verifique se os dados nas colunas estão no formato correto.")
        st.stop()

    try:
        driver_info = separar_pilotos_por_volta(df)
        if not driver_info:
            st.warning("⚠️ Nenhum piloto foi encontrado nos dados. Verifique o formato do arquivo CSV.")
            st.stop()
        top_speed = maior_velocidade_por_piloto(driver_info)
    except Exception as e:
        st.error(f"❌ Erro ao processar dados dos pilotos: {e}")
        st.stop()
    
    # Seção para salvar sessão (apenas se não estiver em modo visualização)
    if 'sessao_carregada' not in st.session_state or not st.session_state.get('modo_visualizacao', False):
        st.markdown("---")
        st.subheader("💾 Salvar Sessão")
        
        col_save1, col_save2 = st.columns(2)
        with col_save1:
            evento_save = st.text_input("Evento", key="save_evento", placeholder="Ex: S26E01")
            data_save = st.text_input("Data", key="save_data", placeholder="Ex: 15/03/2024")
        with col_save2:
            circuito_save = st.text_input("Circuito", key="save_circuito", placeholder="Ex: Interlagos")
            tipo_sessao_save = st.text_input("Sessão", key="save_tipo_sessao", placeholder="Ex: Treino Livre 1")
        
        observacoes_save = st.text_area("Observações (opcional)", key="save_observacoes", placeholder="Informações adicionais...")
        
        if st.button("💾 Salvar Sessão no Banco de Dados"):
            if not evento_save or not data_save or not circuito_save or not tipo_sessao_save:
                st.warning("⚠️ Preencha pelo menos Evento, Data, Circuito e Sessão para salvar.")
            else:
                try:
                    # Preparar dados para salvar
                    dados_para_salvar = {
                        'df_original': df,  # DataFrame original processado
                        'driver_info': driver_info,  # Dicionário de DataFrames por piloto
                    }
                    
                    # Adicionar dados específicos conforme o tipo
                    if opcao == "Treino":
                        dados_para_salvar['df_resultado'] = processar_resultado_csv(df)
                    else:  # Corrida
                        df_resultado_corrida = montar_dataframe_resultado_corrida(driver_info, equipes_pilotos)
                        dados_para_salvar['df_resultado_corrida'] = df_resultado_corrida
                    
                    # Salvar no banco
                    sessao_id = salvar_sessao(
                        evento=evento_save,
                        data=data_save,
                        circuito=circuito_save,
                        tipo_sessao=tipo_sessao_save,
                        observacoes=observacoes_save,
                        tipo_opcao=opcao,
                        nome_arquivo_csv=uploaded_file.name if uploaded_file else "desconhecido.csv",
                        dados_processados=dados_para_salvar
                    )
                    st.success(f"✅ Sessão salva com sucesso! ID: {sessao_id}")
                except Exception as e:
                    st.error(f"❌ Erro ao salvar sessão: {e}")
                    import traceback
                    st.code(traceback.format_exc())

if tem_dados:
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
                    "Filtrar ST para GAP > x", value=False)

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

            # Seletor de esquema de cores (Padrão Amattheis pré-selecionado)
            esquema_cores = st.radio(
                "Esquema de cores:",
                ('Equipe', 'Padrão Amattheis'),
                index=1,  # Padrão Amattheis pré-selecionado
                horizontal=True
            )

            # Cores conforme o esquema selecionado
            cores = []
            legendas = []
            
            if esquema_cores == 'Equipe':
                # Cores por equipe (comportamento original)
                for piloto in pilotos:
                    equipe = equipes_pilotos.get(piloto)
                    cor = equipes_cor.get(equipe, 'gray')
                    cores.append(cor)
                    legendas.append(equipe)
            else:
                # Padrão Amattheis: todos em silver, exceto os pilotos Amattheis destacados
                # Lista dos pilotos Amattheis que devem ser destacados
                pilotos_amattheis = ['6 - Helio Castroneves', '12 - Lucas Foresti', 
                                    '21 - Thiago Camilo', '30 - Cesar Ramos', 
                                    '83 - Gabriel Casagrande']
                
                for piloto in pilotos:
                    # Tenta encontrar a cor no dicionário pilotos_cor_amattheis
                    # Usa get() com fallback para 'silver' se não encontrar
                    cor = pilotos_cor_amattheis.get(piloto, 'silver')
                    cores.append(cor)
                    # Para o padrão Amattheis, usa o nome do piloto se for Amattheis, senão "Outros"
                    if piloto in pilotos_amattheis and cor != 'silver':
                        legendas.append(piloto)  # Nome do piloto individual
                    else:
                        legendas.append('Outros')

            # Gráfico
            fig = go.Figure()
            barras_adicionadas = set()
            
            if esquema_cores == 'Equipe':
                # Comportamento original: agrupar por equipe na legenda
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
                legend_title = 'Equipe'
            else:
                # Padrão Amattheis: cada piloto Amattheis individualmente, outros agrupados
                for piloto, velocidade, legenda, cor in zip(pilotos, velocidades_max, legendas, cores):
                    show_legend = legenda not in barras_adicionadas
                    barras_adicionadas.add(legenda)
                    fig.add_trace(go.Bar(
                        x=[piloto],
                        y=[velocidade],
                        name=legenda if show_legend else None,
                        marker_color=cor,
                        width=[0.6],
                        showlegend=show_legend
                    ))
                legend_title = 'Pilotos'

            fig.update_layout(
                title="<b>Top speed</b><br><span style='font-size:12px; color:gray;'>Clique e arraste o eixo Y para alterar a escala</span>",
                title_x=0.4,
                xaxis_title='Piloto',
                yaxis_title='Velocidade Máxima (km/h)',
                yaxis=dict(range=[y_min, y_max]),
                height=600,
                barmode='group',
                legend_title_text=legend_title
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

    elif opcao == "Corrida":

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

            # Checkbox e input para filtro GAP
            is_filtrar_gap = st.checkbox(
                "Filtrar ST para GAP > x", value=False)
            limite_gap = 0.0
            if is_filtrar_gap:
                limite_gap = st.number_input(
                    "Digite o limite de GAP (em segundos):", min_value=0.0, value=1.0, step=0.1)

            # Processar GAP
            df_gap = processar_gap_st(df)

            # Filtrar dados se checkbox ativado
            if is_filtrar_gap:
                df_gap = filtrar_gap(df_gap, limite_gap)
                st.caption(
                    f"{len(df_gap)} voltas consideradas após remover STs com GAP ≤ {limite_gap:.1f}s")

            # Separar pilotos com base no dataframe bruto
            driver_info = separar_pilotos_por_volta(df)

            # Criar versão filtrada dos dados por piloto, se filtro ativo
            if is_filtrar_gap:
                driver_info_filtrado = {
                    piloto: voltas[voltas['Lap'].isin(
                        df_gap[df_gap['Piloto'] == piloto]['Lap'])]
                    for piloto, voltas in driver_info.items()
                    if piloto in df_gap['Piloto'].unique()
                }
            else:
                driver_info_filtrado = driver_info

            # Checkbox para mostrar só numerais
            col1, col2, col3 = st.columns([6, 1, 1])
            with col3:
                mostrar_numerais = st.checkbox("Somente numerais", value=False)

            # Criar matriz ST filtrada conforme checkbox
            if mostrar_numerais:
                df_matriz_st = criar_matriz_velocidades_numeral(
                    driver_info_filtrado)
            else:
                df_matriz_st = criar_matriz_velocidades(driver_info_filtrado)

            # Formatar e exibir matriz
            df_st_formatado = formatar_st_com_cores_interativo(df_matriz_st)
            st.dataframe(df_st_formatado,
                         use_container_width=False, hide_index=True)

            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                df_matriz_st.to_excel(writer, index=True,
                                      sheet_name='Matriz ST')

            excel_buffer.seek(0)  # Volta ao início do arquivo em memória
            excel_data = excel_buffer.read()

            st.download_button(
                label="📥 Baixar Matriz ST em Excel",
                data=excel_data,
                file_name='matriz_st.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

            # Dados para boxplot e gráficos, usando dados filtrados
            df_boxplot = preparar_dados_boxplot(
                driver_info_filtrado, piloto_modelo)
            fig_box = gerar_boxplot_st(df_boxplot)
            st.plotly_chart(fig_box, use_container_width=True)

            df_st = calcular_st_maior_e_media(driver_info_filtrado)
            
            # Seletor de esquema de cores (Padrão Amattheis pré-selecionado)
            esquema_cores_st = st.radio(
                "Esquema de cores:",
                ('Padrão Amattheis', 'Montadora'),
                index=0,  # Padrão Amattheis pré-selecionado
                horizontal=True
            )
            
            fig_maior_st = plotar_maior_st(df_st, modelo_cor, esquema_cores_st)
            fig_media_top_5_st = plotar_media_top_5_st(df_st, modelo_cor, esquema_cores_st)

            st.plotly_chart(fig_maior_st)
            st.plotly_chart(fig_media_top_5_st)

            # Raising Average ST
            # Opção de coloração
            modo_coloracao = st.radio(
                "Colorir linhas por:",
                ["Padrão Amattheis", "Montadora", "Piloto"],
                index=0,  # Padrão Amattheis pré-selecionado
                horizontal=True
            )

            # Cálculo e plotagem do gráfico
            dict_raising = calcular_raising_average_st(driver_info_filtrado)
            fig_raising = plotar_raising_average_st(
                dict_raising,
                piloto_modelo,
                modelo_cor,
                colorir_por=modo_coloracao.lower(),
                pilotos_cor=pilotos_cor  # Para modo "piloto"
            )

            st.plotly_chart(fig_raising, use_container_width=True)

            st.markdown("---")
            st.subheader("📄 Gerar Relatório em PDF")
            
            # Informações da sessão para a capa
            st.markdown("### 📋 Informações da Sessão")
            st.markdown("Preencha as informações abaixo para incluir na capa do relatório:")
            
            col_info1, col_info2 = st.columns(2)
            
            with col_info1:
                evento = st.text_input("Evento", placeholder="Ex: S26E01")
                data = st.text_input("Data", placeholder="Ex: 15/03/2024")
            
            with col_info2:
                circuito = st.text_input("Circuito", placeholder="Ex: Interlagos")
                tipo_sessao = st.text_input("Sessão", placeholder="Ex: Treino Livre 1")
            
            observacoes = st.text_area("Observações (opcional)", placeholder="Informações adicionais sobre a sessão...", height=100)
            
            # Criar dicionário com informações da sessão
            info_sessao = {
                'evento': evento,
                'data': data,
                'circuito': circuito,
                'tipo_sessao': tipo_sessao,
                'observacoes': observacoes
            }
            
            st.markdown("---")
            
            # Seleção de gráficos a incluir
            st.markdown("**Selecione quais elementos incluir no relatório:**")
            col1, col2 = st.columns(2)
            
            with col1:
                incluir_resumo = st.checkbox("Resumo de ST por Piloto", value=True)
                incluir_boxplot = st.checkbox("Boxplot por Montadora", value=True)
            
            with col2:
                incluir_maior_st = st.checkbox("Gráfico Maior ST", value=True)
                incluir_media_top5_st = st.checkbox("Gráfico Média Top 5 ST", value=True)
            
            # Verificar se pelo menos um elemento foi selecionado
            if not any([incluir_resumo, incluir_boxplot, incluir_maior_st, incluir_media_top5_st]):
                st.warning("⚠️ Selecione pelo menos um elemento para incluir no relatório.")
            
            if st.button("📄 Gerar relatório em PDF"):
                try:
                    caminho_pdf = gerar_relatorio_completo_speed_report(
                        df_st=df_st,
                        df_matriz_st=df_matriz_st,
                        fig_box=fig_box,
                        fig_maior_st=fig_maior_st,
                        fig_media_top_5_st=fig_media_top_5_st,
                        incluir_resumo=incluir_resumo,
                        incluir_boxplot=incluir_boxplot,
                        incluir_maior_st=incluir_maior_st,
                        incluir_media_top5_st=incluir_media_top5_st,
                        info_sessao=info_sessao
                    )
                    st.success(f"✅ Relatório gerado com sucesso: {caminho_pdf}")
                    with open(caminho_pdf, "rb") as f:
                        st.download_button("📥 Baixar PDF", f,
                                           file_name="relatorio_speed_report.pdf")
                except Exception as e:
                    st.error(f"❌ Erro ao gerar relatório: {e}")

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
