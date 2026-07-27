"""
sprint 3

Dashboard interativo (Streamlit) com KPIs principais, series temporais de
faturamento e filtros dinamicos, sobre o banco relacional gerado nas
Sprints 1 e 2 (database/ecommerce.db).

Executar com: streamlit run dashboard/app.py
"""

import sqlite3
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR / "scripts"))
from eda import DB_PATH, load_vendas  # reuso do carregamento da Sprint 2

CORTE_SEMESTRE = "2025-07-01"

st.set_page_config(page_title="InsightFlow - Dashboard de Vendas", layout="wide")


@st.cache_data
def carregar_dados() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    try:
        df = load_vendas(conn)
    finally:
        conn.close()
    return df


@st.cache_data
def calcular_ciclo_vida(df: pd.DataFrame, corte: str) -> pd.DataFrame:
    """Recencia (dias) e flags de compra em cada semestre, por cliente,
    calculadas sobre o historico completo (independente dos filtros)."""
    max_data = df["Data_Venda"].max()
    corte_ts = pd.Timestamp(corte)

    por_cliente = df.groupby("ID_Cliente").agg(ultima_compra=("Data_Venda", "max"))
    por_cliente["recencia_dias"] = (max_data - por_cliente["ultima_compra"]).dt.days

    clientes_h1 = set(df.loc[df["Data_Venda"] < corte_ts, "ID_Cliente"])
    clientes_h2 = set(df.loc[df["Data_Venda"] >= corte_ts, "ID_Cliente"])
    por_cliente["comprou_h1"] = por_cliente.index.isin(clientes_h1)
    por_cliente["comprou_h2"] = por_cliente.index.isin(clientes_h2)

    return por_cliente.reset_index()


