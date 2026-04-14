"""
Extracción de features estadísticas por ventana de aceleración.

Este módulo es idéntico en lógica al de ml/scripts/feature_extractor.py.
Está duplicado aquí para que el backend no dependa del directorio ml/.
"""

import numpy as np

AXIS_NAMES = ["ax", "ay", "az"]


def extract_features_from_window(
    ax: list | np.ndarray,
    ay: list | np.ndarray,
    az: list | np.ndarray,
) -> dict:
    """
    Calcula 25 features estadísticas de una ventana de aceleración.

    Args:
        ax, ay, az: Listas o arrays con las muestras del eje correspondiente.

    Returns:
        Dict ordenado {nombre_feature: valor_float}.
        El orden es el mismo que el usado durante el entrenamiento.
    """
    ax_a = np.asarray(ax, dtype=np.float64)
    ay_a = np.asarray(ay, dtype=np.float64)
    az_a = np.asarray(az, dtype=np.float64)

    features = {}

    for name, vals in zip(AXIS_NAMES, [ax_a, ay_a, az_a]):
        features[f"{name}_mean"] = float(np.mean(vals))
        features[f"{name}_std"] = float(np.std(vals))
        features[f"{name}_min"] = float(np.min(vals))
        features[f"{name}_max"] = float(np.max(vals))
        features[f"{name}_range"] = float(np.max(vals) - np.min(vals))
        features[f"{name}_rms"] = float(np.sqrt(np.mean(vals**2)))
        features[f"{name}_energy"] = float(np.sum(vals**2) / len(vals))

    magnitude = np.sqrt(ax_a**2 + ay_a**2 + az_a**2)
    features["magnitude_mean"] = float(np.mean(magnitude))
    features["magnitude_std"] = float(np.std(magnitude))
    features["magnitude_max"] = float(np.max(magnitude))

    centered = ax_a - ax_a.mean()
    crossings = np.where(np.diff(np.sign(centered)))[0]
    features["zcr_ax"] = float(len(crossings) / len(ax_a))

    return features


def feature_vector(ax, ay, az) -> list[float]:
    """Retorna la lista de valores (sin nombres) para el modelo."""
    return list(extract_features_from_window(ax, ay, az).values())
