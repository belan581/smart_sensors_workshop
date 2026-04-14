from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db import crud
from app.db.database import get_db
from app.schemas import PredictRequest, PredictResponse, PredictionOut

router = APIRouter()


@router.get(
    "/predictions/{device_id}/latest",
    response_model=PredictionOut,
    summary="Última predicción de un sensor",
)
def latest_prediction(device_id: str, db: Session = Depends(get_db)):
    """Retorna la predicción de movimiento más reciente del dispositivo."""
    prediction = crud.get_latest_prediction(db, device_id)
    if prediction is None:
        raise HTTPException(
            status_code=404, detail=f"No hay predicciones para '{device_id}'"
        )
    result = PredictionOut.model_validate(prediction)
    result.device_id = device_id
    return result


@router.get(
    "/predictions/{device_id}/history",
    response_model=list[PredictionOut],
    summary="Historial de predicciones",
)
def prediction_history(
    device_id: str,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Retorna el historial de predicciones del dispositivo."""
    limit = min(limit, 200)
    predictions = crud.get_prediction_history(db, device_id, limit)
    results = []
    for p in predictions:
        item = PredictionOut.model_validate(p)
        item.device_id = device_id
        results.append(item)
    return results


@router.post(
    "/predict",
    response_model=PredictResponse,
    summary="Inferencia directa por HTTP",
)
def predict_direct(
    payload: PredictRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Ejecuta clasificación de movimiento directamente desde HTTP.
    Útil para pruebas en el taller sin necesitar el ESP32.

    También guarda la medición y predicción en la base de datos.
    """
    ml_service = getattr(request.app.state, "ml_service", None)
    if ml_service is None or not ml_service.is_loaded:
        raise HTTPException(
            status_code=503,
            detail="Modelo ML no disponible. Verifica que el modelo esté en backend/models/",
        )

    if len(payload.ax) != len(payload.ay) or len(payload.ax) != len(payload.az):
        raise HTTPException(
            status_code=422,
            detail="Las listas ax, ay, az deben tener la misma longitud",
        )

    result = ml_service.predict(payload.ax, payload.ay, payload.az)
    if result is None:
        raise HTTPException(status_code=500, detail="Error durante la inferencia")

    # Guardar en base de datos
    sensor = crud.get_or_create_sensor(db, payload.device_id)
    measurement = crud.create_measurement(
        db,
        sensor_id=sensor.id,
        device_timestamp=payload.timestamp,
        ax=payload.ax,
        ay=payload.ay,
        az=payload.az,
        temperature=payload.temperature,
        battery=payload.battery,
    )
    crud.create_prediction(
        db,
        sensor_id=sensor.id,
        measurement_id=measurement.id,
        label=result["label"],
        confidence=result["confidence"],
        all_probabilities=result["all_probabilities"],
    )
    db.commit()

    return PredictResponse(
        device_id=payload.device_id,
        label=result["label"],
        confidence=result["confidence"],
        all_probabilities=result["all_probabilities"],
    )
