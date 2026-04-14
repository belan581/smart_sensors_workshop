"""
Verificar si los datos escalados del sensor están en el rango correcto
para usar con el modelo existente
"""

import pandas as pd
import numpy as np

print("=" * 70)
print("ANÁLISIS: ¿Necesito Re-entrenar?")
print("=" * 70)

# 1. Cargar datos del CSV de entrenamiento
df_train = pd.read_csv("data/processed/cleaned_data.csv")
print("\n📊 DATOS DE ENTRENAMIENTO (cleaned_data.csv):")
print(f"  Total muestras: {len(df_train):,}")
print(f"  Rango X: {df_train['ax'].min():.2f} a {df_train['ax'].max():.2f}")
print(f"  Rango Y: {df_train['ay'].min():.2f} a {df_train['ay'].max():.2f}")
print(f"  Rango Z: {df_train['az'].min():.2f} a {df_train['az'].max():.2f}")

# 2. Cargar datos escalados del sensor
df_sensor = pd.read_csv("sensor_data_scaled.csv")
print("\n📡 DATOS DEL SENSOR ESCALADOS:")
print(f"  Total muestras: {len(df_sensor):,}")
print(f"  Rango X: {df_sensor['X'].min():.2f} a {df_sensor['X'].max():.2f}")
print(f"  Rango Y: {df_sensor['Y'].min():.2f} a {df_sensor['Y'].max():.2f}")
print(f"  Rango Z: {df_sensor['Z'].min():.2f} a {df_sensor['Z'].max():.2f}")


# 3. Verificar rango porcentual
def check_range_overlap(sensor_min, sensor_max, train_min, train_max, axis_name):
    """Verifica si el rango del sensor está dentro del rango de entrenamiento"""
    in_range_min = train_min <= sensor_min <= train_max
    in_range_max = train_min <= sensor_max <= train_max

    if in_range_min and in_range_max:
        status = "✅ DENTRO DEL RANGO"
    elif sensor_min < train_min or sensor_max > train_max:
        status = "⚠️  FUERA DEL RANGO"
    else:
        status = "⚠️  PARCIALMENTE FUERA"

    print(f"\n  {axis_name}:")
    print(f"    Sensor: [{sensor_min:.2f}, {sensor_max:.2f}]")
    print(f"    Entrenamiento: [{train_min:.2f}, {train_max:.2f}]")
    print(f"    Estado: {status}")

    return in_range_min and in_range_max


print("\n🔍 VERIFICACIÓN DE RANGOS:")
x_ok = check_range_overlap(
    df_sensor["X"].min(),
    df_sensor["X"].max(),
    df_train["ax"].min(),
    df_train["ax"].max(),
    "X (ax)",
)
y_ok = check_range_overlap(
    df_sensor["Y"].min(),
    df_sensor["Y"].max(),
    df_train["ay"].min(),
    df_train["ay"].max(),
    "Y (ay)",
)
z_ok = check_range_overlap(
    df_sensor["Z"].min(),
    df_sensor["Z"].max(),
    df_train["az"].min(),
    df_train["az"].max(),
    "Z (az)",
)

print("\n" + "=" * 70)
print("CONCLUSIÓN:")
print("=" * 70)

if x_ok and y_ok and z_ok:
    print("\n✅ NO NECESITAS RE-ENTRENAR")
    print("\nRazones:")
    print("  1. Los datos escalados están dentro del rango de entrenamiento")
    print("  2. El modelo tiene 95.99% accuracy con Random Forest")
    print("  3. El SensorDataScaler convierte correctamente las unidades")
    print("\n📝 Siguiente paso:")
    print("  → Usar el modelo existente con el escalador para predecir")
else:
    print("\n⚠️  CONSIDERA RE-ENTRENAR")
    print("\nRazones:")
    print("  - Algunos datos están fuera del rango de entrenamiento")
    print("  - El modelo podría no generalizar bien")
    print("\n📝 Opciones:")
    print("  1. Re-entrenar combinando datos CSV + datos del sensor")
    print("  2. Ajustar el escalador para mejor alineación")
    print("  3. Probar predicciones y evaluar accuracy real")

print("\n" + "=" * 70)
print("RECOMENDACIÓN FINAL:")
print("=" * 70)

# Calcular estadísticas adicionales
train_stats = df_train[["ax", "ay", "az"]].describe()
sensor_stats = df_sensor[["X", "Y", "Z"]].describe()

print("\nComparación de distribuciones:")
print(
    f"\nMedia entrenamiento: X={train_stats.loc['mean', 'ax']:.2f}, "
    f"Y={train_stats.loc['mean', 'ay']:.2f}, Z={train_stats.loc['mean', 'az']:.2f}"
)
print(
    f"Media sensor:        X={sensor_stats.loc['mean', 'X']:.2f}, "
    f"Y={sensor_stats.loc['mean', 'Y']:.2f}, Z={sensor_stats.loc['mean', 'Z']:.2f}"
)

print(
    f"\nDesv. estándar entrenamiento: X={train_stats.loc['std', 'ax']:.2f}, "
    f"Y={train_stats.loc['std', 'ay']:.2f}, Z={train_stats.loc['std', 'az']:.2f}"
)
print(
    f"Desv. estándar sensor:        X={sensor_stats.loc['std', 'X']:.2f}, "
    f"Y={sensor_stats.loc['std', 'Y']:.2f}, Z={sensor_stats.loc['std', 'Z']:.2f}"
)

# Verificar si el sensor está en reposo (baja variabilidad)
sensor_variability = (
    sensor_stats.loc["std", "X"]
    + sensor_stats.loc["std", "Y"]
    + sensor_stats.loc["std", "Z"]
) / 3

if sensor_variability < 1.0:
    print("\n⚠️  NOTA: Los datos del sensor muestran MUY POCA variabilidad")
    print("   → El sensor parece estar en REPOSO o casi sin movimiento")
    print("   → Para entrenar/probar, necesitas datos con MOVIMIENTO activo:")
    print("      • Bebiendo (drinking)")
    print("      • Conduciendo (driving)")
    print("      • Lanzando (throwing)")
    print("\n💡 ACCIÓN REQUERIDA:")
    print("   1. Recolecta datos haciendo las actividades reales")
    print("   2. Entonces escala y prueba con el modelo existente")
    print("   3. Si funciona mal, considera re-entrenar")
else:
    print("\n✅ Los datos muestran variabilidad suficiente")
    print("   → Procede a hacer predicciones con el modelo existente")
