
# 🌤️ AEMET Weather Analytics v3.1

Dashboard interactivo con **Streamlit** para análisis climático usando la **API AEMET OpenData**. Incluye ETL robusta, cache inteligente y visualizaciones avanzadas.

---

## ✅ Estado
**Versión:** 3.1 (Producción)  
**Última actualización:** Diciembre 2025  
**Autor:** Mostapha Jaaidi

---

## ✨ Características
- Datos en tiempo real (API AEMET) + fallback CSV
- 5 pestañas: Series, Índices, Análisis, Estadísticas, Exportar
- Visualizaciones interactivas (Plotly)
- Detección de anomalías (STL + z-score)
- Exportación CSV/JSON

---

## 🚀 Ejecución
```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar dashboard
streamlit run app/streamlit_app.py
``
