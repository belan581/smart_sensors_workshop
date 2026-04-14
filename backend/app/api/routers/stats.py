from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import crud
from app.db.database import get_db
from app.schemas import StatsOut

router = APIRouter()


@router.get("/stats", response_model=StatsOut, summary="Estadísticas globales")
def global_stats(db: Session = Depends(get_db)):
    """
    Retorna estadísticas globales del sistema:
    - Total de dispositivos registrados
    - Total de mediciones almacenadas
    - Total de predicciones realizadas
    - Distribución de etiquetas de movimiento
    """
    return crud.get_global_stats(db)
