from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import crud
from app.db.database import get_db
from app.schemas import MeasurementOut, SensorOut

router = APIRouter()


@router.get("/sensors", response_model=list[SensorOut], summary="Lista de sensores")
def list_sensors(db: Session = Depends(get_db)):
    """Retorna todos los dispositivos ESP32 registrados."""
    return crud.get_all_sensors(db)


@router.get(
    "/sensors/{device_id}/latest",
    response_model=MeasurementOut,
    summary="Última medición de un sensor",
)
def latest_measurement(device_id: str, db: Session = Depends(get_db)):
    """Retorna la medición más reciente del dispositivo indicado."""
    measurement = crud.get_latest_measurement(db, device_id)
    if measurement is None:
        raise HTTPException(
            status_code=404, detail=f"No se encontraron mediciones para '{device_id}'"
        )
    # Inyectar device_id en la respuesta
    result = MeasurementOut.model_validate(measurement)
    result.device_id = device_id
    return result


@router.get(
    "/sensors/{device_id}/history",
    response_model=list[MeasurementOut],
    summary="Historial de mediciones",
)
def measurement_history(
    device_id: str,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    Retorna las últimas N mediciones del dispositivo.
    Parámetro `limit` (default: 50, máximo recomendado: 200).
    """
    limit = min(limit, 200)  # Limitar para evitar respuestas excesivamente grandes
    measurements = crud.get_measurement_history(db, device_id, limit)
    results = []
    for m in measurements:
        item = MeasurementOut.model_validate(m)
        item.device_id = device_id
        results.append(item)
    return results
