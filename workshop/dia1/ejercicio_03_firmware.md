# Ejercicio 03 — Flashear el firmware y ver datos en vivo

**Tiempo:** 105 minutos  
**Día 1 — 13:15 a 15:00**

> **Si no tienes ESP32 o el flash falla:** salta directamente al apartado
> "Alternativa: usar el simulador" y continúa desde allí.

---

## Objetivo

Compilar y cargar el firmware en el ESP32-S3, conectarlo a la red WiFi del
taller y verificar que los datos del MPU6050 llegan al backend en tiempo real.

---

## Conexiones de hardware

Antes de conectar el ESP32 a la PC:

| Pin MPU6050 | Pin ESP32-S3 | Color típico |
|------------|-------------|-------------|
| VCC        | 3.3V        | Rojo        |
| GND        | GND         | Negro       |
| SDA        | GPIO 8      | Azul        |
| SCL        | GPIO 9      | Amarillo    |
| AD0        | GND         | (dirección I²C = 0x68) |

---

## Paso 1 — Instalar ESP-IDF (si no está instalado)

**Windows — método recomendado:**
1. Descargar el instalador: https://dl.espressif.com/dl/esp-idf/
2. Seleccionar ESP-IDF v5.3 o superior
3. Marcar "Add to PATH" y "Install all tools"
4. La instalación tarda ~15 minutos

Verificar desde PowerShell:
```powershell
idf.py --version
```

---

## Paso 2 — Configurar la IP del broker en el firmware

Abre `firmware/components/wifi_manager/wifi_manager.c` y localiza:

```c
#define BROKER_MDNS_HOSTNAME  "smart-sensors-broker"
#define BROKER_FALLBACK_IP    "192.168.1.100"
```

Cambia `BROKER_FALLBACK_IP` por la IP de tu PC en la red del taller.

Para saber tu IP:
```powershell
ipconfig | Select-String "IPv4"
```

---

## Paso 3 — Configurar device_id único (opcional)

Abre `firmware/main/app_main.c` y busca:

```c
#define DEVICE_ID  "esp32s3_001"
```

Cambia `001` por las últimas 3 cifras de tu número de lista o nombre corto.
Esto garantiza que cada alumno tenga un `device_id` diferente.

---

## Paso 4 — Compilar y flashear

```powershell
cd C:\taller\smart_sensors_workshop\firmware

# Primera vez (puede tardar 5-10 minutos)
idf.py build

# Conectar el ESP32 y flashear
idf.py -p COM3 flash monitor
```

> Reemplaza `COM3` por el puerto real. Verificar en:
> `Administrador de dispositivos → Puertos (COM y LPT)`

---

## Paso 5 — Configurar WiFi con BluFi

Después del flash, el monitor serie mostrará:
```
I (1234) wifi_manager: Iniciando BluFi provisioning...
I (1234) wifi_manager: Esperando credenciales via BluFi...
```

1. Instalar app **ESP BLE Provisioning** en tu teléfono
   - Android: Play Store | iOS: App Store
2. Abrir la app → "Provision New Device" → "I don't have a QR code"
3. La app encontrará el ESP32 como `PROV_XXXXXX`
4. Ingresar SSID y contraseña del WiFi del taller
5. El monitor serie mostrará: `I wifi_manager: ¡Conectado! IP: 192.168.x.x`

---

## Paso 6 — Verificar que los datos llegan

En el monitor serie verás:
```
I sensor_manager: Ventana completa. samples=50
I mqtt_client_manager: Publicado → sensors/esp32s3_001/raw (847 bytes)
```

En el backend (http://localhost:8000/docs):
- `GET /sensors` → debe aparecer tu device_id
- `GET /sensors/{device_id}/latest` → datos del último window

---

## Alternativa: usar el simulador

Si el flash falla o no tienes hardware, el simulador es equivalente:

```powershell
# Reemplaza "mi_esp32" por tu nombre
python scripts\simulate_esp32.py --device mi_esp32 --motion reposo

# Ver los datos en el backend
# http://localhost:8000/sensors/mi_esp32/latest
```

El simulador publica exactamente el mismo payload JSON que el firmware real.

---

## ✅ Criterio de éxito

**Con hardware:**
- Monitor serie muestra "Publicado → sensors/.../raw" cada ~500 ms
- `GET /sensors` muestra tu device_id con `last_seen` reciente

**Con simulador:**
- El simulador publica sin errores de conexión
- `GET /sensors` muestra el device_id configurado

---

## Explorar el código (10 min)

Abre estos archivos y lee los comentarios:

| Archivo | Qué explica |
|---------|------------|
| `firmware/main/app_main.c` | Secuencia de inicialización de 6 pasos |
| `firmware/components/sensor_manager/sensor_manager.c` | Double buffer + 100 Hz con `vTaskDelayUntil` |
| `firmware/components/mqtt_client_manager/mqtt_client_manager.c` | Construcción del payload JSON con cJSON |

**Pregunta:** ¿Por qué el sensor_manager corre en el Core 1 y el publish_task en el Core 0?
