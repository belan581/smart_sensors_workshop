"""
Predicción en tiempo real de actividades desde datos del sensor ESP32-S3

Integra:
  1. Feature extraction - Extrae características estadísticas
  2. Modelo entrenado - Predice actividad (drinking/driving/throwing)

Uso:
    # Desde archivos CSV pre-escalados (MPU6050):
    python scripts/predict_activity.py --csv data/raw/drinking.csv

    # Desde archivos CSV con ventanas personalizadas:
    python scripts/predict_activity.py --csv data/raw/driving.csv
        --window-size 100
"""

import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from feature_extractor import extract_features_from_window

# ── Rutas ───────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = ROOT / "outputs"

MODEL_PATH = OUTPUTS_DIR / "model_rf.pkl"  # Random Forest (recomendado)
LABEL_ENCODER_PATH = OUTPUTS_DIR / "label_encoder.pkl"


class ActivityPredictor:
    """Predictor de actividades desde datos del sensor ESP32-S3"""

    def __init__(self, model_path=MODEL_PATH, le_path=LABEL_ENCODER_PATH):
        """Inicializa el predictor cargando modelo"""
        print("🔄 Inicializando predictor...")

        # Cargar modelo y label encoder
        self.model = joblib.load(model_path)
        self.label_encoder = joblib.load(le_path)

        # Obtener nombres de actividades
        self.activities = self.label_encoder.classes_

        print(f"✅ Modelo cargado: {model_path.name}")
        print(f"✅ Actividades: {', '.join(self.activities)}")
        print(f"✅ Sin escalado (datos pre-escalados)\n")

    def predict_from_window(self, ax, ay, az):
        """Predice actividad desde arrays de aceleración"""
        # Extraer características
        features_dict = extract_features_from_window(ax, ay, az)

        # Convertir a vector
        feature_vector = np.array(list(features_dict.values())).reshape(1, -1)

        # Predecir
        prediction = self.model.predict(feature_vector)[0]
        probabilities = self.model.predict_proba(feature_vector)[0]

        # Formatear resultado
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
            "samples": len(ax),
            "features": features_dict,
        }


def print_prediction_result(result, window_id=None):
    """Imprime resultado de predicción"""
    print("\n" + "=" * 60)
    print(f"🎯 PREDICCIÓN {f'(Ventana {window_id})' if window_id is not None else ''}")
    print("=" * 60)

    print(f"\n🏃 Actividad: {result['activity'].upper()}")
    print(f"📊 Confianza: {result['confidence']*100:.1f}%")
    print(f"📈 Muestras: {result['samples']}")

    print(f"\n📉 Probabilidades:")
    for activity, prob in sorted(
        result["probabilities"].items(), key=lambda x: x[1], reverse=True
    ):
        bar = "█" * int(prob * 40)
        print(f"  {activity:10s} [{prob*100:5.1f}%] {bar}")

    if result.get("true_activity"):
        true_act = result["true_activity"]
        pred_act = result["activity"]
        if true_act == pred_act:
            print(f"\n✅ CORRECTO (Real: {true_act})")
        else:
            print(f"\n❌ INCORRECTO (Real: {true_act}, Predicho: {pred_act})")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Predecir actividad desde datos del sensor"
    )
    parser.add_argument(
        "--csv", type=str, help="Ruta a archivo CSV con datos del MPU6050"
    )
    parser.add_argument(
        "--show-features", action="store_true", help="Mostrar características"
    )
    parser.add_argument(
        "--window-size",
        type=int,
        default=50,
        help="Tamaño de ventana (default: 50)",
    )
    parser.add_argument(
        "--max-windows", type=int, help="Máximo número de ventanas a procesar"
    )
    args = parser.parse_args()

    # Crear predictor
    predictor = ActivityPredictor()

    # Cargar datos desde CSV
    if not args.csv:
        print("❌ Error: Debe especificar --csv con la ruta al archivo")
        print(
            "   Ejemplo: python scripts/predict_activity.py --csv data/raw/drinking.csv"
        )
        return

    print(f"📂 Cargando datos desde: {args.csv}")
    df = pd.read_csv(args.csv)

    # Verificar columnas
    if not all(col in df.columns for col in ["ax", "ay", "az"]):
        print("❌ Error: CSV debe contener columnas 'ax', 'ay', 'az'")
        return

    # Crear ventanas
    window_size = args.window_size
    max_windows = args.max_windows or ((len(df) // window_size) + 1)

    print(f"✅ Dataset: {len(df):,} muestras")
    print(f"✅ Tamaño de ventana: {window_size}")
    print(f"✅ Procesando hasta {max_windows} ventanas\n")

    results = []

    for i in range(
        0, min(len(df) - window_size + 1, max_windows * window_size), window_size
    ):
        window = df.iloc[i : i + window_size]

        result = predictor.predict_from_window(
            window["ax"].values, window["ay"].values, window["az"].values
        )

        result["window_id"] = i // window_size
        result["true_activity"] = (
            window["activity"].iloc[0] if "activity" in df.columns else None
        )

        results.append(result)

        # Mostrar resultado
        print_prediction_result(result, result["window_id"])

        if args.show_features:
            print("\n🔍 Características extraídas:")
            for name, value in result["features"].items():
                print(f"   {name:20s} = {value:.4f}")

    # Resumen
    if len(results) > 1:
        print("\n" + "=" * 60)
        print("📊 RESUMEN GENERAL")
        print("=" * 60)

        activities = [r["activity"] for r in results]
        unique, counts = np.unique(activities, return_counts=True)

        print(f"\nVentanas procesadas: {len(results)}")
        print(f"\nDistribución de predicciones:")
        for activity, count in zip(unique, counts):
            pct = count / len(results) * 100
            print(f"  {activity:10s}: {count:3d} ({pct:5.1f}%)")

        avg_conf = np.mean([r["confidence"] for r in results])
        print(f"\nConfianza promedio: {avg_conf*100:.1f}%")

        # Accuracy si hay etiquetas reales
        if results[0].get("true_activity"):
            correct = sum(1 for r in results if r.get("true_activity") == r["activity"])
            accuracy = correct / len(results) * 100
            print(
                f"\n🎯 Accuracy: {accuracy:.2f}% "
                f"({correct}/{len(results)} correctos)"
            )

        print("=" * 60)


if __name__ == "__main__":
    main()
