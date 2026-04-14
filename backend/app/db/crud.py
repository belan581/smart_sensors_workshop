"""
Operaciones CRUD reutilizables sobre la base de datos.
Cada función recibe una sesión SQLAlchemy y retorna objetos ORM.
"""

from datetime import datetime

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.db.models import Measurement, Prediction, Sensor


# ── Sensors ──────────────────────────────────────────────────────────────────


def get_or_create_sensor(db: Session, device_id: str) -> Sensor:
    """Retorna el sensor existente o crea uno nuevo."""
    sensor = db.query(Sensor).filter(Sensor.device_id == device_id).first()
    if sensor is None:
        sensor = Sensor(device_id=device_id)
        db.add(sensor)
        db.flush()  # para obtener el id sin commit aún
    else:
        sensor.last_seen = datetime.utcnow()
    return sensor


def get_all_sensors(db: Session) -> list[Sensor]:
    return db.query(Sensor).order_by(Sensor.last_seen.desc()).all()


def get_sensor_by_device_id(db: Session, device_id: str) -> Sensor | None:
    return db.query(Sensor).filter(Sensor.device_id == device_id).first()


# ── Measurements ─────────────────────────────────────────────────────────────


def create_measurement(
    db: Session,
    sensor_id: int,
    device_timestamp: int | None,
    ax: list[float],
    ay: list[float],
    az: list[float],
    temperature: float | None = None,
    battery: int | None = None,
) -> Measurement:
    """Inserta una nueva medición y retorna el objeto creado."""
    measurement = Measurement(
        sensor_id=sensor_id,
        device_timestamp=device_timestamp,
        ax=ax,
        ay=ay,
        az=az,
        temperature=temperature,
        battery=battery,
    )
    db.add(measurement)
    db.flush()
    return measurement


def get_latest_measurement(db: Session, device_id: str) -> Measurement | None:
    sensor = get_sensor_by_device_id(db, device_id)
    if sensor is None:
        return None
    return (
        db.query(Measurement)
        .filter(Measurement.sensor_id == sensor.id)
        .order_by(desc(Measurement.received_at))
        .first()
    )


def get_measurement_history(
    db: Session, device_id: str, limit: int = 100
) -> list[Measurement]:
    sensor = get_sensor_by_device_id(db, device_id)
    if sensor is None:
        return []
    return (
        db.query(Measurement)
        .filter(Measurement.sensor_id == sensor.id)
        .order_by(desc(Measurement.received_at))
        .limit(limit)
        .all()
    )


# ── Predictions ──────────────────────────────────────────────────────────────


def create_prediction(
    db: Session,
    sensor_id: int,
    measurement_id: int,
    label: str,
    confidence: float,
    all_probabilities: dict,
) -> Prediction:
    prediction = Prediction(
        sensor_id=sensor_id,
        measurement_id=measurement_id,
        label=label,
        confidence=confidence,
        all_probabilities=all_probabilities,
    )
    db.add(prediction)
    db.flush()
    return prediction


def get_latest_prediction(db: Session, device_id: str) -> Prediction | None:
    sensor = get_sensor_by_device_id(db, device_id)
    if sensor is None:
        return None
    return (
        db.query(Prediction)
        .filter(Prediction.sensor_id == sensor.id)
        .order_by(desc(Prediction.predicted_at))
        .first()
    )


def get_prediction_history(
    db: Session, device_id: str, limit: int = 50
) -> list[Prediction]:
    sensor = get_sensor_by_device_id(db, device_id)
    if sensor is None:
        return []
    return (
        db.query(Prediction)
        .filter(Prediction.sensor_id == sensor.id)
        .order_by(desc(Prediction.predicted_at))
        .limit(limit)
        .all()
    )


# ── Stats ────────────────────────────────────────────────────────────────────


def get_global_stats(db: Session) -> dict:
    """Retorna estadísticas globales del sistema."""
    total_sensors = db.query(func.count(Sensor.id)).scalar() or 0
    total_measurements = db.query(func.count(Measurement.id)).scalar() or 0
    total_predictions = db.query(func.count(Prediction.id)).scalar() or 0

    # Distribución de clases predichas
    label_counts = (
        db.query(Prediction.label, func.count(Prediction.id).label("count"))
        .group_by(Prediction.label)
        .order_by(desc("count"))
        .all()
    )

    return {
        "total_sensors": total_sensors,
        "total_measurements": total_measurements,
        "total_predictions": total_predictions,
        "label_distribution": {row.label: row.count for row in label_counts},
    }
