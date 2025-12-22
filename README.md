
# 🌤️ AEMET Weather Analytics — v3.1

Dashboard geoespacial (Streamlit) con **ETL robusta**, **caché inteligente** y visualizaciones **Plotly** sobre la **API AEMET OpenData**. Monitorea temperatura, humedad, precipitación e **índices térmicos** (THI, Humidex, Dew Point), con **detección de anomalías** y exportación de datos.

[![Estado](https://img.shields.io/badge/Estado-FUNCIONAL-00c853)](#)
[![Versión](https://img.shields.io/badge/Versi%C3%B3n-3.1-blue)](#)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](#)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28.1-FF4B4B?logo=streamlit&logoColor=white)](#)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🔗 Live Demo

> **URL en vivo (Streamlit Cloud):**  
> **https://aemet-dashboard-pro-3s9ay3cnvowfgvrutqvh4w.streamlit.app/**

Badge de Streamlit:  
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://aemet-dashboard-pro-3s9ay3cnvowfgvrutqvh4w.streamlit.app/)

---

## ✨ Características

- **Datos en (casi) tiempo real** desde **AEMET OpenData** (36+ registros/día).
- **Fallback CSV** cuando la API falla o hay timeout.
- **Caché inteligente** (5–30 min por endpoint).
- **3 estaciones** por defecto: Sevilla (**5783**), Córdoba (**5788X**), Jaén (**5790Y**).
- **5 pestañas**:
  1. Series Temporales (temp/precipitación, medias móviles).
  2. Índices & Anomalías (THI, Humidex, Dew Point, z‑score ≥ 2.5).
  3. Análisis Avanzado (histogramas, correlaciones, semanal).
  4. Estadísticas (descriptivas + tabla de anomalías).
  5. Exportar (CSV/JSON + vista previa).
- **Visualizaciones**: 10+ gráficos interactivos (Plotly), tema `plotly_white`.
- **Mapa estático** con **Folium** (sin “baile”).
- **Exportación**: CSV/JSON, filtros (7/14/30/90 días, completo o rango personalizado).

---

## 🧭 Arquitectura & Estructura
*(Aquí puedes añadir el bloque de arquitectura y estructura que ya tienes en tu README original)*

---

✅ Ahora tu README está listo para mostrar el **link real** y el **badge oficial**.  
¿Quieres que también te prepare atractivo en GitHub?

