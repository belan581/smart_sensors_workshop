"""
Fase 4 del pipeline ML: Evaluación visual y análisis del modelo entrenado.

Genera:
  - Matriz de confusión (imagen)
  - Importancia de features (imagen)
  - Curva de precisión/recall

Uso:
    python scripts/04_evaluate.py
    python scripts/04_evaluate.py --model rf
"""

import argparse
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    classification_report,
    confusion_matrix,
)

# ── Rutas base ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
OUTPUTS_DIR = ROOT / "outputs"

FEATURES_FILE = PROCESSED_DIR / "features_dataset.csv"
LABEL_COLUMN = "activity"


def load_model_and_data(model_name: str):
    """Carga modelo, scaler, label encoder y datos de test."""
    model_path = OUTPUTS_DIR / f"model_{model_name}.pkl"
    scaler_path = OUTPUTS_DIR / "scaler.pkl"
    le_path = OUTPUTS_DIR / "label_encoder.pkl"

    if not model_path.exists():
        print(f"[ERROR] No se encontró el modelo: {model_path}")
        print(f"  Ejecuta primero: python scripts/03_train.py --model {model_name}")
        return None, None, None, None, None

    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)
    le = joblib.load(le_path)

    # Cargar datos y recrear split con misma semilla
    from sklearn.model_selection import train_test_split

    df = pd.read_csv(FEATURES_FILE)
    feature_cols = [c for c in df.columns if c != LABEL_COLUMN]
    X = df[feature_cols].values.astype(np.float32)
    y = le.transform(df[LABEL_COLUMN].values)

    _, X_test, _, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Normalizar solo para MLP
    if model_name == "mlp":
        X_test = scaler.transform(X_test)

    return model, X_test, y_test, le, feature_cols


def plot_confusion_matrix(model, X_test, y_test, class_names, model_name):
    """Genera y guarda la matriz de confusión."""
    y_pred = model.predict(X_test)
    cm = confusion_matrix(y_test, y_pred)

    fig, ax = plt.subplots(
        figsize=(max(6, len(class_names) * 1.5), max(5, len(class_names) * 1.5))
    )
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=class_names)
    disp.plot(ax=ax, colorbar=True, cmap="Blues")
    ax.set_title(
        f"Matriz de Confusión — {model_name.upper()}\n"
        f"(filas=real, columnas=predicho)",
        fontsize=12,
    )
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    out_path = OUTPUTS_DIR / f"confusion_matrix_{model_name}.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"[OK] Matriz de confusión guardada: {out_path}")
    plt.close()

    # Imprimir reporte detallado
    report = classification_report(y_test, y_pred, target_names=class_names)
    print(f"\n[{model_name.upper()}] Reporte de clasificación:")
    print(report)


def plot_feature_importance(model, feature_names, model_name, top_n=15):
    """Grafica la importancia de features (solo RandomForest)."""
    if not hasattr(model, "feature_importances_"):
        print(f"[INFO] Importancia de features no disponible para {model_name}")
        return

    importances = model.feature_importances_
    indices = np.argsort(importances)[::-1][:top_n]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(range(top_n), importances[indices], color="steelblue", edgecolor="white")
    ax.set_xticks(range(top_n))
    ax.set_xticklabels(
        [feature_names[i] for i in indices], rotation=45, ha="right", fontsize=9
    )
    ax.set_title(f"Top {top_n} Features más Importantes — RandomForest", fontsize=12)
    ax.set_xlabel("Feature")
    ax.set_ylabel("Importancia (Gini)")
    plt.tight_layout()

    out_path = OUTPUTS_DIR / f"feature_importance_{model_name}.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"[OK] Importancia de features guardada: {out_path}")
    plt.close()


def plot_class_distribution():
    """Grafica la distribución de clases en el dataset de features."""
    if not FEATURES_FILE.exists():
        return

    df = pd.read_csv(FEATURES_FILE)
    if LABEL_COLUMN not in df.columns:
        return

    counts = df[LABEL_COLUMN].value_counts()

    fig, ax = plt.subplots(figsize=(max(6, len(counts) * 1.2), 5))
    bars = ax.bar(counts.index, counts.values, color="coral", edgecolor="white")

    # Etiquetas sobre las barras
    for bar, val in zip(bars, counts.values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 5,
            str(val),
            ha="center",
            va="bottom",
            fontsize=9,
        )

    ax.set_title("Distribución de Clases en el Dataset de Features", fontsize=12)
    ax.set_xlabel("Clase de movimiento")
    ax.set_ylabel("Número de ventanas")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    out_path = OUTPUTS_DIR / "class_distribution.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"[OK] Distribución de clases guardada: {out_path}")
    plt.close()


def main(model_name: str = "rf"):
    print(f"\n[INFO] Evaluando modelo: {model_name.upper()}")

    model, X_test, y_test, le, feature_names = load_model_and_data(model_name)
    if model is None:
        return

    class_names = list(le.classes_)
    print(f"[INFO] Clases: {class_names}")
    print(f"[INFO] Muestras de test: {len(X_test):,}")

    # Generar visualizaciones
    plot_confusion_matrix(model, X_test, y_test, class_names, model_name)
    plot_feature_importance(model, feature_names, model_name)
    plot_class_distribution()

    print(f"\n[RESUMEN] Archivos generados en: {OUTPUTS_DIR}")
    for f in OUTPUTS_DIR.glob("*.png"):
        print(f"  {f.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Evalúa y visualiza el modelo entrenado"
    )
    parser.add_argument(
        "--model",
        choices=["rf", "mlp"],
        default="rf",
        help="Modelo a evaluar (default: rf)",
    )
    args = parser.parse_args()
    main(args.model)
