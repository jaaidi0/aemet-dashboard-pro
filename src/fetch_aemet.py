
#!/usr/bin/env python3
import os, sys, json
from pathlib import Path
import pandas as pd, requests
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())  # carga .env automáticamente

BASE = Path(__file__).resolve().parents[1]
RAW  = BASE/"data_raw"; RAW.mkdir(exist_ok=True)
CLEAN= BASE/"data_clean"; CLEAN.mkdir(exist_ok=True)

API_KEY = os.getenv("AEMET_API_KEY")
if not API_KEY:
    print("❌ Falta AEMET_API_KEY. Carga .env"); sys.exit(1)

# META (HATEOAS)
meta_url = "https://opendata.aemet.es/opendata/api/observacion/convencional/todas"
r = requests.get(meta_url, params={"api_key": API_KEY}, timeout=60)
r.raise_for_status()
RAW.joinpath("aemet_meta.json").write_text(r.text, encoding="utf-8")

meta = r.json()
datos_url = meta.get("datos")
if not datos_url:
    print("❌ 'datos' vacío en META:", meta); sys.exit(1)

dr = requests.get(datos_url, timeout=120)
dr.raise_for_status()
RAW.joinpath("aemet_obs.json").write_text(dr.text, encoding="utf-8")

# Limpieza + filtro local (Haversine rápido)
obs = json.loads(dr.text)
df = pd.DataFrame(obs)
keep = [c for c in ["idema","lat","lon","alt","fint","ta","prec","vv","hr"] if c in df.columns]
if not keep:
    print("⚠️ Sin columnas esperadas"); sys.exit(0)
df = df[keep].copy()
df["fint"] = pd.to_datetime(df["fint"], errors="coerce")

import math
LAT0 = float(os.getenv("LAT0", "37.280"))
LON0 = float(os.getenv("LON0", "-5.930"))
RADIO_KM = float(os.getenv("RADIO_KM", "25"))

def hav(lat1, lon1, lat2, lon2):
    R=6371.0
    dlat=math.radians(lat2-lat1); dlon=math.radians(lon2-lon1)
    a=math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return 2*R*math.asin(math.sqrt(a))

df["dist_km"] = df.apply(lambda r: hav(LAT0,LON0, r["lat"], r["lon"]), axis=1)
local = df[df["dist_km"]<=RADIO_KM].copy()
if local.empty:
    print("⚠️ No hay observaciones dentro del radio seleccionado."); sys.exit(0)

daily = (local
         .groupby([local["fint"].dt.date, "idema"])
         .agg({"ta":"mean","prec":"sum","vv":"mean","hr":"mean"})
         .reset_index()
         .rename(columns={"fint":"fecha"}))

out_csv = CLEAN/"aemet_obs_local_daily.csv"
daily.to_csv(out_csv, index=False)
print(f"✅ OK -> {out_csv}")
print(f"   Estaciones locales: {local['idema'].nunique()} | días: {daily['fecha'].nunique()}")
