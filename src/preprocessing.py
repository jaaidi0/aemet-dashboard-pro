# src/preprocessing.py
"""
Cálculo de índices agronómicos, anomalías y estadísticas
VERSIÓN OPTIMIZADA: manejo robusto de datos faltantes y errores
"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


# ================================================================
# 🧮 ENRICH INDICES (cálculos seguros y a prueba de errores)
# ================================================================
def enrich_indices(df: pd.DataFrame) -> pd.DataFrame:

    if df.empty:
        logger.warning("⚠️ DataFrame vacío recibido en enrich_indices")
        return df

    df = df.copy()

    # ============================================================
    # NORMALIZAR COLUMNAS AEMET
    # ============================================================

    if "ta" in df.columns:
        df["temp_media"] = pd.to_numeric(df["ta"], errors="coerce")

    if "prec" in df.columns:
        df["lluvia"] = pd.to_numeric(df["prec"], errors="coerce")

    if "hr" in df.columns:
        df["humedad"] = pd.to_numeric(df["hr"], errors="coerce")
        df["humedad_media"] = pd.to_numeric(df["hr"], errors="coerce")

    if "temp_max" not in df.columns and "temp_media" in df.columns:
        df["temp_max"] = df["temp_media"]

    if "temp_min" not in df.columns and "temp_media" in df.columns:
        df["temp_min"] = df["temp_media"]

    # -----------------------------------------------------------
    # 1. NORMALIZAR COLUMNAS NUMÉRICAS
    # -----------------------------------------------------------
    cols_expected = {
        "temp_media": float,
        "temp_max": float,
        "temp_min": float,
        "humedad": float,
        "lluvia": float
    }

    for col, dtype in cols_expected.items():
        if col not in df.columns:
            df[col] = np.nan
            logger.debug(f"Columna {col} no existe, se crea con NaN")
        
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # -----------------------------------------------------------
    # 2. HUMEDAD MEDIA (si no existe)
    # -----------------------------------------------------------
    if "humedad_media" not in df.columns:
        df["humedad_media"] = df["humedad"]
    else:
        df["humedad_media"] = pd.to_numeric(df["humedad_media"], errors="coerce")

    # -----------------------------------------------------------
    # 3. THI – Temperature-Humidity Index
    # -----------------------------------------------------------
    try:
        df["thi"] = df["temp_media"] - (
            0.55 - 0.0055 * df["humedad_media"]
        ) * (df["temp_media"] - 14.5)
        
        # Limitar valores extremos
        df["thi"] = df["thi"].clip(lower=-50, upper=100)
        
    except Exception as e:
        logger.warning(f"⚠️ Error calculando THI: {e}")
        df["thi"] = np.nan

    # -----------------------------------------------------------
    # 4. HUMIDEX (índice de confort térmico)
    # -----------------------------------------------------------
    try:
        # Punto de rocío aproximado
        dew_point = df["temp_media"] - ((100 - df["humedad_media"]) / 5)
        
        # Presión de vapor
        e = 6.11 * np.exp(5417.7530 * ((1/273.16) - (1/(dew_point + 273.16))))
        
        # Humidex
        df["humidex"] = df["temp_media"] + 0.5555 * (e - 10)
        
        # Limitar valores extremos
        df["humidex"] = df["humidex"].clip(lower=-50, upper=100)
        
    except Exception as e:
        logger.warning(f"⚠️ Error calculando Humidex: {e}")
        df["humidex"] = np.nan

    # -----------------------------------------------------------
    # 5. ACUMULADOS MÓVILES
    # -----------------------------------------------------------
    try:
        # Lluvia acumulada 7 días
        df["lluvia_acum7"] = df["lluvia"].rolling(
            window=7, 
            min_periods=1
        ).sum()
        
        # Temperatura media móvil 7 días (para tendencias)
        df["temp_media_mov7"] = df["temp_media"].rolling(
            window=7,
            min_periods=1
        ).mean()
        
    except Exception as e:
        logger.warning(f"⚠️ Error calculando acumulados: {e}")
        df["lluvia_acum7"] = df["lluvia"]
        df["temp_media_mov7"] = df["temp_media"]

    # -----------------------------------------------------------
    # 6. DETECCIÓN DE ANOMALÍAS (Z-score robusto)
    # -----------------------------------------------------------
    try:
        # Calcular media y desviación estándar robustas
        temp_mean = df["temp_media"].mean()
        temp_std = df["temp_media"].std(ddof=0)
        
        # Evitar división por cero
        if temp_std == 0 or pd.isna(temp_std):
            df["zscore"] = 0
            df["anomaly"] = False
            logger.warning("⚠️ Desviación estándar cero, no se detectan anomalías")
        else:
            # Z-score
            df["zscore"] = (df["temp_media"] - temp_mean) / temp_std
            
            # Anomalía si |zscore| > 2.5 (intervalo de confianza ~98.8%)
            df["anomaly"] = df["zscore"].abs() > 2.5
            
            num_anomalias = df["anomaly"].sum()
            if num_anomalias > 0:
                logger.info(f"🔍 {num_anomalias} anomalías detectadas")
                
    except Exception as e:
        logger.warning(f"⚠️ Error detectando anomalías: {e}")
        df["zscore"] = 0
        df["anomaly"] = False

    # -----------------------------------------------------------
    # 7. ÍNDICE DE ESTRÉS TÉRMICO (para agricultura)
    # -----------------------------------------------------------
    try:
        # Índice simple: diferencia entre máxima y mínima
        df["amplitud_termica"] = df["temp_max"] - df["temp_min"]
        
        # Días de estrés por calor (>30°C)
        df["estres_calor"] = df["temp_max"] > 30
        
        # Días de helada (<0°C)
        df["riesgo_helada"] = df["temp_min"] < 0
        
    except Exception as e:
        logger.warning(f"⚠️ Error calculando índices de estrés: {e}")

    # -----------------------------------------------------------
    # 8. LIMPIEZA FINAL
    # -----------------------------------------------------------
    # Reemplazar infinitos con NaN
    df = df.replace([np.inf, -np.inf], np.nan)
    
    logger.info(f"✅ Enriquecimiento completado: {len(df)} registros procesados")
    
    return df


# ================================================================
# 📊 ESTADÍSTICAS SEGURAS Y COMPLETAS
# ================================================================
def calcular_estadisticas(df: pd.DataFrame) -> dict:
    """
    Calcula estadísticas descriptivas robustas del dataset.
    Maneja valores faltantes y casos extremos.
    """
    if df.empty:
        logger.warning("⚠️ DataFrame vacío para calcular estadísticas")
        return {
            "temp_media": 0,
            "temp_max": 0,
            "temp_min": 0,
            "humedad_media": 0,
            "lluvia_total": 0,
            "dias_lluvia": 0,
            "tendencia": 0,
            "anomalias": 0,
        }

    stats = {}

    try:
        # -----------------------------------------------------------
        # TEMPERATURA
        # -----------------------------------------------------------
        stats["temp_media"] = df["temp_media"].mean() if df["temp_media"].notna().any() else 0
        stats["temp_max"] = df["temp_max"].max() if df["temp_max"].notna().any() else 0
        stats["temp_min"] = df["temp_min"].min() if df["temp_min"].notna().any() else 0
        stats["temp_std"] = df["temp_media"].std() if df["temp_media"].notna().any() else 0

        # -----------------------------------------------------------
        # HUMEDAD
        # -----------------------------------------------------------
        if "humedad_media" in df.columns:
            stats["humedad_media"] = df["humedad_media"].mean() if df["humedad_media"].notna().any() else 0
        elif "humedad" in df.columns:
            stats["humedad_media"] = df["humedad"].mean() if df["humedad"].notna().any() else 0
        else:
            stats["humedad_media"] = 0

        # -----------------------------------------------------------
        # PRECIPITACIÓN
        # -----------------------------------------------------------
        stats["lluvia_total"] = df["lluvia"].sum() if df["lluvia"].notna().any() else 0
        stats["dias_lluvia"] = int((df["lluvia"] > 0).sum()) if df["lluvia"].notna().any() else 0
        stats["lluvia_max_dia"] = df["lluvia"].max() if df["lluvia"].notna().any() else 0

        # -----------------------------------------------------------
        # TENDENCIA (diferencia promedio día a día)
        # -----------------------------------------------------------
        try:
            tendencia = df["temp_media"].diff().mean()
            stats["tendencia"] = tendencia if pd.notna(tendencia) else 0
        except:
            stats["tendencia"] = 0

        # -----------------------------------------------------------
        # ANOMALÍAS
        # -----------------------------------------------------------
        stats["anomalias"] = int(df["anomaly"].sum()) if "anomaly" in df.columns else 0

        # -----------------------------------------------------------
        # ÍNDICES TÉRMICOS
        # -----------------------------------------------------------
        if "thi" in df.columns:
            stats["thi_media"] = df["thi"].mean() if df["thi"].notna().any() else 0
            
        if "humidex" in df.columns:
            stats["humidex_media"] = df["humidex"].mean() if df["humidex"].notna().any() else 0

        # -----------------------------------------------------------
        # ESTRÉS TÉRMICO
        # -----------------------------------------------------------
        if "estres_calor" in df.columns:
            stats["dias_estres_calor"] = int(df["estres_calor"].sum())
            
        if "riesgo_helada" in df.columns:
            stats["dias_helada"] = int(df["riesgo_helada"].sum())

        # -----------------------------------------------------------
        # AMPLITUD TÉRMICA
        # -----------------------------------------------------------
        if "amplitud_termica" in df.columns:
            stats["amplitud_termica_media"] = df["amplitud_termica"].mean() if df["amplitud_termica"].notna().any() else 0

        logger.info(f"✅ Estadísticas calculadas: {len(stats)} métricas")

    except Exception as e:
        logger.error(f"❌ Error calculando estadísticas: {e}")
        # Retornar valores por defecto en caso de error
        return {
            "temp_media": 0,
            "temp_max": 0,
            "temp_min": 0,
            "humedad_media": 0,
            "lluvia_total": 0,
            "dias_lluvia": 0,
            "tendencia": 0,
            "anomalias": 0,
        }

    return stats


# ================================================================
# 🔍 ANÁLISIS ADICIONAL: DETECCIÓN DE PATRONES
# ================================================================
def detectar_patrones(df: pd.DataFrame) -> dict:
    """
    Detecta patrones climáticos relevantes para agricultura.
    """
    if df.empty:
        return {}
    
    patrones = {}
    
    try:
        # Rachas de días sin lluvia
        df["sin_lluvia"] = df["lluvia"] <= 0
        rachas = df["sin_lluvia"].astype(int).groupby(df["sin_lluvia"].ne(df["sin_lluvia"].shift()).cumsum()).sum()
        patrones["racha_sequia_max"] = int(rachas.max()) if not rachas.empty else 0
        
        # Días consecutivos con temperatura alta
        df["temp_alta"] = df["temp_max"] > 30
        rachas_calor = df["temp_alta"].astype(int).groupby(df["temp_alta"].ne(df["temp_alta"].shift()).cumsum()).sum()
        patrones["racha_calor_max"] = int(rachas_calor.max()) if not rachas_calor.empty else 0
        
    except Exception as e:
        logger.warning(f"⚠️ Error detectando patrones: {e}")
    
    return patrones
