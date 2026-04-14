"""
Predicción en tiempo real de actividades desde datos del sensor ESP32-S3

Integra:
  1. SensorDataScaler - Escala datos de 'g' a formato CSV
  2. Feature extraction - Extrae características estadísticas
  3. Modelo entrenado - Predice actividad (drinking/driving/throwing)

Uso:
    python scripts/predict_activity.py --json sensor_data.json
    python scripts/predict_activity.py  # Usa datos de ejemplo
"""

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from feature_extractor import extract_features_from_window, feature_names
from sensor_data_scaler import SensorDataScaler

# ── Rutas ───────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = ROOT / "outputs"

MODEL_PATH = OUTPUTS_DIR / "model_rf.pkl"  # Random Forest (recomendado)
LABEL_ENCODER_PATH = OUTPUTS_DIR / "label_encoder.pkl"


class ActivityPredictor:
    """Predictor de actividades desde datos del sensor ESP32-S3"""

    def __init__(self, model_path=MODEL_PATH, le_path=LABEL_ENCODER_PATH):
        """Inicializa el predictor cargando modelo y escalador"""
        print("🔄 Inicializando predictor...")

        # Cargar modelo y label encoder
        self.model = joblib.load(model_path)
        self.label_encoder = joblib.load(le_path)

        # Crear escalador para datos del sensor
        self.scaler = SensorDataScaler()

        # Obtener nombres de actividades
        self.activities = self.label_encoder.classes_

        print(f"✅ Modelo cargado: {model_path.name}")
        print(f"✅ Actividades: {', '.join(self.activities)}")
        print(f"✅ Escalador configurado\n")

    def predict_from_sensor_packet(self, sensor_packet: dict) -> dict:
        """
        Predice actividad desde un paquete del sensor

        Args:
            sensor_packet: Dict con keys 'ax', 'ay', 'az' (arrays en 'g')

        Returns:
            Dict con:
                - activity: Nombre de la actividad predicha
                - confidence: Probabilidad (0-1)
                - probabilities: Dict con probabilidad por cada actividad
                - samples: Número de muestras procesadas
        """
        # 1. Escalar datos del sensor a formato CSV
        scaled_df = self.scaler.scale_packet(sensor_packet)

        # 2. Extraer características (ventana completa)
        features_dict = extract_features_from_window(
            scaled_df["X"].values, scaled_df["Y"].values, scaled_df["Z"].values
        )

        # 3. Convertir a vector para el modelo
        feature_vector = np.array(list(features_dict.values())).reshape(1, -1)

        # 4. Predecir
        prediction = self.model.predict(feature_vector)[0]
        probabilities = self.model.predict_proba(feature_vector)[0]

        # 5. Formatear resultado
        activity = self.label_encoder.inverse_transform([prediction])[0]
        confidence = float(probabilities[prediction])

        prob_dict = {
            self.activities[i]: float(probabilities[i])
            for i in range(len(self.activities))
        }

        return {
            "activity": activity,
            "confidence": confidence,
            "probabilities": prob_dict,
            "samples": len(sensor_packet["ax"]),
            "features": features_dict,
        }

    def predict_from_json_batch(self, json_data: list) -> list:
        """
        Predice actividades desde múltiples paquetes JSON

        Args:
            json_data: Lista de diccionarios con datos del sensor

        Returns:
            Lista de resultados de predicción
        """
        results = []

        for i, packet in enumerate(json_data):
            print(
                f"📦 Procesando paquete {i+1}/{len(json_data)} (ID: {packet.get('id', 'N/A')})..."
            )
            result = self.predict_from_sensor_packet(packet)
            result["packet_id"] = packet.get("id")
            result["timestamp"] = packet.get("received_at")
            results.append(result)

        return results


def print_prediction_result(result: dict):
    """Imprime resultado de predicción de forma legible"""
    print("\n" + "=" * 60)
    print("🎯 PREDICCIÓN DE ACTIVIDAD")
    print("=" * 60)

    print(f"\n🏃 Actividad detectada: {result['activity'].upper()}")
    print(f"📊 Confianza: {result['confidence']*100:.1f}%")
    print(f"📈 Muestras: {result['samples']}")

    if "timestamp" in result and result["timestamp"]:
        print(f"🕐 Timestamp: {result['timestamp']}")

    print(f"\n📉 Probabilidades por actividad:")
    for activity, prob in sorted(
        result["probabilities"].items(), key=lambda x: x[1], reverse=True
    ):
        bar = "█" * int(prob * 40)
        print(f"  {activity:10s} [{prob*100:5.1f}%] {bar}")

    # Interpretar resultado
    print(f"\n💡 Interpretación:")
    if result["confidence"] > 0.90:
        print(f"   ✅ Alta confianza - Predicción muy confiable")
    elif result["confidence"] > 0.70:
        print(f"   ⚠️  Confianza media - Predicción razonable")
    else:
        print(f"   ❌ Baja confianza - Predicción incierta")

    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Predecir actividad desde datos del sensor"
    )
    parser.add_argument(
        "--json", type=str, help="Ruta a archivo JSON con datos del sensor"
    )
    parser.add_argument(
        "--show-features", action="store_true", help="Mostrar características extraídas"
    )
    args = parser.parse_args()

    # Crear predictor
    predictor = ActivityPredictor()

    # Cargar datos
    if args.json:
        print(f"📂 Cargando datos desde: {args.json}")
        with open(args.json, "r") as f:
            sensor_data = json.load(f)
    else:
        print("📂 Usando datos de ejemplo (sensor en reposo)")
        sensor_data = [
            {
                "id": 1190,
                "device_id": "esp32s3_001",
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
                    0.1884,
                    0.1855,
                    0.1906,
                    0.1828,
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
                    0.0449,
                    0.0441,
                    0.048,
                    0.0512,
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
                    1.0895,
                    1.1037,
                    1.0959,
                    1.0944,
                ],
                "temperature": 32.8,
                "battery": 100,
            }
        ]

    # Asegurar que sea lista
    if isinstance(sensor_data, dict):
        sensor_data = [sensor_data]

    # Predecir
    print(f"\n🚀 Iniciando predicción para {len(sensor_data)} paquete(s)...\n")

    results = predictor.predict_from_json_batch(sensor_data)

    # Mostrar resultados
    for result in results:
        print_prediction_result(result)

        if args.show_features:
            print("🔍 Características extraídas:")
            for name, value in result["features"].items():
                print(f"   {name:20s} = {value:.4f}")
            print()

    # Resumen si hay múltiples paquetes
    if len(results) > 1:
        print("=" * 60)
        print("📊 RESUMEN DE PREDICCIONES")
        print("=" * 60)

        activities = [r["activity"] for r in results]
        unique, counts = np.unique(activities, return_counts=True)

        print(f"\nDistribución de actividades:")
        for activity, count in zip(unique, counts):
            pct = count / len(results) * 100
            print(f"  {activity:10s}: {count:2d} ({pct:5.1f}%)")

        avg_conf = np.mean([r["confidence"] for r in results])
        print(f"\nConfianza promedio: {avg_conf*100:.1f}%")


if __name__ == "__main__":
    main()
