"""
Fase 3 del pipeline ML: Entrenamiento del clasificador de movimiento.

Entrena dos modelos y los compara:
  - Opción A: RandomForestClassifier  (recomendado para el taller)
  - Opción B: MLPClassifier (red neuronal simple)

Salida:
  ml/outputs/model_rf.pkl
  ml/outputs/model_mlp.pkl
  ml/outputs/scaler.pkl
  ml/outputs/label_encoder.pkl
  ml/outputs/metrics_report.txt

Uso:
    python scripts/03_train.py              → entrena ambos
    python scripts/03_train.py --model rf   → solo RandomForest
    python scripts/03_train.py --model mlp  → solo MLP
    python scripts/03_train.py --full-pipeline  → ejecuta scripts 01 y 02 antes
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler

# ── Rutas base ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
OUTPUTS_DIR = ROOT / "outputs"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

FEATURES_FILE = PROCESSED_DIR / "features_dataset.csv"
LABEL_COLUMN = "activity"

# ── Configuración de modelos ─────────────────────────────────────────────────

RF_PARAMS = {
    # n_estimators: cantidad de árboles. Más árboles = más precisión pero más lento.
    # 100 es un buen balance para este tamaño de dataset.
    "n_estimators": 100,
    # max_depth: profundidad máxima por árbol. None = sin límite.
    # Limitar evita overfitting y hace el modelo más explicable.
    "max_depth": 15,
    # min_samples_split: mínimo de muestras para dividir un nodo.
    "min_samples_split": 5,
    # random_state: semilla para reproducibilidad.
    "random_state": 42,
    # n_jobs: usar todos los núcleos del procesador.
    "n_jobs": -1,
    # class_weight: compensa clases desbalanceadas automáticamente.
    "class_weight": "balanced",
}

MLP_PARAMS = {
    # hidden_layer_sizes: arquitectura de la red.
    # (128, 64) = dos capas ocultas de 128 y 64 neuronas.
    # Simple, rápida de entrenar, fácil de explicar.
    "hidden_layer_sizes": (128, 64),
    # activation: función de activación. ReLU es la más usada hoy en día.
    "activation": "relu",
    # solver: optimizador. 'adam' funciona bien con datasets medianos.
    "solver": "adam",
    # max_iter: épocas máximas de entrenamiento.
    "max_iter": 500,
    # early_stopping: detiene el entrenamiento si el val_loss no mejora.
    "early_stopping": True,
    "validation_fraction": 0.1,
    # learning_rate_init: tasa de aprendizaje inicial.
    "learning_rate_init": 0.001,
    "random_state": 42,
}

TEST_SIZE = 0.2  # 20% para test
CV_FOLDS = 5  # validación cruzada de 5 pliegues


# ── Funciones de entrenamiento ───────────────────────────────────────────────


def load_and_split(features_file: Path):
    """Carga el dataset de features, separa X/y, aplica train/test split."""
    print(f"[INFO] Cargando features: {features_file}")
    df = pd.read_csv(features_file)
    print(f"[INFO] {len(df):,} ventanas × {len(df.columns) - 1} features")

    feature_cols = [c for c in df.columns if c != LABEL_COLUMN]
    X = df[feature_cols].values.astype(np.float32)
    y_raw = df[LABEL_COLUMN].values

    # Codificar etiquetas a enteros: "walking" → 0, "running" → 1, etc.
    le = LabelEncoder()
    y = le.fit_transform(y_raw)

    print(f"\n[INFO] Clases detectadas: {list(le.classes_)}")
    print(f"[INFO] Codificación: {dict(zip(le.classes_, range(len(le.classes_))))}")

    # Separar train/test con estratificación (mantiene proporción de clases)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=42, stratify=y
    )
    print(f"\n[INFO] Train: {len(X_train):,} ventanas | Test: {len(X_test):,} ventanas")

    return X_train, X_test, y_train, y_test, le, feature_cols


def scale_features(X_train, X_test):
    """
    Normalización con StandardScaler.

    Por qué normalizar:
    - Necesario para MLP (los gradientes divergen con valores muy distintos)
    - No estrictamente necesario para RandomForest (árboles son invariantes a escala)
    - Pero normalizar siempre es buena práctica y facilita la comparación
    """
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)  # fit SOLO en train
    X_test_scaled = scaler.transform(X_test)  # transform en test
    return X_train_scaled, X_test_scaled, scaler


def train_random_forest(X_train, y_train, X_test, y_test, class_names):
    """Entrena RandomForestClassifier y retorna modelo + métricas."""
    print("\n" + "=" * 55)
    print("  ENTRENAMIENTO: RandomForestClassifier")
    print("=" * 55)
    print(f"  Parámetros: {RF_PARAMS}")

    model = RandomForestClassifier(**RF_PARAMS)

    # Validación cruzada (mide la robustez del modelo)
    print(f"\n[RF] Validación cruzada ({CV_FOLDS} pliegues)...")
    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=42)
    cv_scores = cross_val_score(model, X_train, y_train, cv=cv, scoring="accuracy")
    print(f"[RF] CV Accuracy: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    # Entrenamiento final
    t0 = time.time()
    model.fit(X_train, y_train)
    t_train = time.time() - t0
    print(f"[RF] Tiempo de entrenamiento: {t_train:.2f} s")

    # Evaluación en test
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"[RF] Accuracy en test      : {acc:.4f} ({acc*100:.2f}%)")

    report = classification_report(y_test, y_pred, target_names=class_names)
    print(f"\n[RF] Reporte de clasificación:\n{report}")

    # Importancia de features (ventaja didáctica del RF)
    importances = model.feature_importances_
    print("[RF] Top 10 features más importantes:")
    # Se imprimirán en la función principal donde tenemos los nombres

    metrics = {
        "cv_mean": float(cv_scores.mean()),
        "cv_std": float(cv_scores.std()),
        "test_accuracy": float(acc),
        "train_time_s": float(t_train),
        "report": report,
    }
    return model, metrics, importances


def train_mlp(X_train_scaled, y_train, X_test_scaled, y_test, class_names):
    """Entrena MLPClassifier y retorna modelo + métricas."""
    print("\n" + "=" * 55)
    print("  ENTRENAMIENTO: MLPClassifier")
    print("=" * 55)
    print(f"  Arquitectura: {MLP_PARAMS['hidden_layer_sizes']}")
    print(f"  Parámetros: {MLP_PARAMS}")

    model = MLPClassifier(**MLP_PARAMS)

    # Validación cruzada
    print(f"\n[MLP] Validación cruzada ({CV_FOLDS} pliegues)...")
    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=42)
    cv_scores = cross_val_score(
        model, X_train_scaled, y_train, cv=cv, scoring="accuracy"
    )
    print(f"[MLP] CV Accuracy: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    # Entrenamiento final
    t0 = time.time()
    model.fit(X_train_scaled, y_train)
    t_train = time.time() - t0
    print(f"[MLP] Épocas           : {model.n_iter_}")
    print(f"[MLP] Tiempo entrenom. : {t_train:.2f} s")

    # Evaluación en test
    y_pred = model.predict(X_test_scaled)
    acc = accuracy_score(y_test, y_pred)
    print(f"[MLP] Accuracy en test : {acc:.4f} ({acc*100:.2f}%)")

    report = classification_report(y_test, y_pred, target_names=class_names)
    print(f"\n[MLP] Reporte de clasificación:\n{report}")

    metrics = {
        "cv_mean": float(cv_scores.mean()),
        "cv_std": float(cv_scores.std()),
        "test_accuracy": float(acc),
        "train_time_s": float(t_train),
        "n_iter": model.n_iter_,
        "report": report,
    }
    return model, metrics


def print_feature_importance(importances, feature_names, top_n=10):
    """Muestra las features más importantes del RandomForest."""
    indices = np.argsort(importances)[::-1][:top_n]
    print(f"\n[RF] Top {top_n} features más importantes:")
    for rank, idx in enumerate(indices, 1):
        print(f"  {rank:2}. {feature_names[idx]:<30} {importances[idx]:.4f}")


def generate_report(rf_metrics, mlp_metrics, output_path: Path):
    """Genera archivo de texto con comparación de métricas."""
    lines = [
        "=" * 60,
        "  REPORTE COMPARATIVO DE MODELOS",
        "  Smart Sensors Workshop - Clasificador de Movimiento",
        "=" * 60,
        "",
        "── RandomForestClassifier ──────────────────────────────",
        f"  CV Accuracy    : {rf_metrics['cv_mean']:.4f} ± {rf_metrics['cv_std']:.4f}",
        f"  Test Accuracy  : {rf_metrics['test_accuracy']:.4f}",
        f"  Tiempo entren. : {rf_metrics['train_time_s']:.2f} s",
        "",
        "  Clasificación por clase:",
        rf_metrics["report"],
        "",
        "── MLPClassifier ───────────────────────────────────────",
        f"  CV Accuracy    : {mlp_metrics['cv_mean']:.4f} ± {mlp_metrics['cv_std']:.4f}",
        f"  Test Accuracy  : {mlp_metrics['test_accuracy']:.4f}",
        f"  Tiempo entren. : {mlp_metrics['train_time_s']:.2f} s",
        f"  Épocas         : {mlp_metrics.get('n_iter', 'N/A')}",
        "",
        "  Clasificación por clase:",
        mlp_metrics["report"],
        "",
        "── Recomendación para el taller ────────────────────────",
    ]

    rf_acc = rf_metrics["test_accuracy"]
    mlp_acc = mlp_metrics["test_accuracy"]

    if rf_acc >= mlp_acc - 0.02:  # RF dentro de 2% del MLP
        lines.append("  RECOMENDADO: RandomForestClassifier")
        lines.append("  Razón: Rendimiento comparable, más interpretable,")
        lines.append("         no requiere normalización, más fácil de explicar.")
    else:
        lines.append("  RECOMENDADO: MLPClassifier")
        lines.append("  Razón: Significantly better accuracy en este dataset.")

    lines.append("=" * 60)

    report_text = "\n".join(lines)
    output_path.write_text(report_text, encoding="utf-8")
    print(f"\n[OK] Reporte guardado en: {output_path}")
    return report_text


def save_artifacts(model_rf, model_mlp, scaler, le, which):
    """Guarda modelos, scaler y label encoder con joblib."""
    saved = []

    if model_rf is not None and which in ("rf", "both"):
        path = OUTPUTS_DIR / "model_rf.pkl"
        joblib.dump(model_rf, path)
        print(f"[OK] Modelo RF guardado: {path}")
        saved.append(path)

    if model_mlp is not None and which in ("mlp", "both"):
        path = OUTPUTS_DIR / "model_mlp.pkl"
        joblib.dump(model_mlp, path)
        print(f"[OK] Modelo MLP guardado: {path}")
        saved.append(path)

    if scaler is not None:
        path = OUTPUTS_DIR / "scaler.pkl"
        joblib.dump(scaler, path)
        print(f"[OK] Scaler guardado: {path}")

    if le is not None:
        path = OUTPUTS_DIR / "label_encoder.pkl"
        joblib.dump(le, path)
        print(f"[OK] LabelEncoder guardado: {path}")
        print(f"     Clases: {list(le.classes_)}")

    return saved


def run_previous_scripts():
    """Ejecuta scripts 01 y 02 como parte del pipeline completo."""
    scripts = ["01_prepare_data.py", "02_extract_features.py"]
    scripts_dir = Path(__file__).parent

    for script in scripts:
        script_path = scripts_dir / script
        print(f"\n[PIPELINE] Ejecutando {script}...")
        result = subprocess.run(
            [sys.executable, str(script_path)], capture_output=False
        )
        if result.returncode != 0:
            print(f"[ERROR] {script} falló. Abortando pipeline.")
            sys.exit(1)


def main(which: str = "both", full_pipeline: bool = False):

    # Pipeline completo opcional
    if full_pipeline:
        run_previous_scripts()

    # Verificar que el archivo de features existe
    if not FEATURES_FILE.exists():
        print(f"[ERROR] No se encontró: {FEATURES_FILE}")
        print("  Ejecuta primero:")
        print("    python scripts/01_prepare_data.py")
        print("    python scripts/02_extract_features.py")
        print("  O usa: python scripts/03_train.py --full-pipeline")
        sys.exit(1)

    # Cargar y dividir datos
    X_train, X_test, y_train, y_test, le, feature_names = load_and_split(FEATURES_FILE)
    class_names = list(le.classes_)

    # Normalizar (necesario para MLP, sin daño para RF)
    X_train_sc, X_test_sc, scaler = scale_features(X_train, X_test)

    rf_model, mlp_model = None, None
    rf_metrics, mlp_metrics = None, None
    rf_importances = None

    # Entrenar RandomForest
    if which in ("rf", "both"):
        rf_model, rf_metrics, rf_importances = train_random_forest(
            X_train, y_train, X_test, y_test, class_names
        )
        print_feature_importance(rf_importances, feature_names)

    # Entrenar MLP
    if which in ("mlp", "both"):
        mlp_model, mlp_metrics = train_mlp(
            X_train_sc, y_train, X_test_sc, y_test, class_names
        )

    # Comparativa y recomendación
    if rf_metrics and mlp_metrics:
        print("\n" + "=" * 55)
        print("  COMPARATIVA FINAL")
        print("=" * 55)
        print(
            f"  RandomForest → Accuracy: {rf_metrics['test_accuracy']:.4f}  "
            f"| CV: {rf_metrics['cv_mean']:.4f} ± {rf_metrics['cv_std']:.4f}  "
            f"| Tiempo: {rf_metrics['train_time_s']:.1f}s"
        )
        print(
            f"  MLP          → Accuracy: {mlp_metrics['test_accuracy']:.4f}  "
            f"| CV: {mlp_metrics['cv_mean']:.4f} ± {mlp_metrics['cv_std']:.4f}  "
            f"| Tiempo: {mlp_metrics['train_time_s']:.1f}s"
        )

        print(
            """
  RECOMENDACIÓN PARA EL TALLER:
  ──────────────────────────────────────────────────────
  RandomForest es la mejor opción si:
    ✓ Los accuracies son similares (< 3% de diferencia)
    ✓ Quieres explicar qué features importan más
    ✓ Quieres resultados reproducibles sin ajuste fino
    ✓ No quieres preocuparte por normalización en producción

  MLP es preferible si:
    ✓ El accuracy es significativamente mejor (> 5%)
    ✓ Quieres introducir conceptos de redes neuronales
    ✓ Tienes > 10,000 ventanas de entrenamiento
  ──────────────────────────────────────────────────────"""
        )

        # Guardar reporte comparativo
        generate_report(rf_metrics, mlp_metrics, OUTPUTS_DIR / "metrics_report.txt")

    # Guardar artefactos
    print("\n[INFO] Guardando artefactos...")
    save_artifacts(rf_model, mlp_model, scaler, le, which)

    print("\n[PIPELINE COMPLETO] Siguiente paso:")
    print("  → Copiar ml/outputs/*.pkl a backend/models/")
    print("  → Ejecutar: python scripts/04_evaluate.py  (análisis detallado)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Entrena clasificador de movimiento MPU6050"
    )
    parser.add_argument(
        "--model",
        choices=["rf", "mlp", "both"],
        default="both",
        help="Modelo a entrenar (default: both)",
    )
    parser.add_argument(
        "--full-pipeline",
        action="store_true",
        help="Ejecuta también los scripts 01 y 02 antes de entrenar",
    )
    args = parser.parse_args()
    main(which=args.model, full_pipeline=args.full_pipeline)
