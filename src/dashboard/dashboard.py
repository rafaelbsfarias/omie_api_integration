import datetime

import numpy as np
import pandas as pd
import streamlit as st

from src.config import Settings
from src.db.database import Database

# Carregar as configurações do ambiente
settings = Settings()


# Funções de carregamento dos dados (cache para evitar recarregamento desnecessário)
@st.cache_data(show_spinner=True)
def load_fluxo_caixa_data():
    db = Database()
    # Query para contas a pagar (despesas) – convertemos o valor para numérico
    query_despesas = """
        SELECT data_vencimento, CAST(valor_documento AS numeric) AS valor_documento
        FROM contapagar;
    """
    despesas = pd.read_sql(query_despesas, db.engine)

    # Query para contas a receber (receitas)
    query_receitas = """
        SELECT data_vencimento, CAST(valor_documento AS numeric) AS valor_documento
        FROM contareceber;
    """
    receitas = pd.read_sql(query_receitas, db.engine)
    return despesas, receitas


@st.cache_data(show_spinner=True)
def load_despesas_por_categoria():
    db = Database()
    # Consulta unindo contapagar e categorias para agrupar as despesas por categoria
    query = """
        SELECT c.descricao AS categoria,
               SUM(CAST(cp.valor_documento AS numeric)) AS total
        FROM contapagar cp
        JOIN categorias c ON cp.codigo_categoria = c.codigo
        GROUP BY c.descricao
        ORDER BY total DESC;
    """
    df = pd.read_sql(query, db.engine)
    return df


@st.cache_data(show_spinner=True)
def load_despesas_por_fornecedor():
    db = Database()
    # Consulta unindo contapagar e clientes para agrupar as despesas por fornecedor
    query = """
        SELECT cli.razao_social AS fornecedor,
               SUM(CAST(cp.valor_documento AS numeric)) AS total
        FROM contapagar cp
        JOIN clientes cli ON cp.codigo_cliente_fornecedor = cli.codigo_cliente_integracao
        GROUP BY cli.razao_social
        ORDER BY total DESC;
    """
    df = pd.read_sql(query, db.engine)
    return df


@st.cache_data(show_spinner=True)
def load_pagamentos_vencidos():
    db = Database()
    # Consulta para buscar pagamentos vencidos (data_vencimento menor que a data atual)
    query = """
        SELECT *
        FROM contapagar
        WHERE to_date(data_vencimento, 'DD/MM/YYYY') < CURRENT_DATE;
    """
    df = pd.read_sql(query, db.engine)
    return df


@st.cache_data(show_spinner=True)
def load_tendencias_despesas():
    db = Database()
    # Agregação mensal das despesas
    query = """
        SELECT DATE_TRUNC('month', to_date(data_vencimento, 'DD/MM/YYYY')) AS mes,
        SUM(CAST(valor_documento AS numeric)) AS total
        FROM contapagar
        GROUP BY DATE_TRUNC('month', to_date(data_vencimento, 'DD/MM/YYYY'))
        ORDER BY mes;
    """
    df = pd.read_sql(query, db.engine)
    return df


# Funções para renderizar cada dashboard
def dashboard_fluxo_caixa():
    st.header("Visão Geral do Fluxo de Caixa")
    despesas, receitas = load_fluxo_caixa_data()
    total_despesas = despesas["valor_documento"].sum()
    total_receitas = receitas["valor_documento"].sum()
    saldo = total_receitas - total_despesas

    st.metric("Total Despesas", f"R$ {total_despesas:,.2f}")
    st.metric("Total Receitas", f"R$ {total_receitas:,.2f}")
    st.metric("Saldo (Receitas - Despesas)", f"R$ {saldo:,.2f}")

    # Agrupar despesas por mês e exibir gráfico de linha
    despesas["data_vencimento"] = pd.to_datetime(
        despesas["data_vencimento"], format="%d/%m/%Y", dayfirst=True
    )
    despesas_monthly = (
        despesas.groupby(pd.Grouper(key="data_vencimento", freq="M"))
        .sum()
        .reset_index()
    )
    st.line_chart(
        despesas_monthly.rename(columns={"data_vencimento": "index"}).set_index("index")
    )


def dashboard_despesas_categoria():
    st.header("Despesas por Categoria")
    df = load_despesas_por_categoria()
    st.dataframe(df)
    if not df.empty:
        st.bar_chart(df.set_index("categoria"))


def dashboard_despesas_fornecedor():
    st.header("Despesas por Fornecedor")
    df = load_despesas_por_fornecedor()
    st.dataframe(df)
    if not df.empty:
        st.bar_chart(df.set_index("fornecedor"))


def dashboard_pagamentos_vencidos():
    st.header("Pagamentos Vencidos")
    df = load_pagamentos_vencidos()
    st.dataframe(df)


def dashboard_tendencias():
    st.header("Tendências Mensais de Despesas")
    df = load_tendencias_despesas()
    st.dataframe(df)
    df["mes"] = pd.to_datetime(df["mes"])
    st.line_chart(df.set_index("mes"))


# Menu de navegação usando a sidebar
def main():
    st.sidebar.title("Menu de Dashboards")
    dashboards = {
        "Fluxo de Caixa": dashboard_fluxo_caixa,
        "Despesas por Categoria": dashboard_despesas_categoria,
        "Despesas por Fornecedor": dashboard_despesas_fornecedor,
        "Pagamentos Vencidos": dashboard_pagamentos_vencidos,
        "Tendências de Despesas": dashboard_tendencias,
    }
    escolha = st.sidebar.radio("Selecione um Dashboard", list(dashboards.keys()))
    dashboards[escolha]()


if __name__ == "__main__":
    main()
