"""
Comparar datos del sensor con los datos en CSV
"""

import pandas as pd
import numpy as np

# Analizar datos del sensor (ejemplo de uno de los registros)
sensor_ax = [0.1831, 0.1855, 0.1838, 0.1862, 0.1831]  # Primeras 5 muestras
sensor_ay = [0.0468, 0.0473, 0.0478, 0.04, 0.0375]
sensor_az = [1.0908, 1.0925, 1.093, 1.1013, 1.1]

print("=" * 60)
print("COMPARACIÓN DE DATOS: SENSOR vs CSV")
print("=" * 60)

print("\n📡 DATOS DEL SENSOR (últimas mediciones):")
print(
    f"  ax: rango {min(sensor_ax):.4f} a {max(sensor_ax):.4f}, media: {np.mean(sensor_ax):.4f}"
)
print(
    f"  ay: rango {min(sensor_ay):.4f} a {max(sensor_ay):.4f}, media: {np.mean(sensor_ay):.4f}"
)
print(
    f"  az: rango {min(sensor_az):.4f} a {max(sensor_az):.4f}, media: {np.mean(sensor_az):.4f}"
)
print(f"  Temperatura: 32.6-32.8°C")
print(f"  Formato: 50 muestras por paquete")

print("\n📊 DATOS EN CSV (drinking_2.csv):")
df = pd.read_csv("data/raw/drinking_2.csv")
print(
    f"  X: rango {df['X'].min():.4f} a {df['X'].max():.4f}, media: {df['X'].mean():.4f}"
)
print(
    f"  Y: rango {df['Y'].min():.4f} a {df['Y'].max():.4f}, media: {df['Y'].mean():.4f}"
)
print(
    f"  Z: rango {df['Z'].min():.4f} a {df['Z'].max():.4f}, media: {df['Z'].mean():.4f}"
)
print(f"  Formato: 1 muestra por fila")

print("\n⚖️  DIFERENCIAS DETECTADAS:")

# Calcular factor de escala
factor_x = df["X"].mean() / np.mean(sensor_ax)
factor_y = df["Y"].mean() / np.mean(sensor_ay)
factor_z = df["Z"].mean() / np.mean(sensor_az)

print(f"\n1. ESCALA:")
print(f"   - Factor X: {factor_x:.2f}x (CSV es {factor_x:.2f} veces mayor)")
print(f"   - Factor Y: {factor_y:.2f}x (CSV es {factor_y:.2f} veces mayor)")
print(f"   - Factor Z: {factor_z:.2f}x (CSV es {factor_z:.2f} veces mayor)")

# Convertir valores del sensor
sensor_ax_scaled = [x * factor_x for x in sensor_ax]
sensor_ay_scaled = [y * factor_y for y in sensor_ay]
sensor_az_scaled = [z * factor_z for z in sensor_az]

print(f"\n2. VALORES SENSOR ESCALADOS (multiplicados por factor):")
print(f"   ax: {sensor_ax_scaled[:5]}")
print(f"   ay: {sensor_ay_scaled[:5]}")
print(f"   az: {sensor_az_scaled[:5]}")

print(f"\n3. VALORES TÍPICOS EN CSV:")
print(df[["X", "Y", "Z"]].head(5).to_string(index=False))

print("\n" + "=" * 60)
print("CONCLUSIÓN:")
print("=" * 60)
if 9 < factor_x < 11:
    print("✓ Los datos del sensor están en unidades de 'g' (gravedad)")
    print("✓ Los datos del CSV están en m/s² (multiplicados por ~9.81)")
    print("✓ Para comparar, multiplica valores del sensor por ~9.81")
else:
    print(f"⚠ Factor de escala inusual: ~{factor_x:.2f}x")
    print("  Verifica las unidades de medición del sensor")

print(f"\nValor de gravedad en reposo (az):")
print(f"  Sensor: ~{np.mean(sensor_az):.2f}g (correcto)")
print(f"  CSV: ~{df['Z'].mean():.2f} (unidades diferentes)")
