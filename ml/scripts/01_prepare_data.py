"""
Fase 1 del pipeline ML: Carga, inspección y preparación del dataset.

Dataset: mpu6050-3-axis-acceleration-dataset (Kaggle)
Columnas esperadas: una columna de etiqueta + ax, ay, az (y posiblemente timestamp)

Salida: ml/data/processed/cleaned_data.csv

Uso:
    python scripts/01_prepare_data.py
    python scripts/01_prepare_data.py --input data/raw/mi_archivo.csv
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ── Rutas base ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = PROCESSED_DIR / "cleaned_data.csv"

# ── Configuración del dataset ────────────────────────────────────────────────
# Ajusta estos nombres según el CSV descargado de Kaggle
LABEL_COLUMN = "activity"  # Nombre de la columna de etiqueta
AXIS_COLUMNS = ["ax", "ay", "az"]  # Nombres de las columnas de aceleración

# Mapas alternativos de nombres de columna en distintas versiones del dataset
COLUMN_ALIASES = {
    "label": LABEL_COLUMN,
    "class": LABEL_COLUMN,
    "activity": LABEL_COLUMN,
    "target": LABEL_COLUMN,
    "x": "ax",
    "accel_x": "ax",
    "X": "ax",
    "y": "ay",
    "accel_y": "ay",
    "Y": "ay",
    "z": "az",
    "accel_z": "az",
    "Z": "az",
}


def find_csv_files(raw_dir: Path) -> list[Path]:
    """Busca todos los archivos CSV en la carpeta raw/."""
    csvs = list(raw_dir.glob("*.csv"))
    if not csvs:
        print(f"\n[ERROR] No se encontró ningún CSV en: {raw_dir}")
        print("  → Descarga el dataset de Kaggle y colócalo en ml/data/raw/")
        print("  → URL: https://www.kaggle.com/datasets/")
        print("         (buscar: mpu6050-3-axis-acceleration-dataset)\n")
        sys.exit(1)
    print(f"[INFO] Se encontraron {len(csvs)} archivos CSV:")
    for csv_file in csvs:
        print(f"       - {csv_file.name}")
    return csvs


def load_and_combine_csvs(csv_files: list[Path]) -> pd.DataFrame:
    """Carga y combina múltiples archivos CSV en un solo DataFrame."""
    all_dfs = []
    for csv_file in csv_files:
        print(f"[INFO] Cargando: {csv_file.name}")
        df = pd.read_csv(csv_file)
        print(f"       {len(df):,} filas")
        all_dfs.append(df)

    combined_df = pd.concat(all_dfs, ignore_index=True)
    print(f"[INFO] Total combinado: {len(combined_df):,} filas")
    return combined_df


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Renombra columnas usando COLUMN_ALIASES para compatibilidad."""
    rename_map = {}
    for col in df.columns:
        col_lower = col.strip().lower()
        if col_lower in COLUMN_ALIASES:
            rename_map[col] = COLUMN_ALIASES[col_lower]
        elif col in COLUMN_ALIASES:
            rename_map[col] = COLUMN_ALIASES[col]
    if rename_map:
        print(f"[INFO] Renombrando columnas: {rename_map}")
        df = df.rename(columns=rename_map)
    return df


