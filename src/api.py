# src/api.py
"""
Módulo API para descargar y cargar datos de AEMET con fallback a CSV local
VERSIÓN PARALELA: Descarga concurrente con ThreadPoolExecutor
"""

import requests
import pandas as pd
import logging
import time
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple, List
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

API_KEY = None
API_URL = "https://opendata.aemet.es/opendata/api/observacion/convencional/datos/estacion/"
ESTACIONES = {"5788X", "5783", "5790Y"}

DATA_CLEAN = Path(__file__).resolve().parents[1] / "data_clean"
DATA_CLEAN.mkdir(exist_ok=True)


# -------------------------------------------------------------------
# RATE LIMITER CON TOKEN BUCKET (Thread-safe)
# -------------------------------------------------------------------
@dataclass
class RateLimiter:
    """Token bucket thread-safe para controlar tasa de peticiones"""
    capacity: int = 10
    refill_rate: float = 2.0
    tokens: float = field(default=10.0)
    last_update: float = field(default_factory=time.time)
    
    def acquire(self, tokens: int = 1) -> bool:
        """Intenta consumir tokens. Retorna True si hay disponibles."""
        now = time.time()
        elapsed = now - self.last_update
        
        # Rellenar tokens según tiempo transcurrido
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_update = now
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def wait_time(self, tokens: int = 1) -> float:
        """Calcula tiempo de espera necesario para obtener tokens"""
        if self.tokens >= tokens:
            return 0.0
        deficit = tokens - self.tokens
        return deficit / self.refill_rate


rate_limiter = RateLimiter(capacity=10, refill_rate=1.5)


# -------------------------------------------------------------------
# CACHÉ DE ESTACIONES
# -------------------------------------------------------------------
class EstacionCache:
    """Caché temporal para datos de estaciones"""
    def __init__(self, ttl_minutes: int = 30):
        self.cache = {}
        self.ttl = timedelta(minutes=ttl_minutes)
    
    def get(self, estacion: str) -> Optional[pd.DataFrame]:
        """Obtiene datos del caché si son recientes"""
        if estacion in self.cache:
            df, timestamp = self.cache[estacion]
            if datetime.now() - timestamp < self.ttl:
                logger.info(f"✅ Caché HIT para estación {estacion}")
                return df
            else:
                logger.info(f"⏰ Caché EXPIRED para estación {estacion}")
                del self.cache[estacion]
        return None
    
    def set(self, estacion: str, df: pd.DataFrame):
        """Guarda datos en caché"""
        self.cache[estacion] = (df, datetime.now())
    
    def clear(self):
        """Limpia todo el caché"""
        self.cache.clear()


estacion_cache = EstacionCache(ttl_minutes=30)


