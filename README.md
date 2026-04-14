# Smart Sensors Workshop
## Sensores inteligentes, IA en sistemas embebidos y emulación IIoT

Taller de 2 días para estudiantes principiantes de robótica.

### Stack del sistema

| Capa | Tecnología |
|------|-----------|
| Dispositivo | ESP32-S3 + MPU6050 + ESP-IDF |
| Mensajería | MQTT (Mosquitto local) |
| Backend | Python + FastAPI + paho-mqtt |
| Base de datos | SQLite (via SQLAlchemy) |
| ML | scikit-learn (RandomForest / MLP) |
| Descubrimiento | mDNS (`mqtt.local`) |

### Estructura del repositorio

```
smart_sensors_workshop/
├── firmware/          → Proyecto ESP-IDF para ESP32-S3
├── backend/           → Servidor FastAPI + suscriptor MQTT + inferencia
├── ml/                → Pipeline de entrenamiento del modelo
├── config/            → Configuración compartida (broker, red, etc.)
└── docs/              → Documentación del taller
```

### Inicio rápido

1. Entrenar modelo: `cd ml && python scripts/train.py`
2. Levantar backend: `cd backend && uvicorn app.main:app --reload`
3. Flashear firmware: `cd firmware && idf.py flash monitor`
4. Explorar API: http://localhost:8000/docs

Ver README de cada subcarpeta para instrucciones detalladas.
