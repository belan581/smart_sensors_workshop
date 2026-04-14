# Backend - Smart Sensors Workshop

Servidor Python que:
- Se suscribe al broker MQTT local
- Almacena mediciones en SQLite
- Ejecuta inferencia con modelo entrenado
- Expone API REST con FastAPI

## Estructura

```
backend/
├── app/
│   ├── main.py               → Punto de entrada: FastAPI + MQTT thread
│   ├── config.py             → Configuración desde variables de entorno
│   ├── api/
│   │   ├── __init__.py
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── health.py     → GET /health
│   │       ├── sensors.py    → GET /sensors, /sensors/{id}/latest, /history
│   │       ├── predictions.py→ GET /predictions/{id}/latest, POST /predict
│   │       └── stats.py      → GET /stats
│   ├── core/
│   │   ├── __init__.py
│   │   └── mqtt_subscriber.py→ Hilo MQTT, dispatcher de mensajes
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py       → Engine SQLAlchemy, SessionLocal
│   │   ├── models.py         → Tablas ORM (Sensor, Measurement, Prediction)
│   │   └── crud.py           → Operaciones CRUD reutilizables
│   ├── ml/
│   │   ├── __init__.py
│   │   ├── feature_extractor.py → Cálculo de features por ventana
│   │   └── ml_service.py    → Carga modelo, ejecuta predict
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── schemas.py        → Modelos Pydantic de request/response
│   └── services/
│       ├── __init__.py
│       └── data_processor.py → Orquesta MQTT → features → DB → predicción
├── models/                   → Archivos .pkl del modelo entrenado
├── data/                     → SQLite database file
├── requirements.txt
├── .env.example
└── README.md
```

## Instalación

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

## Configuración

Copiar `.env.example` a `.env` y ajustar valores:

```bash
copy .env.example .env
```

## Correr el servidor

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Documentación interactiva: http://localhost:8000/docs