# -------------------------------------------------------------------
# DESCARGA INDIVIDUAL CON TIMEOUT REDUCIDO
# -------------------------------------------------------------------
def descargar_observacion_convencional(
    estacion: str, 
    max_intentos: int = 2,  # Reducido de 3 a 2 para ser más ágil
    usar_cache: bool = True
) -> Optional[pd.DataFrame]:
    """
    Descarga datos de una estación usando la API de AEMET.
    Versión optimizada con timeouts más agresivos.
    """
    global API_KEY

    # 1. Intentar caché primero
    if usar_cache:
        cached = estacion_cache.get(estacion)
        if cached is not None:
            return cached

    # 2. Cargar API key
    if API_KEY is None:
        from dotenv import load_dotenv
        import os
        load_dotenv()
        API_KEY = os.getenv("AEMET_API_KEY")

        if not API_KEY:
            logger.error("❌ No se definió AEMET_API_KEY en .env")
            return None

    url = f"{API_URL}{estacion}/"
    headers = {"api_key": API_KEY}
    
    # Timeouts más agresivos: 15s, 25s (en vez de 20s, 30s, 45s)
    base_timeouts = [15, 25]

    for intento in range(max_intentos):
        # 3. Rate limiting
        while not rate_limiter.acquire(tokens=1):
            wait = rate_limiter.wait_time(tokens=1)
            logger.info(f"⏳ Rate limit: esperando {wait:.1f}s")
            time.sleep(wait + 0.1)
        
        timeout = base_timeouts[min(intento, len(base_timeouts) - 1)]
        
        try:
            logger.info(f"📡 [{intento + 1}/{max_intentos}] Estación {estacion} (timeout: {timeout}s)")
            
            # Primera petición: obtener metadatos
            r = requests.get(url, headers=headers, timeout=timeout)
            
            # Manejo de rate limiting
            if r.status_code == 429:
                base_wait = 2 ** intento * 3  # Reducido de 5 a 3
                jitter = random.uniform(0, 2)
                wait_time = base_wait + jitter
                
                logger.warning(f"⚠️ AEMET 429 (rate limit) - esperando {wait_time:.1f}s")
                time.sleep(wait_time)
                continue
            
            if r.status_code != 200:
                logger.warning(f"⚠️ HTTP {r.status_code} para estación {estacion}")
                if intento == max_intentos - 1:
                    return None
                time.sleep(1)
                continue
                
            r.raise_for_status()
            meta = r.json()
            datos_url = meta.get("datos")
            
            if not datos_url:
                logger.error("❌ API no devolvió URL de datos")
                return None

            time.sleep(0.3)  # Reducido de 0.5 a 0.3

            # Segunda petición: obtener datos reales
            datos_resp = requests.get(datos_url, timeout=timeout)
            datos_resp.raise_for_status()
            data = datos_resp.json()

            if not data:
                logger.warning(f"⚠️ No hay datos para estación {estacion}")
                return None

            df = pd.DataFrame(data)
            logger.info(f"✅ Datos obtenidos para {estacion}: {len(df)} registros")
            
            # Guardar en caché
            estacion_cache.set(estacion, df)
            
            return df

        except requests.Timeout:
            logger.warning(f"⏱️ Timeout en intento {intento + 1}/{max_intentos} para {estacion}")
            if intento < max_intentos - 1:
                time.sleep(1)  # Reducido de 2s a 1s
            else:
                logger.error(f"❌ Timeout final para {estacion} - continuando con otras estaciones")
                return None
                
        except requests.RequestException as e:
            logger.error(f"❌ Error de red en intento {intento + 1}: {e}")
            if intento < max_intentos - 1:
                time.sleep(1)
            else:
                return None
            
        except Exception as e:
            logger.error(f"❌ Error inesperado: {e}")
            return None

    return None


# -------------------------------------------------------------------
# DESCARGA PARALELA CON ThreadPoolExecutor
# -------------------------------------------------------------------
def descargar_todas_estaciones_paralelo(usar_cache: bool = True) -> Tuple[List[pd.DataFrame], List[str]]:
    """
    Descarga datos de todas las estaciones EN PARALELO.
    
    Ventajas:
    - Las estaciones rápidas no esperan a las lentas
    - Tiempo total = max(tiempo_estacion) en vez de sum(tiempos)
    - Si una estación falla, las demás continúan
    
    Returns:
        Tuple con (lista de DataFrames exitosos, lista de logs)
    """
    frames = []
    logs = []
    
    logs.append("🌊 Iniciando carga PARALELA desde API AEMET...")
    
    # Función wrapper para cada estación
    def descargar_wrapper(estacion: str) -> Tuple[str, Optional[pd.DataFrame]]:
        df = descargar_observacion_convencional(estacion, max_intentos=2, usar_cache=usar_cache)
        return estacion, df
    # EN src/api.py - Dentro de descargar_todas_estaciones_paralelo
# ...
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {}
        for est in ESTACIONES:
            # Añadimos un pequeño retraso aleatorio para no golpear la puerta a la vez
            time.sleep(0.5)  # <--- AÑADE ESTA LÍNEA
            future = executor.submit(descargar_wrapper, est)
            futures[future] = est
