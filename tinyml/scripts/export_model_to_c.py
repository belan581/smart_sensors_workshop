"""
export_model_to_c.py
────────────────────
Exporta el RandomForestClassifier entrenado a código C usando micromlgen.

Salida:
    ../components/inference_engine/model_rf.h

Uso:
    python scripts/export_model_to_c.py
"""

import sys
import os
import pathlib

# Asegurar que feature_extractor sea importable desde este directorio
SCRIPTS_DIR = pathlib.Path(__file__).parent
ROOT_DIR = SCRIPTS_DIR.parent
OUTPUT_DIR = ROOT_DIR / "components" / "inference_engine"

sys.path.insert(0, str(SCRIPTS_DIR))

import joblib
from micromlgen import port

# ── Cargar artefactos ────────────────────────────────────────────
MODELS_DIR = ROOT_DIR / "models"

print(f"Cargando modelo desde: {MODELS_DIR / 'model_rf.pkl'}")
model = joblib.load(MODELS_DIR / "model_rf.pkl")

print(f"Cargando label encoder desde: {MODELS_DIR / 'label_encoder.pkl'}")
le = joblib.load(MODELS_DIR / "label_encoder.pkl")

print(f"Clases: {le.classes_}")
print(f"Árboles originales: {model.n_estimators}")
print(f"Features: {model.n_features_in_}")

# ── Reducir a 15 árboles para caber en flash del ESP32-S3 ────────
N_TREES = 15
model.estimators_ = model.estimators_[:N_TREES]
model.n_estimators = N_TREES
print(f"Árboles exportados: {N_TREES} (reducido para flash ESP32-S3)")

# ── Exportar a C ─────────────────────────────────────────────────
classmap = {int(i): str(c) for i, c in enumerate(le.classes_)}
c_code = port(model, classmap=classmap)

# ── Escribir archivo ─────────────────────────────────────────────
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
output_path = OUTPUT_DIR / "model_rf.h"

with open(output_path, "w", encoding="utf-8") as f:
    f.write(c_code)

print(f"\nArchivo generado: {output_path}")
print(f"Tamaño: {len(c_code):,} caracteres")
