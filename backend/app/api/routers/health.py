from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas import HealthOut

router = APIRouter()


@router.get("/health", response_model=HealthOut, summary="Estado del sistema")
def health_check(request: Request, db: Session = Depends(get_db)):
    """
    Verifica el estado de todos los componentes del backend:
    - Conexión MQTT
    - Modelo ML cargado
    - Base de datos accesible
    """
    # Verificar base de datos
    try:
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    # Estado del suscriptor MQTT
    mqtt_sub = getattr(request.app.state, "mqtt_subscriber", None)
    mqtt_connected = mqtt_sub.is_connected if mqtt_sub else False

    # Estado del modelo ML
    ml_service = getattr(request.app.state, "ml_service", None)
    model_loaded = ml_service.is_loaded if ml_service else False

    overall = "ok" if (db_ok and mqtt_connected and model_loaded) else "degraded"

    return HealthOut(
        status=overall,
        mqtt_connected=mqtt_connected,
        model_loaded=model_loaded,
        database_ok=db_ok,
    )
