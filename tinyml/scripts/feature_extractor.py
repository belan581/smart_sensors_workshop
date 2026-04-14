"""
Módulo compartido: extractor de features del pipeline ML.

Este archivo es importado tanto por los scripts de entrenamiento
como por el backend durante la inferencia.

Uso:
    from feature_extractor import extract_features_from_window

    features_dict = extract_features_from_window(ax_list, ay_list, az_list)
    feature_vector = list(features_dict.values())  # para el modelo
"""

import numpy as np


AXIS_NAMES = ["ax", "ay", "az"]


def extract_features_from_window(
    ax: list | np.ndarray,
    ay: list | np.ndarray,
    az: list | np.ndarray,
) -> dict:
    """
    Calcula las features estadísticas de una ventana de aceleración.

    Args:
        ax: Lista o array de muestras de aceleración en X
        ay: Lista o array de muestras de aceleración en Y
        az: Lista o array de muestras de aceleración en Z

    Returns:
        Diccionario ordenado {nombre_feature: valor_float}
        Listo para construir el vector de entrada al modelo.

    Features (25 en total):
        Por eje (×3): mean, std, min, max, range, rms, energy  → 21
        De magnitud : magnitude_mean, magnitude_std, magnitude_max → 3
        Global      : zcr_ax → 1
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

    # Magnitud del vector 3D
    magnitude = np.sqrt(ax_a**2 + ay_a**2 + az_a**2)
    features["magnitude_mean"] = float(np.mean(magnitude))
    features["magnitude_std"] = float(np.std(magnitude))
    features["magnitude_max"] = float(np.max(magnitude))

    # Tasa de cruces por cero en ax (detecta oscilaciones periódicas)
    centered = ax_a - ax_a.mean()
    crossings = np.where(np.diff(np.sign(centered)))[0]
    features["zcr_ax"] = float(len(crossings) / len(ax_a))

    return features


def feature_vector(ax, ay, az) -> list[float]:
    """
    Retorna la lista de valores (sin nombres) para pasar directo al modelo.
    El orden es el mismo que el usado durante el entrenamiento.
    """
    return list(extract_features_from_window(ax, ay, az).values())


def feature_names() -> list[str]:
    """Retorna los nombres de todas las features en el mismo orden."""
    dummy = np.zeros(10)
    return list(extract_features_from_window(dummy, dummy, dummy).keys())
