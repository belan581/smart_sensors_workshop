# Ejercicio 02 — MQTT: el idioma de las máquinas

**Tiempo:** 90 minutos  
**Día 1 — 10:45 a 12:15**

---

## Objetivo

Entender el patrón publish/subscribe de MQTT y publicar tu primer mensaje
desde Python — igual que lo hará el ESP32 más tarde.

---

## Contexto: ¿por qué MQTT?

MQTT fue diseñado para dispositivos con recursos limitados en redes poco
confiables (sensores industriales, fábricas, barcos). Sus ventajas:

| Característica | HTTP REST | MQTT |
|---------------|----------|------|
| Overhead por mensaje | Alto (~200 bytes headers) | Mínimo (~2 bytes) |
| Patrón | Request/Response | Publish/Subscribe |
| Múltiples receptores | No directo | Sí (topics) |
| Desconexión del cliente | Sin solución | LWT (Last Will) |
| Batería | Alto consumo | Bajo consumo |

---

## Parte A — Explorar con MQTT Explorer

**MQTT Explorer** es una herramienta visual para ver mensajes MQTT en tiempo real.

1. Descarga: https://mqtt-explorer.com/
2. Conectar al broker local:
   - Host: `localhost`
   - Port: `1883`
   - No marcar TLS ni autenticación
3. Clic en "Connect"

Deberías ver el panel vacío (nadie ha publicado todavía).

---

## Parte B — Tu primer publisher en Python

Crea un archivo llamado `mi_publisher.py` en la carpeta del taller:

```python
import json
import time
import paho.mqtt.client as mqtt

# Cambia "tu_nombre" por tu nombre real
DEVICE_NAME = "tu_nombre"
BROKER_HOST  = "localhost"
BROKER_PORT  = 1883

client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    client_id=f"publisher_{DEVICE_NAME}",
)
client.connect(BROKER_HOST, BROKER_PORT)
client.loop_start()

topic = f"taller/{DEVICE_NAME}/hola"

for i in range(5):
    mensaje = {
        "nombre": DEVICE_NAME,
        "contador": i,
        "timestamp": int(time.time()),
        "saludo": f"Hola desde {DEVICE_NAME}, mensaje {i}",
    }
    client.publish(topic, json.dumps(mensaje), qos=1)
    print(f"Publicado: {mensaje}")
    time.sleep(2)

client.loop_stop()
client.disconnect()
print("Listo.")
```

Ejecutar:
```powershell
python mi_publisher.py
```

Mientras corre, observa MQTT Explorer: verás los mensajes llegar en tiempo real.

---

## Parte C — Suscribirse a los mensajes de tus compañeros

```python
import json
import paho.mqtt.client as mqtt

def on_message(client, userdata, message, properties=None):
    try:
        data = json.loads(message.payload)
        print(f"[{message.topic}] {data}")
    except json.JSONDecodeError:
        print(f"[{message.topic}] (no es JSON): {message.payload}")

client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    client_id="mi_subscriber",
)
client.on_message = on_message
client.connect("localhost", 1883)

# El '+' es un comodín: recibe mensajes de TODOS los alumnos
client.subscribe("taller/+/hola", qos=1)
print("Escuchando mensajes de todos... Ctrl+C para salir\n")

client.loop_forever()
```

---

## Parte D — El payload del ESP32

Este es el JSON que publicará el firmware (copiado de `mqtt_client_manager.c`):

```json
{
  "device_id": "esp32s3_001",
  "timestamp": 1712345678,
  "ax": [-0.12, 0.08, 0.15, ...],
  "ay": [9.75, 9.82, 9.79, ...],
  "az": [0.05, -0.03, 0.01, ...],
  "temperature": 28.5,
  "battery": 95
}
```

**Preguntas:**
- `ax`, `ay`, `az` tienen **50 valores** cada uno. ¿Por qué 50? (pista: 100 Hz × 0.5 s)
- ¿Por qué enviar el array completo y no features pre-calculadas?
- ¿Qué pasa si el ESP32 se desconecta? (pista: busca "LWT" en `mqtt_client_manager.c`)

---

## Parte E — Simular un ESP32 completo

El proyecto incluye un simulador que genera payloads realistas:

```powershell
# Simular 5 ventanas de vibración
python scripts\simulate_esp32.py --motion vibracion --count 5

# Ver qué llega en el backend
# Abre http://localhost:8000/docs → GET /sensors → Execute
```

Observa en MQTT Explorer el topic `sensors/esp32s3_001/raw`.

---

## ✅ Criterio de éxito

- Publicaste 5 mensajes desde Python y los viste en MQTT Explorer
- Te suscribiste al topic de un compañero y recibiste sus mensajes
- El simulador del ESP32 publica correctamente y aparece en `GET /sensors`

---

## Preguntas para pensar

1. ¿Qué significa QoS 0, 1 y 2 en MQTT? ¿Cuándo usarías QoS 2 en industria?
2. ¿Qué es un "retained message"? ¿Para qué sirve en el firmware?
3. ¿Qué ventaja tiene MQTT sobre enviar los datos directamente al backend vía HTTP POST?
