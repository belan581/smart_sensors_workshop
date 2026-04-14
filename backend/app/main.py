"""
Punto de entrada del backend.

Inicia:
  1. FastAPI con todos los routers registrados
  2. Hilo de suscripción MQTT (en segundo plano)
  3. Crea las tablas de base de datos si no existen

Correr con:
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"""

import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import health, predictions, sensors, stats
from app.config import settings
from app.core.mqtt_subscriber import MQTTSubscriber
from app.db.database import create_tables
from app.ml.ml_service import MLService

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Ciclo de vida de la aplicación ───────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Se ejecuta al arrancar (yield) y al apagar (después del yield).
    Reemplaza el antiguo @app.on_event("startup").
    """
    logger.info("=== Iniciando Smart Sensors Backend ===")

    # 1. Crear tablas en la base de datos
    create_tables()
    logger.info("Base de datos lista")

    # 2. Cargar modelo ML
    ml_service = MLService()
    ml_loaded = ml_service.load_model()
    if ml_loaded:
        logger.info("Modelo ML cargado correctamente")
    else:
        logger.warning("Modelo ML no encontrado — inferencia deshabilitada")
        logger.warning("  Ejecuta: python ml/scripts/03_train.py")
        logger.warning("  Luego copia los .pkl a backend/models/")

    # Hacer el servicio accesible globalmente vía app.state
    app.state.ml_service = ml_service

    # 3. Iniciar suscriptor MQTT en hilo separado
    subscriber = MQTTSubscriber(ml_service=ml_service)
    mqtt_thread = threading.Thread(
        target=subscriber.start,
        daemon=True,  # El hilo se cierra cuando el proceso principal termina
        name="mqtt-subscriber",
    )
    mqtt_thread.start()
    app.state.mqtt_subscriber = subscriber
    logger.info(
        f"Suscriptor MQTT iniciado → {settings.mqtt_broker_host}:{settings.mqtt_broker_port}"
    )

    logger.info(f"API lista en http://{settings.api_host}:{settings.api_port}")
    logger.info(f"Documentación: http://localhost:{settings.api_port}/docs")

    yield  # ← La aplicación corre aquí

    # Apagado limpio
    logger.info("Cerrando backend...")
    subscriber.stop()


# ── Aplicación FastAPI ────────────────────────────────────────────────────────
app = FastAPI(
    title="Smart Sensors Workshop API",
    description=(
        "Backend IoT para clasificación de movimiento con MPU6050.\n\n"
        "Recibe datos de sensores ESP32 vía MQTT, almacena en SQLite "
        "y clasifica movimiento con un modelo RandomForest."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — permite que cualquier cliente en la red local acceda a la API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción real: lista de orígenes específicos
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Registro de routers ───────────────────────────────────────────────────────
app.include_router(health.router, tags=["Sistema"])
app.include_router(sensors.router, tags=["Sensores"])
app.include_router(predictions.router, tags=["Predicciones"])
app.include_router(stats.router, tags=["Estadísticas"])
