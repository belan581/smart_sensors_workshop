"""
Analiza los nuevos datos capturados del MPU6050 y compara con datos de entrenamiento
"""

import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Cargar nuevos datos
new_drinking = pd.read_csv(ROOT / "data/raw/drinking.csv")
new_driving = pd.read_csv(ROOT / "data/raw/driving.csv")
new_throwing = pd.read_csv(ROOT / "data/raw/throwing.csv")

# Cargar datos de entrenamiento procesados
training_data = pd.read_csv(ROOT / "data/processed/cleaned_data.csv")

print("=" * 70)
print("📊 ANÁLISIS DE NUEVOS DATOS DEL MPU6050")
print("=" * 70)

print("\n🔍 NUEVOS DATOS CAPTURADOS:")
print(f"\n  drinking.csv:  {len(new_drinking):,} muestras")
print(f"  driving.csv:   {len(new_driving):,} muestras")
print(f"  throwing.csv:  {len(new_throwing):,} muestras")
print(
    f"  TOTAL:         {len(new_drinking) + len(new_driving) + len(new_throwing):,} muestras"
)

# Combinar nuevos datos
new_data = pd.concat([new_drinking, new_driving, new_throwing], ignore_index=True)

print("\n📏 RANGOS DE ACELERACIÓN (NUEVOS DATOS):")
for axis in ["ax", "ay", "az"]:
    print(
        f"  {axis}: [{new_data[axis].min():7.4f}, {new_data[axis].max():7.4f}]  "
        f"media={new_data[axis].mean():7.4f}, std={new_data[axis].std():6.4f}"
    )

print("\n📏 RANGOS DE ACELERACIÓN (DATOS DE ENTRENAMIENTO):")
for axis in ["ax", "ay", "az"]:
    print(
        f"  {axis}: [{training_data[axis].min():7.2f}, {training_data[axis].max():7.2f}]  "
        f"media={training_data[axis].mean():7.2f}, std={training_data[axis].std():6.2f}"
    )

print("\n🔬 COMPARACIÓN DE ESCALAS:")
print("\nRatio (Entrenamiento / Nuevos datos):")
for axis in ["ax", "ay", "az"]:
    ratio_range = (training_data[axis].max() - training_data[axis].min()) / (
        new_data[axis].max() - new_data[axis].min()
    )
    ratio_std = training_data[axis].std() / new_data[axis].std()
    print(f"  {axis}: Rango={ratio_range:6.2f}x,  Std={ratio_std:6.2f}x")

# Verificar si necesitan escalado
needs_scaling = False
for axis in ["ax", "ay", "az"]:
    new_range = new_data[axis].max() - new_data[axis].min()
    train_range = training_data[axis].max() - training_data[axis].min()
    ratio = train_range / new_range

    # Si el ratio es muy grande (>10x), probablemente necesita escalado
    if ratio > 10:
        needs_scaling = True
        break

print("\n" + "=" * 70)
if needs_scaling:
    print("❌ LOS DATOS NUEVOS PARECEN ESTAR EN ESCALA 'g'")
    print("   → Necesitan ser escalados usando SensorDataScaler")
else:
    print("✅ LOS DATOS NUEVOS YA ESTÁN EN LA ESCALA CORRECTA")
    print("   → NO necesitan escalado adicional")
print("=" * 70)

# Mostrar columnas
print("\n📋 COLUMNAS EN NUEVOS DATOS:")
print(f"  {', '.join(new_data.columns)}")

print("\n📋 COLUMNAS EN DATOS DE ENTRENAMIENTO:")
print(f"  {', '.join(training_data.columns)}")

# Verificar giroscopio
if "gx" in new_data.columns:
    print("\n🔄 DATOS DE GIROSCOPIO DETECTADOS:")
    print(f"  gx: [{new_data['gx'].min():7.4f}, {new_data['gx'].max():7.4f}]")
    print(f"  gy: [{new_data['gy'].min():7.4f}, {new_data['gy'].max():7.4f}]")
    print(f"  gz: [{new_data['gz'].min():7.4f}, {new_data['gz'].max():7.4f}]")