def formatar_moeda(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_inteiro(valor: int) -> str:
    return f"{valor:,}".replace(",", ".")


df = carregar_dados()
ciclo_vida = calcular_ciclo_vida(df, CORTE_SEMESTRE)

# --- Sidebar: filtros dinamicos ---
st.sidebar.header("Filtros")

data_min, data_max = df["Data_Venda"].min().date(), df["Data_Venda"].max().date()
periodo = st.sidebar.date_input(
    "Periodo",
    value=(data_min, data_max),
    min_value=data_min,
    max_value=data_max,
)
categorias = st.sidebar.multiselect("Categoria", sorted(df["Categoria_Produto"].unique()))
estados = st.sidebar.multiselect("Estado", sorted(df["Estado"].unique()))
status_selecionados = st.sidebar.multiselect("Status do pedido", sorted(df["Status_Pedido"].unique()))
metodos = st.sidebar.multiselect("Metodo de pagamento", sorted(df["Metodo_Pagamento"].unique()))
limite_churn = st.sidebar.slider("Inatividade p/ considerar churn (dias)", 30, 180, 90, step=15)

if isinstance(periodo, tuple) and len(periodo) == 2:
    inicio, fim = periodo
else:
    inicio, fim = data_min, data_max

mask = (df["Data_Venda"].dt.date >= inicio) & (df["Data_Venda"].dt.date <= fim)
if categorias:
    mask &= df["Categoria_Produto"].isin(categorias)
if estados:
    mask &= df["Estado"].isin(estados)
if status_selecionados:
    mask &= df["Status_Pedido"].isin(status_selecionados)
if metodos:
    mask &= df["Metodo_Pagamento"].isin(metodos)

df_filtrado = df[mask]

# --- Cabecalho ---
st.title("InsightFlow - Dashboard de Vendas")
st.caption(f"{formatar_inteiro(len(df_filtrado))} vendas no periodo e filtros selecionados")

if df_filtrado.empty:
    st.warning("Nenhum registro para os filtros selecionados.")
    st.stop()

# --- KPIs ---
faturamento_total = df_filtrado["Faturamento"].sum()
ticket_medio = df_filtrado["Faturamento"].mean()
total_pedidos = len(df_filtrado)
clientes_unicos = df_filtrado["ID_Cliente"].nunique()

clientes_no_filtro = ciclo_vida[ciclo_vida["ID_Cliente"].isin(df_filtrado["ID_Cliente"].unique())]
churn_rate = (clientes_no_filtro["recencia_dias"] > limite_churn).mean() * 100 if len(clientes_no_filtro) else 0.0

base_h1 = clientes_no_filtro[clientes_no_filtro["comprou_h1"]]
taxa_retencao = base_h1["comprou_h2"].mean() * 100 if len(base_h1) else 0.0

col1, col2, col3 = st.columns(3)
col1.metric("Faturamento Total", formatar_moeda(faturamento_total))
col2.metric("Ticket Medio", formatar_moeda(ticket_medio))
col3.metric("Total de Pedidos", formatar_inteiro(total_pedidos))

col4, col5, col6 = st.columns(3)
col4.metric("Clientes Unicos", formatar_inteiro(clientes_unicos))
col5.metric(
    "Churn Rate",
    f"{churn_rate:.1f}%",
    help=f"% de clientes sem compra ha mais de {limite_churn} dias, com base no historico completo.",
)
col6.metric(
    "Taxa de Retencao (1o -> 2o semestre)",
    f"{taxa_retencao:.1f}%",
    help="% de clientes que compraram no 1o semestre de 2025 e voltaram a comprar no 2o semestre.",
)

st.divider()

# --- Serie temporal (sazonalidade) ---
st.subheader("Faturamento ao longo do tempo")
granularidade = st.radio("Granularidade", ["Diaria", "Semanal", "Mensal"], index=2, horizontal=True)
regra = {"Diaria": "D", "Semanal": "W", "Mensal": "MS"}[granularidade]

serie = df_filtrado.set_index("Data_Venda")["Faturamento"].resample(regra).sum().reset_index()
serie["Media movel (3 periodos)"] = serie["Faturamento"].rolling(3, min_periods=1).mean()

fig_serie = px.line(
    serie,
    x="Data_Venda",
    y=["Faturamento", "Media movel (3 periodos)"],
    labels={"value": "Faturamento (R$)", "Data_Venda": "Data", "variable": ""},
)
st.plotly_chart(fig_serie, width="stretch")

# --- Faturamento por categoria e status dos pedidos ---
col_a, col_b = st.columns(2)
with col_a:
    st.subheader("Faturamento por categoria")
    por_categoria = (
        df_filtrado.groupby("Categoria_Produto")["Faturamento"].sum().sort_values(ascending=False).reset_index()
    )
    fig_categoria = px.bar(por_categoria, x="Categoria_Produto", y="Faturamento")
    st.plotly_chart(fig_categoria, width="stretch")

with col_b:
    st.subheader("Status dos pedidos")
    por_status = df_filtrado["Status_Pedido"].value_counts().reset_index()
    por_status.columns = ["Status_Pedido", "qtd"]
    fig_status = px.pie(por_status, names="Status_Pedido", values="qtd", hole=0.4)
    st.plotly_chart(fig_status, width="stretch")

# --- Top produtos e ticket medio por estado ---
col_c, col_d = st.columns(2)
with col_c:
    st.subheader("Top 10 produtos por faturamento")
    top_produtos = (
        df_filtrado.groupby("Nome_Produto")["Faturamento"].sum().sort_values(ascending=False).head(10).reset_index()
    )
    fig_produtos = px.bar(top_produtos, x="Faturamento", y="Nome_Produto", orientation="h")
    fig_produtos.update_yaxes(categoryorder="total ascending")
    st.plotly_chart(fig_produtos, width="stretch")

with col_d:
    st.subheader("Ticket medio por estado")
    por_estado = df_filtrado.groupby("Estado")["Faturamento"].mean().sort_values(ascending=False).reset_index()
    fig_estado = px.bar(por_estado, x="Estado", y="Faturamento")
    st.plotly_chart(fig_estado, width="stretch")