# ...
    # Ejecutar en paralelo con máximo 3 workers (una por estación)
    with ThreadPoolExecutor(max_workers=3) as executor:
        # Enviar todas las tareas
        futures = {
            executor.submit(descargar_wrapper, est): est 
            for est in ESTACIONES
        }
        
        # Procesar resultados conforme van llegando
        for future in as_completed(futures):
            estacion = futures[future]
            try:
                est_name, df = future.result()
                
                if df is not None and not df.empty:
                    df["estacion"] = est_name
                    frames.append(df)
                    logs.append(f"✅ API OK: estación {est_name} ({len(df)} registros)")
                else:
                    logs.append(f"⚠️ API FAILED: estación {est_name}")
                    
            except Exception as e:
                logs.append(f"❌ Error procesando estación {estacion}: {e}")
    
    return frames, logs


# -------------------------------------------------------------------
# DESCARGA SECUENCIAL (FALLBACK)
# -------------------------------------------------------------------
def descargar_todas_estaciones_secuencial(usar_cache: bool = True) -> Tuple[List[pd.DataFrame], List[str]]:
    """
    Descarga datos de todas las estaciones SECUENCIALMENTE.
    Usada como fallback si hay problemas con la versión paralela.
    """
    frames = []
    logs = []
    
    logs.append("🌊 Iniciando carga SECUENCIAL desde API AEMET...")
    
    for i, estacion in enumerate(ESTACIONES):
        if i > 0:
            wait = rate_limiter.wait_time(tokens=1)
            if wait > 0:
                time.sleep(wait + 0.5)
            else:
                time.sleep(1)
        
        df = descargar_observacion_convencional(estacion, max_intentos=2, usar_cache=usar_cache)
        
        if df is not None and not df.empty:
            df["estacion"] = estacion
            frames.append(df)
            logs.append(f"✅ API OK: estación {estacion} ({len(df)} registros)")
        else:
            logs.append(f"⚠️ API FAILED: estación {estacion}")
    
    return frames, logs


# -------------------------------------------------------------------
# LIMPIEZA AUTOMÁTICA DE CSVs
# -------------------------------------------------------------------
def limpiar_csvs_antiguos(max_archivos: int = 5):
    """Mantiene solo los N archivos CSV más recientes"""
    try:
        csv_files = [
            f for f in DATA_CLEAN.glob("*.csv") 
            if f.name != "aemet_obs_local_daily.csv"
        ]
        csv_files = sorted(csv_files, key=lambda x: x.stat().st_mtime)
        
        if len(csv_files) > max_archivos:
            archivos_a_eliminar = csv_files[:-max_archivos]
            for old_file in archivos_a_eliminar:
                try:
                    old_file.unlink()
                    logger.info(f"🗑️ CSV antiguo eliminado: {old_file.name}")
                except Exception as e:
                    logger.warning(f"⚠️ No se pudo eliminar {old_file.name}: {e}")
                    
    except Exception as e:
        logger.warning(f"⚠️ Error en limpieza de CSVs: {e}")


# -------------------------------------------------------------------
# GUARDAR CSV LOCAL
# -------------------------------------------------------------------
def guardar_csv_local(df: pd.DataFrame):
    """Guarda DataFrame en data_clean/ con timestamp"""
    try:
        nombre = datetime.now().strftime("%Y-%m-%d_%H-%M") + ".csv"
        ruta = DATA_CLEAN / nombre
        df.to_csv(ruta, index=False)
        logger.info(f"💾 CSV guardado: {ruta.name}")
        
        limpiar_csvs_antiguos(max_archivos=5)
        
    except Exception as e:
        logger.error(f"❌ Error guardando CSV: {e}")


