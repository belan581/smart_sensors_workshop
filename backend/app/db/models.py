"""
Modelos ORM — definen las tablas de la base de datos.

Tablas:
  - sensors     → dispositivos registrados
  - measurements → ventanas de datos crudos recibidas
  - predictions  → resultado de inferencia por ventana
"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Sensor(Base):
    """
    Dispositivo ESP32 registrado en el sistema.
    Se crea automáticamente al recibir el primer mensaje MQTT de un device_id nuevo.
    """

    __tablename__ = "sensors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    first_seen: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=func.now()
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relaciones
    measurements: Mapped[list["Measurement"]] = relationship(
        back_populates="sensor", cascade="all, delete-orphan"
    )
    predictions: Mapped[list["Prediction"]] = relationship(
        back_populates="sensor", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Sensor device_id={self.device_id}>"


class Measurement(Base):
    """
    Ventana de datos crudos recibida desde el ESP32.
    Almacena las listas de ax/ay/az como JSON.
    """

    __tablename__ = "measurements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sensor_id: Mapped[int] = mapped_column(ForeignKey("sensors.id"), index=True)

    # Timestamp del dispositivo (Unix epoch enviado por ESP32)
    device_timestamp: Mapped[int] = mapped_column(Integer, nullable=True)
    # Timestamp del servidor al recibir el mensaje
    received_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=func.now()
    )

    # Datos del sensor
    ax: Mapped[str] = mapped_column(JSON)  # lista de floats
    ay: Mapped[str] = mapped_column(JSON)
    az: Mapped[str] = mapped_column(JSON)
    temperature: Mapped[float] = mapped_column(Float, nullable=True)
    battery: Mapped[int] = mapped_column(Integer, nullable=True)

    # Relaciones
    sensor: Mapped["Sensor"] = relationship(back_populates="measurements")
    prediction: Mapped["Prediction"] = relationship(
        back_populates="measurement", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Measurement id={self.id} sensor_id={self.sensor_id}>"


class Prediction(Base):
    """
    Resultado de clasificación de movimiento para una ventana.
    """

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sensor_id: Mapped[int] = mapped_column(ForeignKey("sensors.id"), index=True)
    measurement_id: Mapped[int] = mapped_column(
        ForeignKey("measurements.id"), unique=True, index=True
    )

    predicted_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=func.now()
    )

    # Resultado de la inferencia
    label: Mapped[str] = mapped_column(String(64))  # "walking", "running", etc.
    confidence: Mapped[float] = mapped_column(
        Float
    )  # probabilidad de la clase ganadora
    all_probabilities: Mapped[str] = mapped_column(
        JSON
    )  # {"walking": 0.85, "running": 0.12}

    # Relaciones
    sensor: Mapped["Sensor"] = relationship(back_populates="predictions")
    measurement: Mapped["Measurement"] = relationship(back_populates="prediction")

    def __repr__(self) -> str:
        return f"<Prediction label={self.label} confidence={self.confidence:.2f}>"
