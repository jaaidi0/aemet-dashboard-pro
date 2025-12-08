# src/utils.py

import io
import pandas as pd
import plotly.io as pio


# ===========================================================
# EXPORTAR A CSV
# ===========================================================
def df_to_csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8")


# ===========================================================
# EXPORTAR A EXCEL  (FIX: eliminar timezone)
# ===========================================================
def df_to_excel_bytes(df):

    df = df.copy()

    # 🔥 FIX EXCEL TZ: eliminar timezone
    if "fecha" in df.columns:
        try:
            df["fecha"] = df["fecha"].dt.tz_localize(None)
        except:
            pass

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)
    return buffer.getvalue()


# ===========================================================
# EXPORTAR FIGURA A PNG
# ===========================================================
def fig_to_png_bytes(fig):
    try:
        png = fig.to_image(format="png")
        return png, True
    except Exception:
        return None, False


# ===========================================================
# HTML SNAPSHOT
# ===========================================================
def crear_snapshot_html(figs: dict, title="Snapshot"):
    html_parts = [f"<h1>{title}</h1>"]
    for name, fig in figs.items():
        try:
            html_parts.append(f"<h2>{name}</h2>")
            html_parts.append(fig.to_html(include_plotlyjs='cdn'))
        except Exception:
            pass

    html = "<html><body>" + "\n".join(html_parts) + "</body></html>"
    return html.encode("utf-8")
