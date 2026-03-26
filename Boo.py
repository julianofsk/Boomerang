import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import psycopg2
from datetime import datetime
import calendar

# -----------------------------
# LOGIN
# -----------------------------

def login():
    st.title("Login")

    user = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if user == "admin" and password == "1234":
            st.session_state["logado"] = True
        else:
            st.error("Usuário ou senha inválidos")

if "logado" not in st.session_state:
    st.session_state["logado"] = False

if not st.session_state["logado"]:
    login()
    st.stop()

# -----------------------------
# CONEXÃO BANCO
# -----------------------------

def get_data():
    conn = psycopg2.connect(
        host=st.secrets["DB_HOST"],
        database=st.secrets["DB_NAME"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"]
    )

    query = """
    SELECT emissao, idcobranca, valor
    FROM titulo
    WHERE emissao >= date_trunc('month', CURRENT_DATE) - interval '1 month'
    """

    df = pd.read_sql(query, conn)
    conn.close()

    return df

df = get_data()
df["emissao"] = pd.to_datetime(df["emissao"])

# -----------------------------
# SIDEBAR
# -----------------------------

st.sidebar.title("Configurações")

data_selecionada = st.sidebar.date_input(
    "Selecionar Data",
    value=datetime.today()
)

data_selecionada = pd.to_datetime(data_selecionada).date()

meta_dia = st.sidebar.number_input("Meta do Dia", value=8000)

# -----------------------------
# IDS
# -----------------------------

ids_dinheiro = [1,2,3,6,7,8]
ids_credito = [10]

# -----------------------------
# FILTRO DIA
# -----------------------------

df_dia = df[df["emissao"].dt.date == data_selecionada]

vendas_dinheiro = df_dia[df_dia["idcobranca"].isin(ids_dinheiro)]["valor"].sum()
vendas_credito = df_dia[df_dia["idcobranca"].isin(ids_credito)]["valor"].sum()

# ⚠️ TOTAL DO DIA AGORA É SÓ DINHEIRO
total_dia = vendas_dinheiro

# -----------------------------
# FILTRO MÊS
# -----------------------------

ano = data_selecionada.year
mes = data_selecionada.month

df_mes = df[
    (df["emissao"].dt.year == ano) &
    (df["emissao"].dt.month == mes)
]

# -----------------------------
# DIAS ÚTEIS
# -----------------------------

cal = calendar.monthcalendar(ano, mes)

dias_uteis = sum(
    1 for semana in cal for i, dia in enumerate(semana)
    if dia != 0 and i < 6
)

meta_mensal = meta_dia * dias_uteis

# -----------------------------
# AGRUPAMENTO DIÁRIO
# -----------------------------

df_dinheiro = df_mes[df_mes["idcobranca"].isin(ids_dinheiro)]
df_credito = df_mes[df_mes["idcobranca"].isin(ids_credito)]

# dinheiro
df_dinheiro_dia = df_dinheiro.groupby(df_dinheiro["emissao"].dt.date)["valor"].sum().reset_index()
df_dinheiro_dia.columns = ["data", "valor"]
df_dinheiro_dia = df_dinheiro_dia.sort_values("data")

df_dinheiro_dia["acumulado"] = df_dinheiro_dia["valor"].cumsum()
df_dinheiro_dia["meta_acumulada"] = [
    meta_dia * (i+1) for i in range(len(df_dinheiro_dia))
]

# crédito
df_credito_dia = df_credito.groupby(df_credito["emissao"].dt.date)["valor"].sum().reset_index()
df_credito_dia.columns = ["data", "valor"]
df_credito_dia = df_credito_dia.sort_values("data")

# -----------------------------
# LAYOUT
# -----------------------------

st.title("Boomerang Kids")
st.subheader(f"📅 Data: {data_selecionada}")

# -----------------------------
# GAUGE META DIA (DINHEIRO)
# -----------------------------

fig_gauge = go.Figure(go.Indicator(
    mode="gauge+number+delta",
    value=total_dia,
    delta={"reference": meta_dia},
    title={"text": "Meta do Dia"},
    gauge={"axis": {"range": [None, meta_dia]}}
))

st.plotly_chart(fig_gauge, width="stretch")

# -----------------------------
# PIZZA (COMPARAÇÃO)
# -----------------------------

fig_pizza = px.pie(
    names=["Dinheiro","Crédito Loja"],
    values=[vendas_dinheiro, vendas_credito],
    title="Dinheiro vs Crédito (Dia)"
)

st.plotly_chart(fig_pizza, width="stretch")

# -----------------------------
# FATURAMENTO DINHEIRO
# -----------------------------

fig_dinheiro = px.bar(
    df_dinheiro_dia,
    x="data",
    y="valor",
    title="Faturamento Diário - Dinheiro"
)

st.plotly_chart(fig_dinheiro, width="stretch")

# -----------------------------
# FATURAMENTO CRÉDITO
# -----------------------------

fig_credito = px.bar(
    df_credito_dia,
    x="data",
    y="valor",
    title="Faturamento Diário - Crédito Loja"
)

st.plotly_chart(fig_credito, width="stretch")

# -----------------------------
# EVOLUÇÃO META (SÓ DINHEIRO)
# -----------------------------

fig_meta = go.Figure()

fig_meta.add_trace(go.Scatter(
    x=df_dinheiro_dia["data"],
    y=df_dinheiro_dia["acumulado"],
    name="Faturamento (Dinheiro)"
))

fig_meta.add_trace(go.Scatter(
    x=df_dinheiro_dia["data"],
    y=df_dinheiro_dia["meta_acumulada"],
    name="Meta"
))

fig_meta.update_layout(title="Evolução Meta Mensal")

st.plotly_chart(fig_meta, width="stretch")

# -----------------------------
# KPIs
# -----------------------------

col1, col2, col3 = st.columns(3)

col1.metric("Faturamento Dia", f"R$ {total_dia:,.0f}")
col2.metric("Crédito no Dia", f"R$ {vendas_credito:,.0f}")
col3.metric("Meta Mensal", f"R$ {meta_mensal:,.0f}")
