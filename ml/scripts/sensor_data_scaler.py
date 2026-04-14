"""
Convertidor de datos del sensor ESP32-S3 al formato del CSV
Escala los datos de 'g' (gravedad) al formato usado en el dataset de entrenamiento
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path

# Rutas
ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"


class SensorDataScaler:
    """Escalador para convertir datos del sensor al formato del CSV"""

    def __init__(self):
        """Calcula factores de escala basados en los datos del CSV"""
        self.factors = self._calculate_scale_factors()
        print(f"✓ Factores de escala calculados:")
        print(f"  Factor X: {self.factors['x']:.2f}")
        print(f"  Factor Y: {self.factors['y']:.2f}")
        print(f"  Factor Z: {self.factors['z']:.2f}")

    def _calculate_scale_factors(self):
        """Calcula los factores de escala analizando los datos del CSV"""
        # Cargar datos de referencia (drinking)
        df = pd.read_csv(RAW_DIR / "drinking_2.csv")

        # Remover valores de calibración (0,0,0)
        df_filtered = df[(df["X"] != 0) | (df["Y"] != 0) | (df["Z"] != 0)]

        # Calcular estadísticas relevantes
        # El sensor en reposo muestra ~1g en Z, ~0.2g en X, ~0.04g en Y
        # Buscamos valores similares en el CSV

        # Para X: El sensor muestra ~0.18g, el CSV muestra ~8-9
        x_typical_csv = df_filtered["X"].median()
        x_typical_sensor = 0.18  # g
        factor_x = x_typical_csv / x_typical_sensor

        # Para Y: El sensor muestra ~0.04g, el CSV muestra ~0.4-2
        y_typical_csv = df_filtered["Y"].abs().median()
        y_typical_sensor = 0.04  # g
        factor_y = y_typical_csv / y_typical_sensor

        # Para Z: El sensor muestra ~1.09g (hacia arriba),
        # el CSV muestra valores negativos (sensor invertido)
        z_typical_csv = df_filtered["Z"].median()
        z_typical_sensor = 1.09  # g
        factor_z = z_typical_csv / z_typical_sensor

        return {"x": factor_x, "y": factor_y, "z": factor_z}

    def scale_sample(self, ax: float, ay: float, az: float) -> tuple:
        """
        Escala una muestra individual del sensor al formato CSV

        Args:
            ax, ay, az: Valores del sensor en 'g'

        Returns:
            Tupla (X, Y, Z) en formato CSV
        """
        X = ax * self.factors["x"]
        Y = ay * self.factors["y"]
        Z = az * self.factors["z"]
        return (X, Y, Z)

    def scale_packet(self, sensor_data: dict) -> pd.DataFrame:
        """
        Escala un paquete completo de datos del sensor

        Args:
            sensor_data: Diccionario con formato:
                {
                    "id": int,
                    "device_id": str,
                    "ax": [float, ...],
                    "ay": [float, ...],
                    "az": [float, ...],
                    ...
                }

        Returns:
            DataFrame con columnas X, Y, Z en formato CSV
        """
        ax_array = np.array(sensor_data["ax"])
        ay_array = np.array(sensor_data["ay"])
        az_array = np.array(sensor_data["az"])

        X = ax_array * self.factors["x"]
        Y = ay_array * self.factors["y"]
        Z = az_array * self.factors["z"]

        df = pd.DataFrame({"X": X, "Y": Y, "Z": Z})

        return df

    def scale_json_batch(self, json_data: list) -> pd.DataFrame:
        """
        Escala un batch de paquetes JSON del sensor

        Args:
            json_data: Lista de diccionarios con datos del sensor

        Returns:
            DataFrame con todas las muestras concatenadas
        """
        all_samples = []

        for packet in json_data:
            df = self.scale_packet(packet)
            all_samples.append(df)

        return pd.concat(all_samples, ignore_index=True)


def demo_usage():
    """Función de demostración"""
    print("\n" + "=" * 60)
    print("DEMOSTRACIÓN: Escalado de Datos del Sensor")
    print("=" * 60 + "\n")

    # Crear escalador
    scaler = SensorDataScaler()

    # Ejemplo de datos del sensor (un paquete)
    sensor_packet = {
        "id": 1190,
        "device_id": "esp32s3_001",
        "ax": [0.1831, 0.1855, 0.1838, 0.1862, 0.1831],
        "ay": [0.0468, 0.0473, 0.0478, 0.0400, 0.0375],
        "az": [1.0908, 1.0925, 1.0930, 1.1013, 1.1000],
        "temperature": 32.8,
        "battery": 100,
    }

    print("\n📡 DATOS ORIGINALES DEL SENSOR (primeras 5 muestras):")
    print(f"  ax: {sensor_packet['ax']}")
    print(f"  ay: {sensor_packet['ay']}")
    print(f"  az: {sensor_packet['az']}")

    # Escalar el paquete
    scaled_df = scaler.scale_packet(sensor_packet)

    print("\n📊 DATOS ESCALADOS (formato CSV):")
    print(scaled_df.head().to_string(index=False))

    print("\n💾 Los datos escalados están listos para:")
    print("  1. Extracción de características")
    print("  2. Predicción con el modelo entrenado")
    print("  3. Evaluación de actividades en tiempo real")

    # Comparar con datos típicos del CSV
    df_csv = pd.read_csv(RAW_DIR / "drinking_2.csv")
    df_csv_clean = df_csv[(df_csv["X"] != 0) | (df_csv["Y"] != 0) | (df_csv["Z"] != 0)]

    print("\n🔍 COMPARACIÓN CON CSV:")
    print("  Rango esperado en CSV (drinking):")
    print(f"    X: {df_csv_clean['X'].min():.2f} a {df_csv_clean['X'].max():.2f}")
    print(f"    Y: {df_csv_clean['Y'].min():.2f} a {df_csv_clean['Y'].max():.2f}")
    print(f"    Z: {df_csv_clean['Z'].min():.2f} a {df_csv_clean['Z'].max():.2f}")

    print("\n  Rango de datos escalados:")
    print(f"    X: {scaled_df['X'].min():.2f} a {scaled_df['X'].max():.2f}")
    print(f"    Y: {scaled_df['Y'].min():.2f} a {scaled_df['Y'].max():.2f}")
    print(f"    Z: {scaled_df['Z'].min():.2f} a {scaled_df['Z'].max():.2f}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    demo_usage()
