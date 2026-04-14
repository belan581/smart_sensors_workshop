"""
Ejemplo de uso: Procesar datos JSON del sensor y escalarlos
"""

import json
from sensor_data_scaler import SensorDataScaler
import pandas as pd

# Ejemplo con datos reales que proporcionaste
sensor_data_json = [
    {
        "id": 1190,
        "device_id": "esp32s3_001",
        "device_timestamp": 1595,
        "received_at": "2026-04-12T22:28:16.268226",
        "ax": [
            0.1831,
            0.1855,
            0.1838,
            0.1862,
            0.1831,
            0.1748,
            0.1787,
            0.1848,
            0.1777,
            0.175,
            0.1892,
            0.1806,
            0.1816,
            0.1855,
            0.1757,
            0.1831,
        ],
        "ay": [
            0.0468,
            0.0473,
            0.0478,
            0.04,
            0.0375,
            0.0412,
            0.0393,
            0.0334,
            0.0209,
            0.0314,
            0.0358,
            0.0305,
            0.0285,
            0.0383,
            0.04,
            0.041,
        ],
        "az": [
            1.0908,
            1.0925,
            1.093,
            1.1013,
            1.1,
            1.0957,
            1.0922,
            1.1091,
            1.1096,
            1.0803,
            1.0981,
            1.0976,
            1.0952,
            1.093,
            1.0981,
            1.101,
        ],
        "temperature": 32.8,
        "battery": 100,
    },
    {
        "id": 1189,
        "device_id": "esp32s3_001",
        "device_timestamp": 1595,
        "received_at": "2026-04-12T22:28:15.768013",
        "ax": [
            0.1804,
            0.1806,
            0.1848,
            0.1826,
            0.1811,
            0.1779,
            0.177,
            0.1818,
            0.1835,
            0.1816,
            0.1789,
            0.1845,
            0.1811,
            0.186,
            0.1809,
            0.185,
        ],
        "ay": [
            0.03,
            0.038,
            0.0488,
            0.0524,
            0.0507,
            0.0488,
            0.0488,
            0.0441,
            0.0385,
            0.0314,
            0.0324,
            0.0351,
            0.0385,
            0.0485,
            0.0527,
            0.0476,
        ],
        "az": [
            1.0964,
            1.0959,
            1.1035,
            1.1057,
            1.0893,
            1.0937,
            1.0986,
            1.0998,
            1.102,
            1.0966,
            1.0952,
            1.0974,
            1.0888,
            1.0976,
            1.093,
            1.1044,
        ],
        "temperature": 32.7,
        "battery": 100,
    },
]


def main():
    print("=" * 70)
    print("PROCESAMIENTO DE DATOS REALES DEL SENSOR ESP32-S3")
    print("=" * 70)

    # Crear el escalador
    scaler = SensorDataScaler()

    print(f"\n📦 Total de paquetes recibidos: {len(sensor_data_json)}")

    # Procesar cada paquete
    all_scaled_data = []

    for i, packet in enumerate(sensor_data_json):
        print(f"\n--- Procesando paquete {i+1} (ID: {packet['id']}) ---")
        print(f"  Timestamp: {packet['received_at']}")
        print(f"  Muestras: {len(packet['ax'])}")
        print(f"  Temperatura: {packet['temperature']}°C")
        print(f"  Batería: {packet['battery']}%")

        # Escalar el paquete
        scaled_df = scaler.scale_packet(packet)
        all_scaled_data.append(scaled_df)

        print(f"  Vista previa (primeras 3 filas):")
        print(scaled_df.head(3).to_string(index=False, float_format="%.2f"))

    # Concatenar todos los datos
    final_df = pd.concat(all_scaled_data, ignore_index=True)

    print("\n" + "=" * 70)
    print("RESULTADO FINAL")
    print("=" * 70)
    print(f"\n✓ Total de muestras procesadas: {len(final_df)}")
    print(f"✓ Formato: Compatible con el dataset de entrenamiento")

    print("\n📊 Estadísticas de los datos escalados:")
    print(final_df.describe().to_string(float_format="%.2f"))

    # Guardar a CSV (opcional)
    output_file = "sensor_data_scaled.csv"
    final_df.to_csv(output_file, index=False)
    print(f"\n💾 Datos guardados en: {output_file}")

    print("\n📝 Próximos pasos:")
    print("  1. Usar estos datos para extraer características")
    print("  2. Aplicar el modelo de ML entrenado")
    print("  3. Predecir la actividad (drinking/driving/throwing)")

    return final_df


if __name__ == "__main__":
    df = main()