# -------------------------------------------------------------------
# CARGAR DATOS CON FALLBACK CSV
# -------------------------------------------------------------------
def cargar_datos(forzar_api: bool = False, usar_paralelo: bool = False) -> Tuple[Optional[pd.DataFrame], str, List[str]]:
    """
    Carga datos desde API AEMET con fallback a CSV local.
    
    Args:
        forzar_api: Si True, limpia caché y fuerza llamada a API
        usar_paralelo: Si True, usa descarga paralela (más rápido)
    
    Returns:
        Tuple de (DataFrame, fuente, logs)
    """
    logs = []
    
    if forzar_api:
        estacion_cache.clear()
        logs.append("🔄 Caché limpiado - forzando consulta API")

    # 1. INTENTAR API (paralelo o secuencial)
    try:
        if usar_paralelo:
            frames, api_logs = descargar_todas_estaciones_paralelo(usar_cache=not forzar_api)
        else:
            frames, api_logs = descargar_todas_estaciones_secuencial(usar_cache=not forzar_api)
        
        logs.extend(api_logs)
    except Exception as e:
        logger.error(f"❌ Error en descarga: {e}")
        frames = []
        logs.append(f"❌ Error en descarga: {e}")

    if frames:
        df_api = pd.concat(frames, ignore_index=True)
        df_api = normalizar_dataframe(df_api)
        guardar_csv_local(df_api)
        logs.append(f"✅ Total: {len(df_api)} registros desde API → guardado CSV local")
        return df_api, "API", logs

    logs.append("⚠️ API no disponible → buscando CSV local...")

    # 2. FALLBACK A CSV LOCAL
    csv_files = sorted(
        DATA_CLEAN.glob("*.csv"), 
        key=lambda x: x.stat().st_mtime, 
        reverse=True
    )
    
    if not csv_files:
        logs.append("❌ No hay CSV disponible en data_clean/")
        return None, "SIN_DATOS", logs

    for csv_file in csv_files:
        try:
            df_local = pd.read_csv(csv_file, parse_dates=["fecha"])
            
            if df_local.empty:
                logs.append(f"⚠️ CSV vacío: {csv_file.name}")
                continue
                
            logs.append(f"✅ CSV cargado: {csv_file.name} ({len(df_local)} registros)")
            return df_local, "CSV LOCAL", logs
            
        except Exception as e:
            logs.append(f"⚠️ Error leyendo {csv_file.name}: {e}")
            continue

    logs.append("❌ No se pudo cargar ningún CSV")
    return None, "SIN_DATOS", logs


# -------------------------------------------------------------------
# NORMALIZACIÓN
# -------------------------------------------------------------------
def normalizar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza columnas y tipos de datos"""
    df = df.copy()

    if "fint" in df.columns:
        df["fecha"] = pd.to_datetime(df["fint"], errors="coerce")
    elif "fecha" not in df.columns:
        logger.warning("⚠️ No se encontró columna de fecha")

    if "ta" in df.columns:
        df["temp_media"] = pd.to_numeric(df["ta"], errors="coerce")
    if "tamax" in df.columns:
        df["temp_max"] = pd.to_numeric(df["tamax"], errors="coerce")
    if "tamin" in df.columns:
        df["temp_min"] = pd.to_numeric(df["tamin"], errors="coerce")

    if "hr" in df.columns:
        df["humedad"] = pd.to_numeric(df["hr"], errors="coerce")

    if "prec" in df.columns:
        df["lluvia"] = pd.to_numeric(df["prec"], errors="coerce")

    keep = ["fecha", "temp_media", "temp_max", "temp_min", "humedad", "lluvia", "estacion"]
    
    for col in keep:
        if col not in df.columns:
            df[col] = None

    df_final = df[keep].sort_values("fecha").reset_index(drop=True)
    df_final = df_final[df_final["fecha"].notna()]
    
    return df_final


# -------------------------------------------------------------------
# TEST
# -------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "="*70)
    print("🧪 PROBANDO SISTEMA DE CARGA PARALELA")
    print("="*70 + "\n")
    
    print("🚀 Prueba 1: Descarga PARALELA")
    inicio = time.time()
    df, fuente, logs = cargar_datos(usar_paralelo=True)
    tiempo_paralelo = time.time() - inicio
    
    print("\n" + "="*70)
    print(f"📊 FUENTE: {fuente} | TIEMPO: {tiempo_paralelo:.2f}s")
    print("="*70)
    
    if df is not None:
        print(f"\n✅ Resumen:")
        print(f"  - Registros: {len(df)}")
        print(f"  - Rango fechas: {df['fecha'].min()} a {df['fecha'].max()}")
        print(f"  - Estaciones: {df['estacion'].nunique()}")
    
    print("\n" + "="*70)
    print("📄 LOGS:")
    print("="*70)
    for log in logs:
        print(f"  {log}")