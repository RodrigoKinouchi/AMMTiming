"""
Módulo de banco de dados para armazenar e consultar sessões de treino/corrida.
Usa SQLite para armazenar metadados e dados processados das sessões.
"""
import sqlite3
import pandas as pd
import json
import pickle
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
import streamlit as st


DB_PATH = "amm_timing.db"


def get_connection():
    """Cria e retorna uma conexão com o banco de dados."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Inicializa o banco de dados criando as tabelas necessárias."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Tabela de sessões (metadados)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evento TEXT,
            data TEXT,
            circuito TEXT,
            tipo_sessao TEXT,
            observacoes TEXT,
            tipo_opcao TEXT NOT NULL,  -- 'Treino' ou 'Corrida'
            nome_arquivo_csv TEXT,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabela de dados processados (armazena dados principais como JSON)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dados_processados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sessao_id INTEGER NOT NULL,
            tipo_dado TEXT NOT NULL,  -- 'driver_info', 'df_st', 'df_matriz_st', 'df_resultado', etc.
            dados_json TEXT NOT NULL,  -- JSON serializado dos dados
            FOREIGN KEY (sessao_id) REFERENCES sessoes(id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    conn.close()


def salvar_sessao(
    evento: str,
    data: str,
    circuito: str,
    tipo_sessao: str,
    observacoes: str,
    tipo_opcao: str,
    nome_arquivo_csv: str,
    dados_processados: Dict[str, Any]
) -> int:
    """
    Salva uma nova sessão no banco de dados.
    
    Args:
        evento: Nome do evento
        data: Data da sessão
        circuito: Nome do circuito
        tipo_sessao: Tipo de sessão (ex: "Treino Livre 1")
        observacoes: Observações adicionais
        tipo_opcao: 'Treino' ou 'Corrida'
        nome_arquivo_csv: Nome do arquivo CSV original
        dados_processados: Dicionário com os dados processados a serem salvos
    
    Returns:
        int: ID da sessão criada
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Inserir sessão
    cursor.execute("""
        INSERT INTO sessoes (evento, data, circuito, tipo_sessao, observacoes, tipo_opcao, nome_arquivo_csv)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (evento, data, circuito, tipo_sessao, observacoes, tipo_opcao, nome_arquivo_csv))
    
    sessao_id = cursor.lastrowid
    
    # Salvar dados processados
    for tipo_dado, dados in dados_processados.items():
        if dados is None:
            continue
            
        # Serializar dados para JSON
        if isinstance(dados, pd.DataFrame):
            dados_json = dados.to_json(orient='records', date_format='iso')
        elif isinstance(dados, dict):
            # Para dicionários (como driver_info), converter cada DataFrame interno
            dados_serializados = {}
            for key, value in dados.items():
                if isinstance(value, pd.DataFrame):
                    # Salvar cada DataFrame do dicionário
                    dados_serializados[key] = value.to_dict(orient='records')
                elif isinstance(value, (str, int, float, bool, type(None))):
                    dados_serializados[key] = value
                else:
                    # Para outros tipos, tentar converter para string
                    dados_serializados[key] = str(value)
            dados_json = json.dumps(dados_serializados, default=str)
        else:
            dados_json = json.dumps(dados, default=str)
        
        cursor.execute("""
            INSERT INTO dados_processados (sessao_id, tipo_dado, dados_json)
            VALUES (?, ?, ?)
        """, (sessao_id, tipo_dado, dados_json))
    
    conn.commit()
    conn.close()
    
    return sessao_id


def listar_sessoes(filtro_evento: Optional[str] = None, 
                   filtro_ano: Optional[str] = None,
                   filtro_circuito: Optional[str] = None,
                   filtro_tipo: Optional[str] = None) -> pd.DataFrame:
    """
    Lista todas as sessões salvas, com opções de filtro.
    
    Args:
        filtro_evento: Filtrar por evento
        filtro_ano: Filtrar por ano (extraído da data)
        filtro_circuito: Filtrar por circuito
        filtro_tipo: Filtrar por tipo ('Treino' ou 'Corrida')
    
    Returns:
        DataFrame com as sessões encontradas
    """
    conn = get_connection()
    
    query = "SELECT * FROM sessoes WHERE 1=1"
    params = []
    
    if filtro_evento:
        query += " AND evento LIKE ?"
        params.append(f"%{filtro_evento}%")
    
    if filtro_ano:
        query += " AND data LIKE ?"
        params.append(f"%{filtro_ano}%")
    
    if filtro_circuito:
        query += " AND circuito LIKE ?"
        params.append(f"%{filtro_circuito}%")
    
    if filtro_tipo:
        query += " AND tipo_opcao = ?"
        params.append(filtro_tipo)
    
    query += " ORDER BY data_criacao DESC"
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    return df


def buscar_sessao_por_id(sessao_id: int) -> Optional[Dict[str, Any]]:
    """
    Busca uma sessão específica por ID e retorna seus dados.
    
    Args:
        sessao_id: ID da sessão
    
    Returns:
        Dicionário com metadados da sessão e dados processados, ou None se não encontrada
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Buscar metadados da sessão
    cursor.execute("SELECT * FROM sessoes WHERE id = ?", (sessao_id,))
    sessao_row = cursor.fetchone()
    
    if not sessao_row:
        conn.close()
        return None
    
    # Converter row para dicionário
    sessao = dict(sessao_row)
    
    # Buscar dados processados
    cursor.execute("SELECT tipo_dado, dados_json FROM dados_processados WHERE sessao_id = ?", (sessao_id,))
    dados_rows = cursor.fetchall()
    
    dados_processados = {}
    for row in dados_rows:
        tipo_dado = row[0]
        dados_json = row[1]
        
        # Deserializar JSON
        try:
            dados = json.loads(dados_json)
            
            # Se for uma lista de registros, converter para DataFrame
            if isinstance(dados, list):
                dados_processados[tipo_dado] = pd.DataFrame(dados)
            elif isinstance(dados, dict):
                # Verificar se é um dicionário de DataFrames (como driver_info)
                # Se os valores são listas de dicionários, converter para DataFrames
                dados_reconstruidos = {}
                for key, value in dados.items():
                    if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                        # É uma lista de registros, converter para DataFrame
                        dados_reconstruidos[key] = pd.DataFrame(value)
                    else:
                        dados_reconstruidos[key] = value
                dados_processados[tipo_dado] = dados_reconstruidos
            else:
                dados_processados[tipo_dado] = dados
        except Exception as e:
            if 'st' in globals():
                st.warning(f"Erro ao deserializar dados do tipo '{tipo_dado}': {e}")
            dados_processados[tipo_dado] = None
    
    sessao['dados_processados'] = dados_processados
    conn.close()
    
    return sessao


def excluir_sessao(sessao_id: int) -> bool:
    """
    Exclui uma sessão e todos os seus dados processados.
    
    Args:
        sessao_id: ID da sessão a ser excluída
    
    Returns:
        True se excluída com sucesso, False caso contrário
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Excluir dados processados (CASCADE deve fazer isso automaticamente, mas vamos garantir)
        cursor.execute("DELETE FROM dados_processados WHERE sessao_id = ?", (sessao_id,))
        
        # Excluir sessão
        cursor.execute("DELETE FROM sessoes WHERE id = ?", (sessao_id,))
        
        conn.commit()
        conn.close()
        return cursor.rowcount > 0
    except Exception as e:
        conn.rollback()
        conn.close()
        st.error(f"Erro ao excluir sessão: {e}")
        return False


def obter_estatisticas() -> Dict[str, Any]:
    """
    Retorna estatísticas sobre as sessões armazenadas.
    
    Returns:
        Dicionário com estatísticas
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Total de sessões
    cursor.execute("SELECT COUNT(*) FROM sessoes")
    total_sessoes = cursor.fetchone()[0]
    
    # Sessões por tipo
    cursor.execute("SELECT tipo_opcao, COUNT(*) FROM sessoes GROUP BY tipo_opcao")
    sessoes_por_tipo = dict(cursor.fetchall())
    
    # Eventos únicos
    cursor.execute("SELECT COUNT(DISTINCT evento) FROM sessoes WHERE evento IS NOT NULL AND evento != ''")
    eventos_unicos = cursor.fetchone()[0]
    
    # Circuitos únicos
    cursor.execute("SELECT COUNT(DISTINCT circuito) FROM sessoes WHERE circuito IS NOT NULL AND circuito != ''")
    circuitos_unicos = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'total_sessoes': total_sessoes,
        'sessoes_por_tipo': sessoes_por_tipo,
        'eventos_unicos': eventos_unicos,
        'circuitos_unicos': circuitos_unicos
    }


# Inicializar banco de dados ao importar o módulo
init_database()
