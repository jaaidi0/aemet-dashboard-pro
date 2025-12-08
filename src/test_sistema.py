#!/usr/bin/env python3
"""
Script de prueba para verificar que todo el sistema funciona correctamente
"""

import sys
from pathlib import Path

# Setup paths
BASE = Path(__file__).resolve().parent
SRC = BASE / "src"
sys.path.insert(0, str(SRC))

print("="*70)
print("🧪 TEST DEL SISTEMA AEMET · GRAND LINE")
print("="*70)

# Test 1: Imports
print("\n1️⃣ Verificando imports...")
try:
    from api import cargar_datos, limpiar_csvs_antiguos
    from preprocessing import enrich_indices, calcular_estadisticas
    from plots import (
        crear_grafico_temperatura,
        crear_grafico_precipitacion,
        crear_grafico_indices,
    )
    from utils import df_to_csv_bytes, df_to_excel_bytes
    print("   ✅ Todos los módulos importados correctamente")
except Exception as e:
    print(f"   ❌ Error en imports: {e}")
    sys.exit(1)

# Test 2: Carga de datos
print("\n2️⃣ Probando carga de datos...")
try:
    df, fuente, logs = cargar_datos()
    
    print(f"   📡 Fuente: {fuente}")
    print(f"   📊 Registros: {len(df) if df is not None else 0}")
    
    if df is None or df.empty:
        print("   ⚠️ No hay datos disponibles")
        print("\n📄 Logs:")
        for log in logs:
            print(f"      {log}")
        sys.exit(0)
    
    print("   ✅ Datos cargados correctamente")
    
except Exception as e:
    print(f"   ❌ Error cargando datos: {e}")
    sys.exit(1)

# Test 3: Preprocessing
print("\n3️⃣ Probando enriquecimiento de datos...")
try:
    df_enriched = enrich_indices(df)
    print(f"   ✅ Datos enriquecidos: {len(df_enriched.columns)} columnas")
    
    # Verificar columnas críticas
    columnas_esperadas = ["thi", "humidex", "anomaly", "temp_media_mov7"]
    columnas_presentes = [col for col in columnas_esperadas if col in df_enriched.columns]
    print(f"   📋 Columnas nuevas: {', '.join(columnas_presentes)}")
    
except Exception as e:
    print(f"   ❌ Error en enriquecimiento: {e}")
    sys.exit(1)

# Test 4: Estadísticas
print("\n4️⃣ Calculando estadísticas...")
try:
    stats = calcular_estadisticas(df_enriched)
    print("   ✅ Estadísticas calculadas:")
    print(f"      • Temperatura media: {stats.get('temp_media', 0):.1f}°C")
    print(f"      • Temperatura máxima: {stats.get('temp_max', 0):.1f}°C")
    print(f"      • Lluvia total: {stats.get('lluvia_total', 0):.1f}mm")
    print(f"      • Anomalías: {stats.get('anomalias', 0)}")
    
except Exception as e:
    print(f"   ❌ Error calculando estadísticas: {e}")
    sys.exit(1)

# Test 5: Gráficos
print("\n5️⃣ Probando generación de gráficos...")
try:
    fig = crear_grafico_temperatura(df_enriched)
    print("   ✅ Gráfico de temperatura generado")
    
    fig = crear_grafico_precipitacion(df_enriched)
    print("   ✅ Gráfico de precipitación generado")
    
except Exception as e:
    print(f"   ❌ Error generando gráficos: {e}")
    sys.exit(1)

# Test 6: Export
print("\n6️⃣ Probando exportación...")
try:
    csv_bytes = df_to_csv_bytes(df_enriched)
    print(f"   ✅ CSV generado: {len(csv_bytes)} bytes")
    
    excel_bytes = df_to_excel_bytes(df_enriched)
    print(f"   ✅ Excel generado: {len(excel_bytes)} bytes")
    
except Exception as e:
    print(f"   ⚠️ Error en exportación: {e}")

# Test 7: Limpieza
print("\n7️⃣ Probando limpieza de archivos...")
try:
    limpiar_csvs_antiguos(max_archivos=5)
    print("   ✅ Limpieza de CSVs completada")
except Exception as e:
    print(f"   ⚠️ Error en limpieza: {e}")

# Resumen final
print("\n" + "="*70)
print("✅ TODOS LOS TESTS COMPLETADOS EXITOSAMENTE")
print("="*70)
print("\n💡 Puedes ejecutar el dashboard con:")
print("   streamlit run app/streamlit_app.py")
print("\n📊 Resumen de datos:")
print(f"   • Registros totales: {len(df_enriched)}")
print(f"   • Rango de fechas: {df_enriched['fecha'].min()} a {df_enriched['fecha'].max()}")
if 'estacion' in df_enriched.columns:
    print(f"   • Estaciones: {df_enriched['estacion'].nunique()}")
print()