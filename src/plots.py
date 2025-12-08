# src/plots.py
"""
Gráficos Plotly para dashboard AEMET PRO.
Solo usa columnas que EXISTEN en df (seguro).
"""

import plotly.graph_objs as go
import plotly.express as px


# ================================================================
# 📈 1 — TEMPERATURA
# ================================================================
def crear_grafico_temperatura(df):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["fecha"], y=df["temp_media"],
        name="🌡️ Temp media", mode="lines+markers",
        line=dict(width=2)
    ))

    # Tendencia 7 días (ASEGURADO por preprocessing)
    if "temp_media_mov7" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["fecha"], y=df["temp_media_mov7"],
            name="📈 Tendencia 7d",
            line=dict(width=2, dash='dash')
        ))

    fig.update_layout(title="Evolución de Temperaturas", height=400)
    return fig


# ================================================================
# 🌧️ 2 — PRECIPITACIÓN
# ================================================================
def crear_grafico_precipitacion(df):
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["fecha"], y=df["lluvia"],
        name="🌧️ Lluvia diaria"
    ))

    if "lluvia_acum7" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["fecha"], y=df["lluvia_acum7"],
            name="📉 Acumulado 7d", line=dict(width=2)
        ))

    fig.update_layout(title="Precipitación", height=400)
    return fig


# ================================================================
# 🧬 3 — ÍNDICES TÉRMICOS
# ================================================================
def crear_grafico_indices(df):
    fig = go.Figure()

    if "thi" in df:
        fig.add_trace(go.Scatter(
            x=df["fecha"], y=df["thi"], name="🔥 THI"
        ))

    if "humidex" in df:
        fig.add_trace(go.Scatter(
            x=df["fecha"], y=df["humidex"], name="🥵 Humidex"
        ))

    fig.update_layout(title="Índices Térmicos", height=400)
    return fig


# ================================================================
# ⚠️ 4 — ANOMALÍAS
# ================================================================
def crear_grafico_anomalias(df):
    if "anomaly" not in df:
        return go.Figure()

    fig = px.scatter(
        df, x="fecha", y="temp_media",
        color="anomaly", color_discrete_map={True: "red", False: "blue"},
        title="Anomalías térmicas"
    )
    return fig


# ================================================================
# 📊 5 — DISTRIBUCIÓN
# ================================================================
def crear_grafico_distribucion(df):
    fig = px.histogram(df, x="temp_media", nbins=40, title="Distribución de Temp")
    return fig


# ================================================================
# 🔗 6 — CORRELACIÓN (SAFE VERSION)
# ================================================================
def crear_grafico_correlacion(df):
    # Usamos SOLO columnas que EXISTEN
    usable_cols = [c for c in ["temp_media", "humedad_media", "lluvia"] if c in df]

    fig = px.scatter_matrix(
        df[usable_cols],
        title="Matriz de correlación T° / HR / Rain"
    )
    fig.update_traces(diagonal_visible=False)
    return fig


# ================================================================
# 📅 7 — SEMANAL
# ================================================================
def crear_grafico_semanal(df):
    if len(df) < 7:
        return None

    df = df.copy()
    df["semana"] = df["fecha"].dt.isocalendar().week

    sem = df.groupby("semana").agg(
        temp_media=("temp_media", "mean"),
        lluvia=("lluvia", "sum")
    ).reset_index()

    fig = px.line(sem, x="semana", y="temp_media", title="Temp media por semana")
    return fig
