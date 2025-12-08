# app/streamlit_app.py
"""
AEMET · Grand Line Dashboard
Versión PLATINO: Mapa estático (cero parpadeos) y logs silenciados.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import logging
import pandas as pd
import streamlit as st
import time
import warnings

# --- IMPORTS MAPA ---
import folium
from streamlit_folium import folium_static  # CAMBIO CLAVE: Usamos static para evitar "baile"
# --------------------

# Silenciar ruido de hilos/asyncio al cerrar
logging.getLogger('asyncio').setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parent.parent
SRC = BASE / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ui import setup_css
from api import cargar_datos, estacion_cache, rate_limiter
from preprocessing import enrich_indices, calcular_estadisticas
from plots import (
    crear_grafico_temperatura,
    crear_grafico_precipitacion,
    crear_grafico_indices,
    crear_grafico_anomalias,
    crear_grafico_distribucion,
    crear_grafico_correlacion,
    crear_grafico_semanal,
)
from utils import df_to_csv_bytes, df_to_excel_bytes

try:
    from logger import setup_logger
    logger = setup_logger()
except Exception:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("aemet_dashboard")


# --------------------------------------
#   PAGE CONFIG
# --------------------------------------
st.set_page_config(
    page_title="AEMET – Grand Line PRO",
    layout="wide",
    initial_sidebar_state="expanded",
)

setup_css()


# --------------------------------------
#   SESSION STATE INIT
# --------------------------------------
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
    st.session_state.df = None
    st.session_state.fuente = None
    st.session_state.logs = []
    st.session_state.metricas_carga = []
    st.session_state.tiempo_carga = 0


# --------------------------------------
#   FUNCIONES CON CACHÉ (CORE)
# --------------------------------------

@st.cache_data(show_spinner=False)
def procesar_datos_dashboard(df: pd.DataFrame, dias: int):
    """Procesa datos con caché para evitar recálculos en cada interacción"""
    df_proc = df.copy()
    try:
        df_proc["fecha"] = pd.to_datetime(df_proc["fecha"], utc=True).dt.tz_convert("Europe/Madrid").dt.tz_localize(None)
    except:
        df_proc["fecha"] = pd.to_datetime(df_proc["fecha"])

    fecha_limite = datetime.now() - timedelta(days=dias)
    dfp = df_proc[df_proc["fecha"] >= fecha_limite].copy().sort_values("fecha")

    dfp = enrich_indices(dfp)
    stats = calcular_estadisticas(dfp)
    
    # Este log solo saldrá UNA vez si los datos no cambian
    # logger.info(f"✅ Datos procesados: {len(dfp)} registros")
    
    return dfp, stats

@st.cache_data(show_spinner=False)
def generar_mapa_base(df_mapa: pd.DataFrame):
    """Genera el objeto mapa folium"""
    if df_mapa is None or df_mapa.empty:
        return None

    mapa = folium.Map(
        location=[37.40, -6.0], 
        zoom_start=9, 
        tiles="CartoDB dark_matter"
    )

    ultimos_datos = df_mapa.sort_values("fecha").groupby("estacion").last().reset_index()

    coords_demo = {
        "5788X": [37.519, -6.230],  # Aznalcóllar
        "5790Y": [37.417, -5.895],  # Sevilla Aeropuerto
        "5783":  [37.375, -5.990]   # Sevilla Tablada
    }

    for _, row in ultimos_datos.iterrows():
        est = row['estacion']
        lat, lon = coords_demo.get(est, [37.38 + (hash(est) % 100)/1000, -5.98])
        
        temp = row.get('temp_media', 0)
        lluvia = row.get('lluvia', 0)
        
        # Lógica de color
        color_icon = "#ff4b4b" if temp > 35 else "#ffa500" if temp > 25 else "#00c0f2"
        
        html = f"""
        <div style="font-family:sans-serif; min-width:120px">
            <h4 style="margin:0; color:#333">{est}</h4>
            <hr style="margin:5px 0">
            <b>🌡️ Temp:</b> {temp:.1f}°C<br>
            <b>🌧️ Lluvia:</b> {lluvia:.1f}mm<br>
            <small style="color:#666">{row['fecha'].strftime('%H:%M')}</small>
        </div>
        """
        
        folium.Marker(
            [lat, lon],
            popup=folium.Popup(html, max_width=200),
            tooltip=f"{est}: {temp:.1f}°C",
            icon=folium.Icon(color="black", icon_color=color_icon, icon="cloud", prefix="fa")
        ).add_to(mapa)

    return mapa


# --------------------------------------
#   CARGA DE DATOS
# --------------------------------------
def cargar_datos_una_vez(forzar: bool = False):
    if st.session_state.data_loaded and not forzar:
        return st.session_state.df, st.session_state.fuente, st.session_state.logs
    
    inicio = time.time()
    # Secuencial = Estabilidad total
    df, fuente, logs = cargar_datos(forzar_api=forzar, usar_paralelo=False)
    tiempo_total = time.time() - inicio
    
    st.session_state.df = df
    st.session_state.fuente = fuente
    st.session_state.logs = logs
    st.session_state.tiempo_carga = tiempo_total
    st.session_state.data_loaded = True
    
    st.session_state.metricas_carga.append({
        'timestamp': datetime.now(),
        'tiempo': tiempo_total,
        'fuente': fuente,
        'registros': len(df) if df is not None else 0
    })
    
    return df, fuente, logs


# --------------------------------------
#   COMPONENTES UI
# --------------------------------------
def mostrar_metricas_performance():
    if not st.session_state.metricas_carga: return
    with st.expander("📊 Métricas de Performance", expanded=False):
        metricas = st.session_state.metricas_carga
        ultima = metricas[-1]
        col1, col3, col4 = st.columns(3)
        col1.metric("⚡ Carga", f"{ultima['tiempo']:.2f}s", delta=f"{ultima['registros']} reg")
        col3.metric("🎯 Caché", f"{(len(metricas)-sum(1 for m in metricas if m['fuente']=='API'))/len(metricas)*100:.0f}%")
        col4.metric("🪙 Tokens", f"{int(rate_limiter.tokens)}/10")

def mostrar_indicador_fuente_avanzado(fuente: str, df: pd.DataFrame):
    if fuente == "API":
        st.success(f"🌐 **En vivo** (AEMET) | 📅 Último dato: {df['fecha'].max().strftime('%H:%M')}")
    elif fuente == "CSV LOCAL":
        st.warning("📁 **Modo Offline** (Datos locales)")
    else:
        st.error("❌ Sin datos disponibles")

def generar_alertas(stats: dict):
    alertas = []
    if stats.get('temp_max', 0) > 38: alertas.append(('error', f"🔥 Calor extremo: {stats['temp_max']:.1f}°C"))
    if stats.get('lluvia_total', 0) > 50: alertas.append(('warn', f"🌊 Lluvia abundante: {stats['lluvia_total']:.1f}mm"))
    return alertas

def mostrar_alertas(alertas: list):
    for level, mensaje in alertas:
        if level == 'error': st.error(mensaje)
        elif level == 'warn': st.warning(mensaje)
        else: st.info(mensaje)


# --------------------------------------
#   MAIN DASHBOARD
# --------------------------------------
def main():
    st.markdown(
        """<div style="position:sticky; top:0; z-index:9999; padding:12px; background:#0e1117; border-bottom:1px solid #333; margin-bottom: 20px;">
            <span style="font-size:22px; font-weight:bold; color:#f6d77a">🏴‍☠️ AEMET · Grand Line PRO</span>
        </div>""",
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.header("⚙️ Configuración")
        dias = st.slider("Rango visual (días)", 7, 365, 30)
        
        col1, col2 = st.columns(2)
        if col1.button("🔄 Recargar"):
            st.session_state.data_loaded = False
            st.rerun()
        if col2.button("🔥 Forzar API"):
            estacion_cache.clear()
            st.session_state.data_loaded = False
            st.rerun()
                
        mostrar_metricas_performance()
        
        with st.expander("📄 Logs del Sistema"):
            for l in st.session_state.logs:
                # Colorear logs para que se vean bonitos
                if "✅" in l: st.markdown(f":green[{l}]")
                elif "⚠️" in l: st.markdown(f":orange[{l}]")
                elif "❌" in l: st.markdown(f":red[{l}]")
                else: st.text(l)

    # 1. CARGA
    try:
        df, fuente, logs = cargar_datos_una_vez(forzar=False)
    except Exception as e:
        st.error(f"❌ Error crítico en carga: {e}")
        st.stop()

    if df is None or df.empty:
        st.warning("⚠️ No hay datos para mostrar. Verifica la conexión.")
        st.stop()

    mostrar_indicador_fuente_avanzado(fuente, df)

    # 2. PROCESAMIENTO (Silencioso gracias a @cache_data)
    dfp, stats = procesar_datos_dashboard(df, dias)

    # KPIs Principales
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("🌡️ Temp Media", f"{stats['temp_media']:.1f}°C")
    k2.metric("🔥 Máxima", f"{stats['temp_max']:.1f}°C")
    k3.metric("🌧️ Lluvia Total", f"{stats['lluvia_total']:.1f}mm")
    k4.metric("💧 Humedad", f"{stats['humedad_media']:.0f}%")

    st.markdown("---")

    # 3. VISUALIZACIÓN DIVIDIDA
    col_izq, col_der = st.columns([2, 3])

    with col_izq:
        st.subheader("🗺️ Mapa de Estaciones")
        
        mapa_obj = generar_mapa_base(dfp)
        if mapa_obj:
            # USAMOS FOLIUM_STATIC -> ¡ADIÓS PARPADEO!
            # width=None se ajusta al ancho de la columna
            folium_static(mapa_obj, height=400, width=None)
        
        alertas = generar_alertas(stats)
        if alertas:
            st.markdown("##### 🚨 Alertas Detectadas")
            mostrar_alertas(alertas)

    with col_der:
        st.subheader("📊 Análisis Detallado")
        
        tab1, tab2, tab3 = st.tabs(["🌡️ Temperaturas", "🌧️ Precipitación", "📥 Exportar"])
        
        with tab1:
            st.plotly_chart(crear_grafico_temperatura(dfp), width="stretch")
        with tab2:
            st.plotly_chart(crear_grafico_precipitacion(dfp), width="stretch")
        with tab3:
            st.dataframe(dfp.tail(15), width="stretch")
            st.download_button(
                "📥 Descargar CSV", 
                df_to_csv_bytes(dfp), 
                f"aemet_export_{datetime.now().strftime('%H%M')}.csv"
            )

    st.markdown("---")
    st.caption(f"🚀 Sistema de Inteligencia Climática | Ejecución estable: {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    main()