def inspect_dataset(df: pd.DataFrame) -> None:
    """Imprime un resumen didáctico del dataset."""
    print("\n" + "=" * 55)
    print("  INSPECCIÓN DEL DATASET")
    print("=" * 55)
    print(f"  Filas totales       : {len(df):,}")
    print(f"  Columnas            : {list(df.columns)}")
    print(f"  Tipos de datos      :\n{df.dtypes.to_string()}")

    print(f"\n  Valores nulos por columna:")
    nulls = df.isnull().sum()
    for col, n in nulls.items():
        status = "OK" if n == 0 else f"ATENCIÓN: {n} nulos"
        print(f"    {col:<20} {status}")

    if LABEL_COLUMN in df.columns:
        print(f"\n  Clases disponibles ({LABEL_COLUMN}):")
        counts = df[LABEL_COLUMN].value_counts()
        for label, count in counts.items():
            pct = 100 * count / len(df)
            print(f"    {str(label):<25} {count:>6,} muestras  ({pct:.1f}%)")

    print(f"\n  Estadísticas de aceleración:")
    axes_present = [c for c in AXIS_COLUMNS if c in df.columns]
    print(df[axes_present].describe().round(4).to_string())
    print("=" * 55 + "\n")


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpieza básica:
    - Elimina filas con NaN en columnas de ejes
    - Elimina duplicados exactos
    - Convierte columnas de ejes a float32
    - Elimina outliers extremos (más de 5 desviaciones estándar)
    """
    n_original = len(df)

    # 1. Eliminar filas con NaN en columnas necesarias
    required = AXIS_COLUMNS + ([LABEL_COLUMN] if LABEL_COLUMN in df.columns else [])
    axes_present = [c for c in required if c in df.columns]
    df = df.dropna(subset=axes_present)
    n_after_nan = len(df)
    if n_original != n_after_nan:
        print(f"[LIMPIEZA] Eliminadas {n_original - n_after_nan} filas con NaN")

    # 2. Eliminar duplicados exactos
    df = df.drop_duplicates()
    n_after_dup = len(df)
    if n_after_nan != n_after_dup:
        print(f"[LIMPIEZA] Eliminadas {n_after_nan - n_after_dup} filas duplicadas")

    # 3. Convertir ejes a float32 (eficiencia de memoria)
    for col in AXIS_COLUMNS:
        if col in df.columns:
            df[col] = df[col].astype(np.float32)

    # 4. Eliminar outliers (> 5 std) — valores físicamente imposibles
    axes_present = [c for c in AXIS_COLUMNS if c in df.columns]
    for col in axes_present:
        mean = df[col].mean()
        std = df[col].std()
        mask = (df[col] >= mean - 5 * std) & (df[col] <= mean + 5 * std)
        n_out = (~mask).sum()
        if n_out > 0:
            print(f"[LIMPIEZA] {col}: {n_out} outliers eliminados (±5σ)")
        df = df[mask]

    print(
        f"[LIMPIEZA] Dataset final: {len(df):,} filas "
        f"({n_original - len(df):,} eliminadas en total)"
    )
    return df.reset_index(drop=True)


def add_magnitude(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega columna de magnitud total del vector de aceleración.
    magnitude = sqrt(ax² + ay² + az²)
    Útil para detectar el nivel general de actividad.
    """
    axes_present = [c for c in AXIS_COLUMNS if c in df.columns]
    if len(axes_present) == 3:
        df["magnitude"] = np.sqrt(df["ax"] ** 2 + df["ay"] ** 2 + df["az"] ** 2).astype(
            np.float32
        )
    return df


def main(input_file: Path | None = None) -> None:
    # 1. Localizar y cargar archivos CSV
    if input_file is None:
        csv_files = find_csv_files(RAW_DIR)
        df = load_and_combine_csvs(csv_files)
    else:
        print(f"[INFO] Cargando: {input_file}")
        df = pd.read_csv(input_file)
        print(f"[INFO] Filas cargadas: {len(df):,}")

    # 2. Normalizar nombres de columnas
    df = normalize_columns(df)

    # 3. Verificar columnas mínimas necesarias
    missing = [c for c in AXIS_COLUMNS if c not in df.columns]
    if missing:
        print(f"\n[ERROR] Columnas de aceleración no encontradas: {missing}")
        print(f"  Columnas disponibles: {list(df.columns)}")
        print("  Ajusta AXIS_COLUMNS o COLUMN_ALIASES al inicio del script.")
        sys.exit(1)

    # 4. Inspección inicial
    inspect_dataset(df)

    # 5. Limpieza
    df = clean_data(df)

    # 6. Agregar magnitud
    df = add_magnitude(df)

    # 7. Guardar resultado
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\n[OK] Dataset limpio guardado en: {OUTPUT_FILE}")
    print(f"     {len(df):,} filas × {len(df.columns)} columnas")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepara el dataset MPU6050")
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Ruta al CSV de entrada (opcional, auto-detecta desde data/raw/)",
    )
    args = parser.parse_args()
    main(args.input)
