
# 🌤️ AEMET Weather Analytics — v3.1

Dashboard geoespacial (Streamlit) con **ETL robusta**, **caché inteligente** y visualizaciones **Plotly** sobre la **API AEMET OpenData**. Monitorea temperatura, humedad, precipitación e **índices térmicos** (THI, Humidex, Dew Point), con **detección de anomalías** y exportación de datos.

[![Estado](https://img.shields.io/badge/Estado-FUNCIONAL-00c853)](#)
[![Versión](https://img.shields.io/badge/Versión-3.1-blue)](#)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](#)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28.1-FF4B4B?logo=streamlit&logoColor=white)](#)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🔗 Live Demo
**App en vivo (Streamlit Cloud):**  
👉 [https://aemet-dashboard-pro-3s9ay3cnvowfgvrutqvh4w.streamlit.app](https://aemet-dashboard-pro-3s9ay3cnvowfgvrutqvh4w.streamlit.app)

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://aemet-dashboard-pro-3s9ay3cnvowfgvrutqvh4w.streamlit.app)

---

## 📑 Tabla de Contenidos
- [✨ Características](#-características)
- [🖼️ Capturas](#-capturas-del-dashboard)
- [🧭 Arquitectura](#-arquitectura--estructura)
- [⚙️ Instalación](#-instalación)
- [🔐 Configuración](#-configuración-env)
- [▶️ Ejecución](#-ejecución-local)
- [🚀 Despliegue](#-despliegue-en-streamlit-cloud)
- [📂 Datos y Referencias](#-datos-y-referencias)
- [📄 Licencia](#-licencia)
- [👤 Autor](#-autor)

---

## ✨ Características
- **Datos en tiempo real** desde **AEMET OpenData** (36+ registros/día).
- **Fallback CSV** cuando la API falla.
- **Caché inteligente** (5–30 min).
- **3 estaciones**: Sevilla (5783), Córdoba (5788X), Jaén (5790Y).
- **5 pestañas**:
  1. Series Temporales
  2. Índices & Anomalías
  3. Análisis Avanzado
  4. Estadísticas
  5. Exportar
- **Visualizaciones**: 10+ gráficos interactivos (Plotly).
- **Mapa estático** con Folium.
- **Exportación**: CSV/Excel.

---

## 🖼️ Capturas del Dashboard
*(Sube tus imágenes a `docs/screenshots/` y ajusta las rutas)*

### 🗺️ Mapa de Estaciones
![Mapa](https://aemet-dashboard-pro-3s9ay3cnvowfgvrutqvh4w.streamlit.app/)

### 📈 Series Temporales
![Series](https://aemet-dashboard-pro-3s9ay3cnvowfgvrutqvh4w.streamlit.app/)

### 🌡️ Índices & Anomalías
![Índices](https://aemet-dashboard-pro-3s9ay3cnvowfgvrutqvh4w.streamlit.app/)

### 📊 Análisis Avanzado
![Análisis](https://aemet-dashboard-pro-3s9ay3cnvowfgvrutqvh4w.streamlit.app/)

### 📥 Exportación
![Exportar](https://aemet-dashboard-pro-3s9ay3cnvowfgvrutqvh4w.streamlit.app/)

---

## 🧭 Arquitectura & Estructura
