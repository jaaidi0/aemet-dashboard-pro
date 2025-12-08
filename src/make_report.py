
#!/usr/bin/env python3
from pathlib import Path
from datetime import date
import pandas as pd, matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parents[1]
IN   = BASE/"data_clean"/"aemet_obs_local_daily.csv"
OUT  = BASE/"reports"; OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(IN, parse_dates=["fecha"])
df["fecha"] = pd.to_datetime(df["fecha"]).dt.floor("D")

agg = {"temp_media":("ta","mean"), "temp_min":("ta","min"), "temp_max":("ta","max"),
       "lluvia_total":("prec","sum"), "viento_medio":("vv","mean")}
if "hr" in df.columns: agg["humedad_media"]=("hr","mean")

resumen = df.groupby("fecha").agg(**agg).round(2)
resumen = resumen.join(df.groupby("fecha")["idema"].nunique().rename("estaciones_con_dato"))
resumen = resumen.join(df.groupby("fecha").size().rename("registros"))
resumen = resumen.sort_index()
resumen["temp_media_mov7"] = resumen["temp_media"].rolling(7, min_periods=1).mean().round(2)
resumen["lluvia_acum7"]    = resumen["lluvia_total"].rolling(7, min_periods=1).sum().round(2)

resumen.to_csv(OUT/"resumen_diario.csv", index=True)
resumen.to_excel(OUT/"resumen_diario.xlsx", sheet_name="resumen")

plt.style.use("seaborn-v0_8")
fig, ax = plt.subplots(3,1, figsize=(12,9), sharex=True)
resumen["temp_media"].plot(ax=ax[0], color="tab:red", label="Temp media")
resumen["temp_media_mov7"].plot(ax=ax[0], color="tab:orange", label="Media 7d", alpha=0.8)
ax[0].set_ylabel("°C"); ax[0].set_title("Temperatura media diaria"); ax[0].legend()

resumen["lluvia_total"].plot(ax=ax[1], color="tab:blue", label="Lluvia diaria")
resumen["lluvia_acum7"].plot(ax=ax[1], color="navy", label="Lluvia acum 7d", alpha=0.8)
ax[1].set_ylabel("mm"); ax[1].set_title("Precipitación"); ax[1].legend()

resumen["viento_medio"].plot(ax=ax[2], color="tab:green", label="Viento medio")
ax[2].set_ylabel("m/s"); ax[2].set_title("Viento medio"); ax[2].legend()
fig.tight_layout()

out_png = OUT/f"fig_resumen_{date.today().isoformat()}.png"
fig.savefig(out_png, dpi=160)
print("✅ Reporte ->", OUT/"resumen_diario.[csv|xlsx]", "| Figura ->", out_png)
