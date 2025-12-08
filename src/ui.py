import streamlit as st

def setup_css():

    st.markdown("""
    <style>

    /* ==========================================================
       🌑 DARK ANIME · ONE PIECE · BIO-TECH · DATA SCIENCE THEME 
       ========================================================== */

    :root {
        --dark-bg: #050708;
        --dark-panel: #0d1214;
        --dark-card: #11181b;
        --accent-green: #32ff8e;
        --accent-green-soft: rgba(50,255,142,0.35);
        --accent-blue: #37c7ff;
        --accent-gold: #f4d47c;
        --accent-red: #ff4d4d;
        --text-main: #e9efec;
        --border: rgba(255,255,255,0.07);
        --shadow-strong: 0 0 35px rgba(0,255,150,0.22);
        --shadow-soft: 0 0 20px rgba(0,255,150,0.12);
    }

    /* ==========================================================
       🌌 BACKGROUND GLOBAL CON ANIMACIÓN SUAVE 
       ========================================================== */
    body, .main {
        background: var(--dark-bg) !important;
        animation: bgShift 20s infinite alternate ease-in-out;
    }

    @keyframes bgShift {
        0% { background: #050708; }
        100% { background: #0a0f13; }
    }

    /* ==========================================================
       ⚓ SIDEBAR · ESTILO BARCO DE LOS SOMBRERO DE PAJA
       ========================================================== */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #080c0d 0%, #0e1517 100%) !important;
        border-right: 1px solid var(--border);
        box-shadow: -4px 0 30px rgba(0,255,140,0.05);
        animation: sidebarFade 1.3s ease-out;
    }

    @keyframes sidebarFade {
        from { transform: translateX(-20px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }

    [data-testid="stSidebar"] * {
        color: #dff7ec !important;
        font-weight: 500;
    }

    /* Botones del sidebar */
    [data-testid="stSidebar"] button {
        background: linear-gradient(135deg, var(--accent-green), #0fff9f);
        color: #000 !important;
        border-radius: 12px !important;
        border: none !important;
        box-shadow: 0 0 22px rgba(50,255,142,0.5);
        transition: 0.2s ease;
    }

    [data-testid="stSidebar"] button:hover {
        transform: scale(1.07) rotate(-1deg);
        box-shadow: var(--shadow-strong);
    }

    /* ==========================================================
       📊 TABS · ESTILO POKEDEX · HACKER · CIBERPUNK AGRÓNOMO
       ========================================================== */
    .stTabs [data-baseweb="tab"] {
        background: var(--dark-panel) !important;
        border-radius: 12px 12px 0 0 !important;
        margin-right: 6px;
        padding: 8px 18px !important;
        color: #bfe6d8 !important;
        font-weight: 600;
        border: 1px solid var(--border);
        transition: 0.15s ease;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, var(--accent-blue), var(--accent-green)) !important;
        color: #000 !important;
        border-bottom: 3px solid var(--accent-gold) !important;
        box-shadow: 0 0 25px rgba(0,255,190,0.45);
        transform: translateY(-2px);
    }

    /* ==========================================================
       📈 GRÁFICOS · PANEL DE NAVE CIENTÍFICA DE WANO
       ========================================================== */
    .stPlotlyChart {
        background: var(--dark-card) !important;
        padding: 20px;
        border-radius: 16px;
        border: 1px solid var(--border);
        box-shadow: var(--shadow-soft);
        animation: chartRise 0.8s ease-out;
        transition: 0.25s ease;
    }

    @keyframes chartRise {
        from { transform: translateY(15px); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
    }

    .stPlotlyChart:hover {
        transform: scale(1.015);
        box-shadow: 0 0 30px var(--accent-green-soft);
    }

    /* ==========================================================
       🧪 TABLAS · LABORATORIO DE ANÁLISIS
       ========================================================== */
    .dataframe {
        background: var(--dark-card) !important;
        color: var(--text-main) !important;
        border-radius: 16px;
        border: 1px solid var(--border) !important;
        box-shadow: var(--shadow-soft);
        animation: tableSpawn 0.7s ease-out;
    }

    @keyframes tableSpawn {
        from { opacity: 0; transform: scale(0.97); }
        to { opacity: 1; transform: scale(1); }
    }

    /* ==========================================================
       🔘 BOTONES GENERALES · CYBERPUNK AGRÓNOMO
       ========================================================== */
    .stButton>button {
        background: linear-gradient(135deg, var(--accent-blue), var(--accent-green));
        border-radius: 14px;
        border: none;
        padding: 12px 20px;
        font-size: 16px;
        font-weight: 700;
        color: #000 !important;
        box-shadow: 0 0 22px rgba(0,255,200,0.35);
        transition: 0.25s;
    }

    .stButton>button:hover {
        transform: translateY(-3px) scale(1.03);
        box-shadow: 0 0 30px rgba(0,255,255,0.6);
    }

    /* EDITAR SLIDERS / SELECTBOX PARA VISIBILIDAD PERFECTA */
    .stSelectbox, select, input {
        background: var(--dark-panel) !important;
        border-radius: 10px !important;
        border: 1px solid var(--border) !important;
        color: var(--text-main) !important;
    }

    input:focus, select:focus {
        border-color: var(--accent-blue) !important;
        box-shadow: 0 0 8px var(--accent-blue);
    }

    /* ==========================================================
       ✨ SCROLLBAR CUSTOM 
       ========================================================== */
    ::-webkit-scrollbar {
        width: 10px;
    }
    ::-webkit-scrollbar-thumb {
        background: var(--accent-green);
        border-radius: 10px;
    }

    /* ==========================================================
       ⚡ ALERTAS DE SISTEMA
       ========================================================== */
    .stAlert {
        background: var(--dark-card) !important;
        border-left: 5px solid var(--accent-green) !important;
        border-radius: 12px;
        animation: alertPulse 1s ease;
    }

    @keyframes alertPulse {
        from { transform: scale(0.98); opacity: 0; }
        to { transform: scale(1); opacity: 1; }
    }

    </style>
    """, unsafe_allow_html=True)
