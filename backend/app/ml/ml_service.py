"""
Servicio de inferencia ML.

Responsabilidades:
  - Cargar el modelo, scaler y label encoder desde disco
  - Ejecutar predicción sobre un vector de features
  - Retornar la etiqueta, confianza y todas las probabilidades
"""

import logging
from pathlib import Path

import joblib
import numpy as np

from app.config import settings
from app.ml.feature_extractor import feature_vector

logger = logging.getLogger(__name__)


class MLService:
    """Servicio de clasificación de movimiento."""

    def __init__(self):
        self.model = None
        self.scaler = None
        self.label_encoder = None
        self._loaded = False

    def load_model(self) -> bool:
        """
        Carga modelo, scaler y label encoder desde los paths configurados.
        Retorna True si cargó correctamente.
        """
        model_path = Path(settings.model_path)
        scaler_path = Path(settings.scaler_path)
        le_path = Path(settings.label_encoder_path)

        missing = [p for p in [model_path, scaler_path, le_path] if not p.exists()]
        if missing:
            logger.warning(
                f"Archivos de modelo no encontrados: {[str(p) for p in missing]}"
            )
            return False

        try:
            self.model = joblib.load(model_path)
            self.scaler = joblib.load(scaler_path)
            self.label_encoder = joblib.load(le_path)
            self._loaded = True
            logger.info(
                f"Modelo cargado: {model_path.name} | "
                f"Clases: {list(self.label_encoder.classes_)}"
            )
            return True
        except Exception as e:
            logger.error(f"Error al cargar modelo: {e}")
            return False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def predict(
        self,
        ax: list[float],
        ay: list[float],
        az: list[float],
    ) -> dict | None:
        """
        Ejecuta inferencia sobre una ventana de aceleración.

        Args:
            ax, ay, az: Listas de muestras de la ventana

        Returns:
            {
                "label": "walking",
                "confidence": 0.87,
                "all_probabilities": {"walking": 0.87, "running": 0.10, ...}
            }
            O None si el modelo no está cargado.
        """
        if not self._loaded:
            logger.warning("Inferencia solicitada pero el modelo no está cargado")
            return None

        if len(ax) < 5 or len(ay) < 5 or len(az) < 5:
            logger.warning(f"Ventana demasiado corta: {len(ax)} muestras")
            return None

        try:
            # 1. Extraer features
            features = feature_vector(ax, ay, az)
            X = np.array(features, dtype=np.float32).reshape(1, -1)

            # 2. Escalar (necesario si el modelo fue entrenado con StandardScaler)
            #    Para RandomForest la escala no afecta, pero mantenemos consistencia
            X_scaled = self.scaler.transform(X)

            # 3. Predicción
            label_idx = self.model.predict(X_scaled)[0]
            label = self.label_encoder.inverse_transform([label_idx])[0]

            # 4. Probabilidades por clase
            if hasattr(self.model, "predict_proba"):
                probas = self.model.predict_proba(X_scaled)[0]
                all_probs = {
                    self.label_encoder.inverse_transform([i])[0]: float(p)
                    for i, p in enumerate(probas)
                }
                confidence = float(probas[label_idx])
            else:
                # Fallback si el modelo no tiene predict_proba
                all_probs = {label: 1.0}
                confidence = 1.0

            return {
                "label": str(label),
                "confidence": confidence,
                "all_probabilities": all_probs,
            }

        except Exception as e:
            logger.error(f"Error en inferencia: {e}", exc_info=True)
            return None
