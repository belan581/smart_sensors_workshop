# Firmware - Smart Sensors Workshop

Firmware ESP-IDF para ESP32-S3 con MPU6050.

## Estructura

```
firmware/
├── main/
│   ├── CMakeLists.txt
│   ├── idf_component.yml     → Dependencias de componentes
│   └── app_main.c            → Punto de entrada, inicialización, tasks
├── components/
│   ├── wifi_manager/
│   │   ├── CMakeLists.txt
│   │   ├── wifi_manager.h
│   │   └── wifi_manager.c    → Provisioning BluFi/BLE + reconexión WiFi
│   ├── sensor_manager/
│   │   ├── CMakeLists.txt
│   │   ├── sensor_manager.h
│   │   └── sensor_manager.c  → Init I2C, lectura MPU6050, ventanas
│   ├── mqtt_client_manager/
│   │   ├── CMakeLists.txt
│   │   ├── mqtt_client_manager.h
│   │   └── mqtt_client_manager.c → Conexión MQTT, publish, reconnect
│   └── http_diag_server/
│       ├── CMakeLists.txt
│       ├── http_diag_server.h
│       └── http_diag_server.c    → Endpoint GET /status
├── CMakeLists.txt             → CMake raíz del proyecto
├── sdkconfig.defaults         → Configuración ESP-IDF por defecto
└── README.md
```

## Responsabilidades

| Componente | Responsabilidad |
|---|---|
| `app_main` | Orquesta init, crea FreeRTOS tasks |
| `wifi_manager` | BluFi provisioning, reconexión automática |
| `sensor_manager` | Lee MPU6050 via I2C, acumula ventanas de N muestras |
| `mqtt_client_manager` | Publica JSON al broker, maneja reconexión |
| `http_diag_server` | Responde GET /status con JSON de diagnóstico |

## Flashear y monitorear

```bash
cd firmware
idf.py set-target esp32s3
idf.py build flash monitor
```
