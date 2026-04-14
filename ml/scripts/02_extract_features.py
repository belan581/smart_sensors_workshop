"""
Fase 2 del pipeline ML: Extracción de características por ventana deslizante.

Concepto clave (para el taller):
    En lugar de pasarle 50 valores crudos al modelo, calculamos ~24 números
    que DESCRIBEN esa ventana: su media, variación, energía, etc.
    El modelo aprende a partir de esas descripciones.

Entrada:  ml/data/processed/cleaned_data.csv
Salida:   ml/data/processed/features_dataset.csv

Uso:
    python scripts/02_extract_features.py
    python scripts/02_extract_features.py --window-size 50 --overlap 0.5
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

# ── Rutas base ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
INPUT_FILE = PROCESSED_DIR / "cleaned_data.csv"
OUTPUT_FILE = PROCESSED_DIR / "features_dataset.csv"

# ── Parámetros de ventana ────────────────────────────────────────────────────
DEFAULT_WINDOW_SIZE = 50  # muestras por ventana (= 0.5 s a 100 Hz)
DEFAULT_OVERLAP = 0.5  # solapamiento entre ventanas (50%)

AXIS_COLUMNS = ["ax", "ay", "az"]
LABEL_COLUMN = "activity"


# ── Funciones de extracción de features ─────────────────────────────────────


def compute_rms(values: np.ndarray) -> float:
    """Root Mean Square: medida de amplitud general de la señal."""
    return float(np.sqrt(np.mean(values**2)))


def compute_energy(values: np.ndarray) -> float:
    """Energía de la señal: suma de cuadrados normalizada."""
    return float(np.sum(values**2) / len(values))


def compute_zero_crossing_rate(values: np.ndarray) -> float:
    """
    Tasa de cruces por cero: mide cuántas veces la señal cruza el eje X.
    Útil para distinguir señales oscilatorias (caminar) de estáticas (quieto).
    """
    mean_centered = values - values.mean()
    crossings = np.where(np.diff(np.sign(mean_centered)))[0]
    return float(len(crossings) / len(values))


def extract_features_from_window(window: pd.DataFrame) -> dict:
    """
    Extrae todas las features de una ventana de aceleración.

    Features por eje (ax, ay, az) — 7 × 3 = 21 features:
        mean    → orientación promedio del eje
        std     → variabilidad / agitación
        min     → valor mínimo (pico negativo)
        max     → valor máximo (pico positivo)
        range   → diferencia max-min (amplitud)
        rms     → amplitud cuadrática media
        energy  → energía de la señal

    Features de magnitud — 3 features:
        magnitude_mean  → nivel promedio de actividad
        magnitude_std   → variabilidad general
        magnitude_max   → pico máximo de movimiento

    Feature global — 1 feature:
        zcr_ax  → tasa de cruces por cero en eje X (distingue periodicidad)

    Total: 25 features por ventana
    """
    features = {}

    for axis in AXIS_COLUMNS:
        if axis not in window.columns:
            continue
        vals = window[axis].values.astype(np.float64)

        features[f"{axis}_mean"] = float(np.mean(vals))
        features[f"{axis}_std"] = float(np.std(vals))
        features[f"{axis}_min"] = float(np.min(vals))
        features[f"{axis}_max"] = float(np.max(vals))
        features[f"{axis}_range"] = float(np.max(vals) - np.min(vals))
        features[f"{axis}_rms"] = compute_rms(vals)
        features[f"{axis}_energy"] = compute_energy(vals)

    # Features de magnitud (si existen los 3 ejes)
    if all(a in window.columns for a in AXIS_COLUMNS):
        mag = np.sqrt(
            window["ax"].values ** 2
            + window["ay"].values ** 2
            + window["az"].values ** 2
        ).astype(np.float64)
        features["magnitude_mean"] = float(np.mean(mag))
        features["magnitude_std"] = float(np.std(mag))
        features["magnitude_max"] = float(np.max(mag))

    # Tasa de cruces por cero en eje X
    if "ax" in window.columns:
        features["zcr_ax"] = compute_zero_crossing_rate(
            window["ax"].values.astype(np.float64)
        )

    return features


def segment_by_label(
    df: pd.DataFrame,
    window_size: int,
    overlap: float,
) -> list[dict]:
    """
    Segmenta el dataset en ventanas por etiqueta.

    Estrategia:
        - Se segmenta DENTRO de cada bloque de la misma etiqueta.
        - No se mezclan muestras de distintas actividades en una misma ventana.
        - Esto refleja la realidad: el movimiento de un período continuo.

    Args:
        df: DataFrame con columnas de ejes + etiqueta
        window_size: número de muestras por ventana
        overlap: fracción de solapamiento entre ventanas (0.0 - 0.9)

    Returns:
        Lista de dicts {features..., label}
    """
    step = max(1, int(window_size * (1 - overlap)))
    records = []

    # Agrupar por etiqueta para no mezclar clases entre ventanas
    for label, group in df.groupby(LABEL_COLUMN, sort=False):
        group = group.reset_index(drop=True)
        n = len(group)

        if n < window_size:
            print(
                f"  [SKIP] Clase '{label}': solo {n} muestras "
                f"(necesita mínimo {window_size})"
            )
            continue

        wins = 0
        for start in range(0, n - window_size + 1, step):
            window = group.iloc[start : start + window_size]
            feats = extract_features_from_window(window)
            feats[LABEL_COLUMN] = label
            records.append(feats)
            wins += 1

        print(f"  Clase '{label}': {n:>6,} muestras → {wins:>5,} ventanas")

    return records


def main(
    window_size: int = DEFAULT_WINDOW_SIZE, overlap: float = DEFAULT_OVERLAP
) -> None:

    # 1. Cargar dataset limpio
    if not INPUT_FILE.exists():
        print(f"[ERROR] No se encontró: {INPUT_FILE}")
        print("  Ejecuta primero: python scripts/01_prepare_data.py")
        return

    print(f"[INFO] Cargando: {INPUT_FILE}")
    df = pd.read_csv(INPUT_FILE)
    print(f"[INFO] {len(df):,} filas cargadas")

    if LABEL_COLUMN not in df.columns:
        print(f"[ERROR] Columna de etiqueta '{LABEL_COLUMN}' no encontrada.")
        print(f"  Columnas disponibles: {list(df.columns)}")
        return

    # 2. Segmentación y extracción
    print(f"\n[INFO] Parámetros de ventana:")
    print(f"  window_size = {window_size} muestras")
    print(f"  overlap     = {overlap:.0%}")
    print(f"  step        = {max(1, int(window_size * (1 - overlap)))} muestras")
    print(f"  Tiempo/ventana ≈ {window_size / 100:.2f} s (asumiendo 100 Hz)\n")

    print("[INFO] Segmentando por clase:")
    records = segment_by_label(df, window_size, overlap)

    if not records:
        print("[ERROR] No se generaron ventanas. Revisa el dataset y parámetros.")
        return

    # 3. Construir DataFrame de features
    features_df = pd.DataFrame(records)

    # Mover la columna de etiqueta al final para claridad
    cols = [c for c in features_df.columns if c != LABEL_COLUMN] + [LABEL_COLUMN]
    features_df = features_df[cols]

    # 4. Resumen
    print(f"\n[RESUMEN] Dataset de features generado:")
    print(f"  Total ventanas  : {len(features_df):,}")
    print(f"  Features por v. : {len(features_df.columns) - 1}")
    print(f"  Columnas totales: {list(features_df.columns)}")
    print(f"\n  Distribución de clases:")
    for label, count in features_df[LABEL_COLUMN].value_counts().items():
        pct = 100 * count / len(features_df)
        print(f"    {str(label):<25} {count:>5,} ventanas ({pct:.1f}%)")

    # 5. Guardar
    features_df.to_csv(OUTPUT_FILE, index=False)
    print(f"\n[OK] Features guardadas en: {OUTPUT_FILE}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extrae features por ventana del dataset MPU6050"
    )
    parser.add_argument(
        "--window-size",
        type=int,
        default=DEFAULT_WINDOW_SIZE,
        help=f"Muestras por ventana (default: {DEFAULT_WINDOW_SIZE})",
    )
    parser.add_argument(
        "--overlap",
        type=float,
        default=DEFAULT_OVERLAP,
        help=f"Solapamiento entre ventanas 0.0-0.9 (default: {DEFAULT_OVERLAP})",
    )
    args = parser.parse_args()
    main(args.window_size, args.overlap)
