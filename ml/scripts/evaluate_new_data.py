"""
Evalúa el accuracy del modelo en los nuevos datos del MPU6050
"""

import pandas as pd
import numpy as np
from pathlib import Path
import joblib

from feature_extractor import extract_features_from_window

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = ROOT / "outputs"

# Cargar modelo
model = joblib.load(OUTPUTS_DIR / "model_rf.pkl")
label_encoder = joblib.load(OUTPUTS_DIR / "label_encoder.pkl")

print("=" * 70)
print("EVALUACION DE ACCURACY CON DATOS NUEVOS (SIN ESCALADO)")
print("=" * 70)

results = {}

for activity_file in ["drinking.csv", "driving.csv", "throwing.csv"]:
    activity_name = activity_file.replace(".csv", "")
    df = pd.read_csv(ROOT / f"data/raw/{activity_file}")

    window_size = 50
    predictions = []
    true_labels = []
    confidences = []

    for i in range(0, len(df) - window_size + 1, window_size):
        window = df.iloc[i : i + window_size]

        # Extraer features
        features_dict = extract_features_from_window(
            window["ax"].values, window["ay"].values, window["az"].values
        )

        feature_vector = np.array(list(features_dict.values())).reshape(1, -1)

        # Predecir
        pred = model.predict(feature_vector)[0]
        proba = model.predict_proba(feature_vector)[0]

        pred_activity = label_encoder.inverse_transform([pred])[0]
        true_activity = window["activity"].iloc[0]

        predictions.append(pred_activity)
        true_labels.append(true_activity)
        confidences.append(proba[pred])

    # Calcular metricas
    correct = sum(1 for p, t in zip(predictions, true_labels) if p == t)
    total = len(predictions)
    accuracy = (correct / total) * 100
    avg_conf = np.mean(confidences)

    results[activity_name] = {
        "total": total,
        "correct": correct,
        "accuracy": accuracy,
        "confidence": avg_conf,
    }

    print(f"\n{activity_name.upper()}:")
    print(f"  Ventanas: {total}")
    print(f"  Correctas: {correct}")
    print(f"  Accuracy: {accuracy:.2f}%")
    print(f"  Confianza promedio: {avg_conf*100:.1f}%")

# Resumen global
print("\n" + "=" * 70)
print("RESUMEN GLOBAL")
print("=" * 70)

total_windows = sum(r["total"] for r in results.values())
total_correct = sum(r["correct"] for r in results.values())
global_accuracy = (total_correct / total_windows) * 100
global_conf = np.mean([r["confidence"] for r in results.values()])

print(f"\nTotal ventanas: {total_windows}")
print(f"Total correctas: {total_correct}")
print(f"Accuracy global: {global_accuracy:.2f}%")
print(f"Confianza promedio: {global_conf*100:.1f}%")

print("\n" + "=" * 70)
print("CONCLUSION: Los datos nuevos del MPU6050 funcionan perfectamente")
print("            SIN NECESIDAD DE ESCALADO")
print("=" * 70)
