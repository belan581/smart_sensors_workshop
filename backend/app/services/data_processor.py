"""
Orquestador del flujo de datos MQTT → features → DB → predicción.

Este servicio recibe un payload parseado y ejecuta la cadena completa:
  1. Registrar/actualizar el sensor en la DB
  2. Guardar la medición cruda
  3. Extraer features de la ventana
  4. Ejecutar inferencia
  5. Guardar la predicción

Toda la lógica de negocio vive aquí, no en los callbacks MQTT ni en los routers.
"""

import logging

from app.db import crud
from app.db.database import SessionLocal
from app.ml.ml_service import MLService

logger = logging.getLogger(__name__)

# Claves esperadas en el payload JSON del ESP32
REQUIRED_KEYS = {"ax", "ay", "az"}


class DataProcessor:
    """Procesa un payload MQTT y lo persiste con su predicción."""

    def __init__(self, ml_service: MLService):
        self._ml = ml_service

    def process(self, device_id: str, payload: dict) -> None:
        """
        Procesa un mensaje MQTT completo.

        Payload esperado:
        {
            "device_id": "esp32s3_001",   (puede diferir del topic, se usa el del topic)
            "timestamp": 1712345678,
            "ax": [0.1, 0.2, ...],        (lista de floats, N muestras)
            "ay": [...],
            "az": [...],
            "temperature": 28.5,          (opcional)
            "battery": 92                 (opcional)
        }
        """
        # 1. Validar claves mínimas
        missing = REQUIRED_KEYS - set(payload.keys())
        if missing:
            logger.warning(
                f"[Processor] Payload de '{device_id}' incompleto. "
                f"Claves faltantes: {missing}"
            )
            return

        ax = payload["ax"]
        ay = payload["ay"]
        az = payload["az"]

        # 2. Validar que son listas no vacías de igual longitud
        if not (isinstance(ax, list) and isinstance(ay, list) and isinstance(az, list)):
            logger.warning(
                f"[Processor] ax/ay/az deben ser listas. Device: {device_id}"
            )
            return

        if not (len(ax) == len(ay) == len(az)) or len(ax) == 0:
            logger.warning(
                f"[Processor] Longitudes inconsistentes o vacías. "
                f"ax={len(ax)} ay={len(ay)} az={len(az)}"
            )
            return

        # 3. Persistir y predecir dentro de una transacción
        db = SessionLocal()
        try:
            # Registrar sensor (crea si no existe, actualiza last_seen si existe)
            sensor = crud.get_or_create_sensor(db, device_id)

            # Guardar medición
            measurement = crud.create_measurement(
                db,
                sensor_id=sensor.id,
                device_timestamp=payload.get("timestamp"),
                ax=ax,
                ay=ay,
                az=az,
                temperature=payload.get("temperature"),
                battery=payload.get("battery"),
            )

            # Ejecutar inferencia
            prediction_result = self._ml.predict(ax, ay, az)

            if prediction_result is not None:
                crud.create_prediction(
                    db,
                    sensor_id=sensor.id,
                    measurement_id=measurement.id,
                    label=prediction_result["label"],
                    confidence=prediction_result["confidence"],
                    all_probabilities=prediction_result["all_probabilities"],
                )
                logger.info(
                    f"[Processor] {device_id} → "
                    f"{prediction_result['label']} "
                    f"({prediction_result['confidence']:.0%}) | "
                    f"ventana: {len(ax)} muestras"
                )
            else:
                logger.info(
                    f"[Processor] Medición de '{device_id}' guardada "
                    f"(sin predicción — modelo no disponible)"
                )

            db.commit()

        except Exception as e:
            db.rollback()
            logger.error(
                f"[Processor] Error al procesar mensaje de '{device_id}': {e}",
                exc_info=True,
            )
        finally:
            db.close()
