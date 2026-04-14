# Guía de Integración — Smart Sensors Workshop

Esta guía resume cómo arrancar el sistema completo paso a paso,
tanto con el ESP32 físico como sin él (usando el simulador).

---

## Requisitos previos

| Herramienta | Versión mínima | Instalación |
|-------------|-------------|-------------|
| Python      | 3.11        | https://python.org |
| Mosquitto   | 2.x         | https://mosquitto.org/download/ |
| ESP-IDF     | v5.0+       | https://esp-idf.readthedocs.io (solo para firmware) |

---

## Flujo completo del sistema

```
ESP32-S3 ──► MQTT (1883) ──► FastAPI Backend ──► SQLite DB
(sensor_manager)  (broker)   (mqtt_subscriber)   (SQLAlchemy)
                                    │
                               ML Service
                           (RandomForest .pkl)
                                    │
                             Predicción guardada
                                    │
                         GET /predictions/latest
```

---

## Pasos de arranque

### Terminal 0 (una sola vez — setup inicial)

```powershell
cd C:\Users\belan\desarrollos\esp32_s3\smart_sensors_workshop

# Crear entorno virtual e instalar paquetes
.\scripts\setup_env.ps1 -IncludeML

# Entrenar modelo con datos sintéticos y copiar al backend
.\scripts\train_model.ps1 -Synthetic -Copy
```

### Terminal 1 — Broker MQTT

```powershell
.\scripts\start_broker.ps1
```

Verás líneas como:
```
1712345678: mosquitto version 2.0.x starting
1712345678: Opening ipv4 listen socket on port 1883.
```

### Terminal 2 — Backend FastAPI

```powershell
.\scripts\start_backend.ps1
```

Swagger UI: http://localhost:8000/docs  
Health check: http://localhost:8000/health

### Terminal 3 — Simulador ESP32 (si no tienes hardware)

```powershell
# Simular 20 ventanas de vibración
python scripts\simulate_esp32.py --motion vibracion --count 20

# Alternar entre todos los movimientos automáticamente
python scripts\simulate_esp32.py --motion auto --rate 2.0

# Ver todos los perfiles disponibles
python scripts\simulate_esp32.py --list-motions
```

### Verificación del sistema

```powershell
# Verificar todos los componentes
python scripts\check_integration.py

# Prueba end-to-end completa
python scripts\test_pipeline.py --send-mqtt
```

---

## Endpoints del API

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET  | `/health` | Estado del sistema (MQTT, BD, modelo) |
| GET  | `/sensors` | Lista de dispositivos registrados |
| GET  | `/sensors/{device_id}/latest` | Última medición de un dispositivo |
| GET  | `/predictions/latest` | Últimas predicciones (todos los dispositivos) |
| GET  | `/predictions/{device_id}/history` | Historial de predicciones por dispositivo |
| POST | `/predict` | Inferencia directa sin pasar por MQTT |
| GET  | `/stats` | Estadísticas globales |

### Ejemplo POST /predict

```bash
curl -X POST http://localhost:8000/predict ^
  -H "Content-Type: application/json" ^
  -d "{\"device_id\":\"test\",\"ax\":[...50 valores...],\"ay\":[...],\"az\":[...]}"
```

O via Swagger UI en http://localhost:8000/docs

---

## Estructura del payload MQTT

El firmware (y el simulador) publican en el topic `sensors/{device_id}/raw`:

```json
{
  "device_id": "esp32s3_001",
  "timestamp": 1712345678,
  "ax": [0.12, -0.08, ...],
  "ay": [9.75, 9.82, ...],
  "az": [0.05, -0.03, ...],
  "temperature": 28.5,
  "battery": 95
}
```

- `ax`, `ay`, `az`: exactamente **50 valores** en m/s² (una ventana de 0.5 s a 100 Hz)
- `timestamp`: Unix epoch en segundos
- `temperature` y `battery`: opcionales, guardados en la BD

---

## Clases del modelo

| Etiqueta   | Descripción |
|-----------|-------------|
| reposo    | Dispositivo quieto |
| vibracion | Motor/maquinaria |
| golpe     | Impacto brusco |
| rotacion  | Rotación continua |
| libre     | Caída libre |
| random    | Señal no clasificable |

---

## Solución de problemas

### "No se pudo conectar a localhost:1883"
- Mosquitto no está corriendo → ejecutar `.\scripts\start_broker.ps1`
- Puerto bloqueado por firewall → agregar regla de entrada para puerto 1883

### "model_loaded = false" en /health
- Faltan archivos .pkl en `backend/models/`
- Ejecutar: `.\scripts\copy_models.ps1`

### "mqtt_connected = false" en /health
- El backend arrancó antes que Mosquitto
- El backend reintentará automáticamente cada 5 s

### Error de CORS accediendo desde el navegador
- Verificar que el frontend use `http://` (no `https://`) para localhost
- CORS está configurado con `allow_origins=["*"]` para el taller

### ESP32 no conecta por WiFi
- Usar BluFi (app ESP BLE Provisioning) para configurar las credenciales
- Si mDNS falla, editar `wifi_manager.c` y cambiar la IP fallback

---

## Secuencia completa del taller (demo rápida)

```powershell
# Ventana 1: Broker
.\scripts\start_broker.ps1

# Ventana 2: Backend
.\scripts\start_backend.ps1

# Ventana 3: Simulador
python scripts\simulate_esp32.py --motion vibracion --count 10

# Ventana 4: Verificar
python scripts\test_pipeline.py
```

Abrir http://localhost:8000/docs en el navegador para ver las predicciones en tiempo real.
