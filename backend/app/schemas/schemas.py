"""
Esquemas Pydantic — contratos de entrada/salida de la API.

Separados de los modelos ORM para desacoplar la capa de presentación
de la capa de base de datos.
"""

from datetime import datetime

from pydantic import BaseModel, Field


# ── Sensor ───────────────────────────────────────────────────────────────────


class SensorOut(BaseModel):
    id: int
    device_id: str
    first_seen: datetime
    last_seen: datetime

    model_config = {"from_attributes": True}


# ── Measurement ──────────────────────────────────────────────────────────────


class MeasurementOut(BaseModel):
    id: int
    device_id: str = ""  # se llena en el router desde el sensor
    device_timestamp: int | None
    received_at: datetime
    ax: list[float]
    ay: list[float]
    az: list[float]
    temperature: float | None
    battery: int | None

    model_config = {"from_attributes": True}


# ── Prediction ───────────────────────────────────────────────────────────────


class PredictionOut(BaseModel):
    id: int
    device_id: str = ""
    label: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    all_probabilities: dict[str, float]
    predicted_at: datetime

    model_config = {"from_attributes": True}


# ── POST /predict — inferencia directa ───────────────────────────────────────


class PredictRequest(BaseModel):
    """
    Payload para invocar la inferencia directamente por HTTP,
    sin pasar por MQTT. Útil para pruebas en el taller.
    """

    device_id: str = Field(..., example="esp32s3_001")
    ax: list[float] = Field(..., min_length=10, max_length=500)
    ay: list[float] = Field(..., min_length=10, max_length=500)
    az: list[float] = Field(..., min_length=10, max_length=500)
    timestamp: int | None = Field(None, example=1712345678)
    temperature: float | None = None
    battery: int | None = None


class PredictResponse(BaseModel):
    device_id: str
    label: str
    confidence: float
    all_probabilities: dict[str, float]


# ── Stats ─────────────────────────────────────────────────────────────────────


class StatsOut(BaseModel):
    total_sensors: int
    total_measurements: int
    total_predictions: int
    label_distribution: dict[str, int]


# ── Health ────────────────────────────────────────────────────────────────────


class HealthOut(BaseModel):
    status: str
    mqtt_connected: bool
    model_loaded: bool
    database_ok: bool
    version: str = "1.0.0"
