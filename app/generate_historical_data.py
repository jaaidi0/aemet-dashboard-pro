""" AEMET Weather Analytics v3.1
Dashboard meteorológico avanzado con predicciones, anomalías e índices.
Autor: Jaidi
GitHub: https://github.com/jaaidi0
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import numpy as np
import os
import requests
from dotenv import load_dotenv
from pathlib import Path
import logging

# ============================================================================
# CONFIGURACIÓN Y LOGGING
# ============================================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="AEMET Weather Analytics",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# .ENV
load_dotenv()
AEMET_API_KEY = os.getenv("AEMET_API_KEY")
IDEMAS_OBJETIVO = set(
    (os.getenv("AEMET_IDEMAS") or "5783,5788X,5790Y")
    .replace(" ", "")
    .split(",")
)

logger.info(f"Estaciones monitoreadas: {IDEMAS_OBJETIVO}")

# ============================================================================
# FUNCIONES DE API Y CARGA DE DATOS
# ============================================================================

@st.cache_resource
def get_session():
    """Sesión HTTP reutilizable"""
    return requests.Session()

@st.cache_data(ttl=300, show_spinner=False)
def descargar_observacion_convencional():
    """Descarga observaciones de AEMET OpenData"""
    if not AEMET_API_KEY:
        return None

    url_api = "https://opendata.aemet.es/opendata/api/observacion/convencional/todas"
    try:
        session = get_session()
        resp = session.get(
            url_api,
            params={"api_key": AEMET_API_KEY},
            timeout=20
        )
        
        if resp.status_code != 200:
            return None
        
        payload = resp.json()
        url_datos = payload.get("datos")
        if not url_datos:
            return None

        datos_resp = session.get(url_datos, timeout=30)
        if datos_resp.status_code != 200:
            return None
        
        registros = datos_resp.json()
        rows = []
        
        for r in registros:
            idema = r.get("idema")
            if idema and idema in IDEMAS_OBJETIVO:
                fint = r.get("fint")
                if not fint:
                    continue
                fecha = fint[:10]
                rows.append({
                    "fecha": fecha,
                    "idema": idema,
                    "ta": r.get("ta"),
                    "prec": r.get("prec"),
                    "vv": r.get("vv"),
                    "hr": r.get("hr"),
                })

        if not rows:
            return None

        df_api = pd.DataFrame(rows)
        df_api["fecha"] = pd.to_datetime(df_api["fecha"]).dt.floor("D")
        for col in ["ta", "prec", "vv", "hr"]:
            df_api[col] = pd.to_numeric(df_api[col], errors="coerce")

        logger.info(f"✓ {len(df_api)} registros desde API")
        return df_api

    except Exception as e:
        logger.error(f"Error API: {e}")
        return None

@st.cache_data(ttl=1800)
def cargar_datos():
    """Carga datos: API primero, CSV fallback"""
    df_origen = descargar_observacion_convencional()
    if df_origen is not None:
        st.session_state["fuente_datos"] = "🟢 AEMET OpenData"
    else:
        # Fallback CSV
        posibles_rutas = [
            Path("data_clean/aemet_obs_local_daily.csv"),
            Path("../data_clean/aemet_obs_local_daily.csv"),
            Path("../../data_clean/aemet_obs_local_daily.csv")
        ]
        archivo = next((r for r in posibles_rutas if r.exists()), None)
        if archivo is None:
            st.session_state["fuente_datos"] = "❌ Sin datos"
            return None
        
        df_origen = pd.read_csv(archivo, parse_dates=["fecha"])
        st.session_state["fuente_datos"] = "🟡 CSV local"

    # Normalizar
    df_origen["fecha"] = pd.to_datetime(df_origen["fecha"]).dt.floor("D")
    df_origen = df_origen.sort_values("fecha")

    # Si vienen agregados, usarlos directamente
    if "idema" not in df_origen.columns:
        agg = df_origen
    else:
        # Agregación diaria
        agg = df_origen.groupby("fecha").agg({
            "ta": ["mean", "min", "max"],
            "prec": "sum",
            "vv": "mean",
            "hr": "mean"
        }).round(2)
        agg.columns = ["temp_media", "temp_min", "temp_max",
                       "lluvia_total", "viento_medio", "humedad_media"]
        agg = agg.reset_index()

    # Asegurar columnas esperadas
    if "temp_media" not in agg.columns:
        agg = agg.rename(columns={"ta": "temp_media", "prec": "lluvia_total", 
                                   "vv": "viento_medio", "hr": "humedad_media"})
    
    # Métricas adicionales
    agg["temp_media_mov7"] = agg["temp_media"].rolling(7, min_periods=1).mean().round(2)
    agg["lluvia_acum7"] = agg["lluvia_total"].rolling(7, min_periods=1).sum().round(2)
    agg["dia_semana"] = pd.to_datetime(agg["fecha"]).dt.day_name()
    agg["mes"] = pd.to_datetime(agg["fecha"]).dt.strftime("%B")
    
    # Índices térmicos
    T = agg["temp_media"]
    RH = agg["humedad_media"]
    
    # Dew Point
    a, b = 17.27, 237.7
    alpha = ((a*T)/(b+T)) + np.log(np.clip(RH, 1, 100)/100.0)
    agg["dew_point"] = (b*alpha/(a-alpha)).round(1)
    
    # THI
    agg["thi"] = (T - (0.55 - 0.0055*RH) * (T - 14.5)).round(1)
    
    # Humidex
    Td = agg["dew_point"]
    e = 6.11 * np.exp(5417.7530 * (1/273.16 - 1/(Td+273.16)))
    agg["humidex"] = (T + 0.5555 * (e - 10)).round(1)
    
    # Anomalías (z-score)
    agg["zscore"] = 0.0
    agg["anomaly"] = False
    
    if len(agg) > 7:
        temp_mean = agg["temp_media"].mean()
        temp_std = agg["temp_media"].std()
        if temp_std > 0:
            agg["zscore"] = ((agg["temp_media"] - temp_mean) / temp_std).round(2)
            agg["anomaly"] = np.abs(agg["zscore"]) >= 2.5

    return agg

def calcular_estadisticas(df):
    """Calcula estadísticas del período"""
    if df is None or len(df) == 0:
        return {}
    
    stats = {
        "temp_media": df["temp_media"].mean(),
        "temp_max": df["temp_max"].max() if "temp_max" in df else df["temp_media"].max(),
        "temp_min": df["temp_min"].min() if "temp_min" in df else df["temp_media"].min(),
        "lluvia_total": df["lluvia_total"].sum(),
        "dias_lluvia": (df["lluvia_total"] > 0).sum(),
        "viento_medio": df["viento_medio"].mean(),
        "humedad_media": df["humedad_media"].mean(),
        "thi_media": df["thi"].mean(),
        "dias_totales": len(df),
        "anomalias": (df["anomaly"] == True).sum()
    }
    
    if len(df) >= 14:
        ultimos_7 = df.tail(7)["temp_media"].mean()
        anteriores_7 = df.iloc[-14:-7]["temp_media"].mean()
        stats["tendencia"] = ultimos_7 - anteriores_7
    else:
        stats["tendencia"] = 0
    
    return stats

# ============================================================================
# FUNCIONES DE GRÁFICOS
# ============================================================================

def crear_grafico_temperatura(df):
    """Gráfico de temperatura con banda de rango"""
    fig = go.Figure()
    
    if "temp_max" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["fecha"], y=df["temp_max"],
            name="Máxima", line=dict(width=0), showlegend=False
        ))
        fig.add_trace(go.Scatter(
            x=df["fecha"], y=df["temp_min"],
            name="Rango", fill='tonexty', line=dict(width=0),
            fillcolor='rgba(173,216,230,0.3)'
        ))
    
    fig.add_trace(go.Scatter(
        x=df["fecha"], y=df["temp_media"],
        name="Media", mode='lines+markers',
        line=dict(color='#ef4444', width=3),
        marker=dict(size=6),
        hovertemplate="<b>%{x|%d/%m}</b><br>%{y:.1f}°C"
    ))
    fig.add_trace(go.Scatter(
        x=df["fecha"], y=df["temp_media_mov7"],
        name="Media 7d", line=dict(color='#f59e0b', width=2, dash='dash')
    ))
    fig.update_layout(
        title="🌡️ Temperatura",
        xaxis_title="Fecha", yaxis_title="°C",
        template='plotly_white', height=350,
        hovermode='x unified', legend=dict(orientation="h", y=1.02)
    )
    return fig

def crear_grafico_precipitacion(df):
    """Gráfico de precipitación"""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    colors = ['#3b82f6' if x > 0 else '#e5e7eb' for x in df["lluvia_total"]]
    fig.add_trace(
        go.Bar(x=df["fecha"], y=df["lluvia_total"],
               name="Lluvia Diaria", marker_color=colors),
        secondary_y=False
    )
    fig.add_trace(
        go.Scatter(x=df["fecha"], y=df["lluvia_acum7"],
                   name="Acum 7d", line=dict(color='#1e40af', width=3)),
        secondary_y=True
    )
    fig.update_layout(
        title="🌧️ Precipitación",
        template='plotly_white', height=350, hovermode='x unified'
    )
    return fig

def crear_grafico_indices(df):
    """Gráfico de índices térmicos"""
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df["fecha"], y=df["thi"], name="THI",
        line=dict(color='#1f77b4', width=2)
    ))
    fig.add_trace(go.Scatter(
        x=df["fecha"], y=df["humidex"], name="Humidex",
        line=dict(color='#ff7f0e', width=2)
    ))
    fig.add_trace(go.Scatter(
        x=df["fecha"], y=df["dew_point"], name="Dew Point",
        line=dict(color='#2ca02c', width=2)
    ))
    
    fig.add_hrect(y0=21, y1=26, fillcolor="green", opacity=0.1,
                  annotation_text="Confort", annotation_position="left")
    
    fig.update_layout(
        title="🌡️ Índices Térmicos",
        xaxis_title="Fecha", yaxis_title="°C",
        template='plotly_white', height=350,
        hovermode='x unified', legend=dict(orientation="h")
    )
    return fig

def crear_grafico_anomalias(df):
    """Gráfico con anomalías resaltadas"""
    df_norm = df[~df["anomaly"]].copy()
    df_anom = df[df["anomaly"]].copy()
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df_norm["fecha"], y=df_norm["temp_media"],
        mode="lines", name="Temperatura",
        line=dict(color="#ef4444", width=2)
    ))
    
    if len(df_anom) > 0:
        fig.add_trace(go.Scatter(
            x=df_anom["fecha"], y=df_anom["temp_media"],
            mode="markers", name="Anomalías",
            marker=dict(color="red", size=10, symbol="diamond")
        ))
    
    fig.update_layout(
        title="🌡️ Temperatura + Anomalías",
        xaxis_title="Fecha", yaxis_title="°C",
        template='plotly_white', height=350
    )
    return fig

def crear_grafico_distribucion(df):
    """Histograma de distribución de temperaturas"""
    fig = px.histogram(
        df, x="temp_media", nbins=20,
        title="📊 Distribución de Temperaturas",
        labels={"temp_media": "Temperatura (°C)", "count": "Frecuencia"},
        color_discrete_sequence=['#ef4444']
    )
    fig.update_layout(template='plotly_white', height=350)
    return fig

def crear_grafico_correlacion(df):
    """Scatter: Temperatura vs Humedad"""
    fig = px.scatter(
        df, x="temp_media", y="humedad_media",
        size="lluvia_total", color="thi",
        color_continuous_scale="RdYlBu_r",
        title="📊 Correlación Temp-Humedad",
        labels={"temp_media": "Temperatura (°C)", "humedad_media": "Humedad (%)"}
    )
    fig.update_layout(template='plotly_white', height=350)
    return fig

def crear_grafico_semanal(df):
    """Comparativa semanal"""
    if len(df) < 7:
        return None
    
    resumen = df.groupby("dia_semana").agg({
        "temp_media": "mean",
        "lluvia_total": "sum",
        "viento_medio": "mean"
    }).reset_index()
    
    dias_orden = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dias_label = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    
    resumen["dia_semana"] = pd.Categorical(resumen["dia_semana"], categories=dias_orden, ordered=True)
    resumen = resumen.sort_values("dia_semana")
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=dias_label[:len(resumen)],
        y=resumen["temp_media"],
        name="Temp Media (°C)",
        marker_color='#ef4444'
    ))
    fig.update_layout(
        title="📅 Temperatura Media por Día",
        xaxis_title="Día de la semana",
        yaxis_title="Temperatura (°C)",
        template='plotly_white', height=350
    )
    return fig

# ============================================================================
# HEADER
# ============================================================================
if "fuente_datos" not in st.session_state:
    st.session_state["fuente_datos"] = "desconocida"

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.markdown("# 🌤️ AEMET Weather Analytics v3.1")
    st.markdown("**Análisis Meteorológico Avanzado**")
with col2:
    if st.button("🔄 Actualizar", width='stretch'):
        st.cache_data.clear()
        st.rerun()
with col3:
    fuente = st.session_state.get("fuente_datos", "?")
    st.markdown(f"**{fuente}**")

st.markdown("---")

# ============================================================================
# CARGAR DATOS
# ============================================================================
df = cargar_datos()
if df is None:
    st.error("❌ No se pudieron cargar los datos")
    st.info("💡 Ejecuta: `python generate_historical_data.py` para crear datos de prueba")
    st.stop()

# ============================================================================
# SIDEBAR
# ============================================================================
with st.sidebar:
    st.markdown("## 🛋️ Controles")
    
    fuente = st.session_state.get("fuente_datos", "desconocida")
    st.markdown(f"**{fuente}**")
    
    st.caption(f"Rango: {df['fecha'].min().date()} → {df['fecha'].max().date()}")
    
    st.markdown("### 📅 Filtro de Fechas")
    fecha_min = df["fecha"].min().date()
    fecha_max = df["fecha"].max().date()
    
    rango_preset = st.selectbox(
        "Período rápido:",
        ["Todo", "Últimos 7d", "Últimos 14d", "Últimos 30d", "Últimos 90d", "Personalizado"]
    )
    
    if rango_preset == "Últimos 7d":
        fecha_inicio = fecha_max - timedelta(days=7)
        fecha_fin = fecha_max
    elif rango_preset == "Últimos 14d":
        fecha_inicio = fecha_max - timedelta(days=14)
        fecha_fin = fecha_max
    elif rango_preset == "Últimos 30d":
        fecha_inicio = fecha_max - timedelta(days=30)
        fecha_fin = fecha_max
    elif rango_preset == "Últimos 90d":
        fecha_inicio = fecha_max - timedelta(days=90)
        fecha_fin = fecha_max
    elif rango_preset == "Personalizado":
        c1, c2 = st.columns(2)
        with c1:
            fecha_inicio = st.date_input("Desde:", fecha_min)
        with c2:
            fecha_fin = st.date_input("Hasta:", fecha_max)
    else:
        fecha_inicio = fecha_min
        fecha_fin = fecha_max
    
    if fecha_inicio > fecha_fin:
        fecha_inicio, fecha_fin = fecha_fin, fecha_inicio
    
    mask = (df["fecha"].dt.date >= fecha_inicio) & (df["fecha"].dt.date <= fecha_fin)
    df_filtrado = df[mask].copy()
    
    st.markdown("---")
    st.markdown("### ℹ️ Dataset")
    st.metric("Días", len(df_filtrado))
    st.caption(f"{fecha_inicio} → {fecha_fin}")
    
    st.markdown("---")
    st.caption("AEMET OpenData")

# ============================================================================
# MÉTRICAS
# ============================================================================
stats = calcular_estadisticas(df_filtrado)

st.markdown("## 📊 Resumen del Período")
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric("🌡️ Temp Media", f"{stats.get('temp_media', 0):.1f}°C",
              delta=f"{stats.get('tendencia', 0):+.1f}°" if abs(stats.get('tendencia', 0)) > 0.1 else None)

with c2:
    st.metric("🌧️ Lluvia Total", f"{stats.get('lluvia_total', 0):.1f}mm",
              delta=f"{stats.get('dias_lluvia', 0)}d")

with c3:
    st.metric("💨 Viento Medio", f"{stats.get('viento_medio', 0):.1f}m/s")

with c4:
    st.metric("💧 Humedad", f"{stats.get('humedad_media', 0):.0f}%")

st.markdown("---")

# ============================================================================
# TABS
# ============================================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Series Temporales",
    "🌡️ Índices & Anomalías",
    "📊 Análisis Avanzado",
    "📋 Estadísticas",
    "📥 Exportar"
])

with tab1:
    st.markdown("### Evolución de Variables")
    st.plotly_chart(crear_grafico_temperatura(df_filtrado), width='stretch')
    st.plotly_chart(crear_grafico_precipitacion(df_filtrado), width='stretch')

with tab2:
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(crear_grafico_indices(df_filtrado), width='stretch')
    with c2:
        st.plotly_chart(crear_grafico_anomalias(df_filtrado), width='stretch')
    
    st.markdown("### 📋 Referencia (THI)")
    ref = pd.DataFrame({
        "Rango THI": ["< 21", "21-26", "26-29", "> 29"],
        "Estado": ["Confort", "Cálido", "Disconfort", "⚠️ Alerta"],
    })
    st.dataframe(ref, width='stretch', hide_index=True)

with tab3:
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(crear_grafico_distribucion(df_filtrado), width='stretch')
    with c2:
        st.plotly_chart(crear_grafico_correlacion(df_filtrado), width='stretch')
    
    if crear_grafico_semanal(df_filtrado):
        st.plotly_chart(crear_grafico_semanal(df_filtrado), width='stretch')

with tab4:
    st.markdown("### Estadísticas Descriptivas")
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("#### Temperatura")
        st.dataframe(
            df_filtrado[["temp_media"]].describe().round(2),
            width='stretch'
        )
    
    with c2:
        st.markdown("#### Otros")
        st.dataframe(
            df_filtrado[["lluvia_total", "viento_medio", "humedad_media"]].describe().round(2),
            width='stretch'
        )
    
    if len(df_filtrado[df_filtrado["anomaly"]]) > 0:
        st.markdown("### ⚠️ Anomalías Detectadas")
        st.dataframe(
            df_filtrado[df_filtrado["anomaly"]][["fecha", "temp_media", "zscore"]],
            width='stretch'
        )

with tab5:
    st.markdown("### 📥 Descargar Datos")
    
    c1, c2 = st.columns(2)
    
    with c1:
        csv = df_filtrado.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📄 CSV",
            data=csv,
            file_name=f"aemet_{fecha_inicio}_{fecha_fin}.csv",
            mime="text/csv",
            width='stretch'
        )
    
    with c2:
        json_data = df_filtrado.to_json(orient='records', date_format='iso')
        st.download_button(
            label="📄 JSON",
            data=json_data,
            file_name=f"aemet_{fecha_inicio}_{fecha_fin}.json",
            mime="application/json",
            width='stretch'
        )
    
    st.markdown("---")
    st.dataframe(
        df_filtrado[[
            "fecha", "temp_media", "lluvia_total", "viento_medio",
            "humedad_media", "thi", "anomaly"
        ]].tail(20),
        width='stretch'
    )

# ============================================================================
# FOOTER
# ============================================================================
st.markdown("---")
st.markdown("""
**AEMET Weather Analytics v3.1** | [GitHub](https://github.com/jaaidi0) | Datos: AEMET OpenData
""", unsafe_allow_html=True)