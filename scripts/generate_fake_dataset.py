#!/usr/bin/env python3
"""
Generador de dataset sintético para entrenar el modelo ML sin hardware real.

Genera ventanas de datos IMU con etiquetas para las 6 clases de movimiento
y las guarda como CSV en ml/data/raw/synthetic_dataset.csv

Uso:
    python scripts/generate_fake_dataset.py
    python scripts/generate_fake_dataset.py --samples-per-class 300

El archivo generado tiene exactamente las mismas columnas que el dataset
real esperado por ml/scripts/01_prepare_data.py:
    label, ax_0..ax_49, ay_0..ay_49, az_0..az_49
"""

import argparse
import math
import random
import sys
from pathlib import Path

try:
    import pandas as pd
    import numpy as np
except ImportError:
    print("[ERROR] Instalar dependencias ML:  pip install pandas numpy")
    raise SystemExit(1)

# Importar generadores del simulador
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from simulate_esp32 import (
    gen_reposo,
    gen_vibracion,
    gen_golpe,
    gen_rotacion,
    gen_libre,
    gen_random,
    WINDOW_SIZE,
)

GENERATORS = {
    "reposo": gen_reposo,
    "vibracion": gen_vibracion,
    "golpe": gen_golpe,
    "rotacion": gen_rotacion,
    "libre": gen_libre,
    "random": gen_random,
}

OUTPUT_DIR = SCRIPTS.parent / "ml" / "data" / "raw"


def generate_dataset(samples_per_class: int, seed: int) -> pd.DataFrame:
    random.seed(seed)
    np.random.seed(seed)

    rows = []
    for label, gen in GENERATORS.items():
        for _ in range(samples_per_class):
            ax, ay, az = gen()
            row = {"label": label}
            for i, (a, b, c) in enumerate(zip(ax, ay, az)):
                row[f"ax_{i}"] = round(a, 4)
                row[f"ay_{i}"] = round(b, 4)
                row[f"az_{i}"] = round(c, 4)
            rows.append(row)

    df = pd.DataFrame(rows).sample(frac=1, random_state=seed).reset_index(drop=True)
    return df


def main():
    parser = argparse.ArgumentParser(
        description="Genera dataset sintético para entrenar"
    )
    parser.add_argument(
        "--samples-per-class",
        type=int,
        default=200,
        help="Muestras por clase (default: 200)",
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_file = OUTPUT_DIR / "synthetic_dataset.csv"

    print(f"Generando dataset sintético...")
    print(f"  Clases: {list(GENERATORS)}")
    print(f"  Muestras por clase: {args.samples_per_class}")

    df = generate_dataset(args.samples_per_class, args.seed)

    df.to_csv(out_file, index=False)

    print(f"\n  Total muestras: {len(df)}")
    print(f"  Columnas: {len(df.columns)}")
    print(f"  Guardado en: {out_file}")
    print(f"\nDistribución de clases:")
    print(df["label"].value_counts().to_string())
    print(f"\nPróximo paso:")
    print(f"  cd ml")
    print(f"  python scripts/02_extract_features.py")
    print(f"  python scripts/03_train.py")


if __name__ == "__main__":
    main()
