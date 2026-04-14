# Ejercicio 06 — El sistema completo en acción

**Tiempo:** 90 minutos  
**Día 2 — 10:45 a 12:15**

---

## Objetivo

Ver el flujo completo funcionando: sensor → MQTT → backend → ML → predicción,
y entender qué hace cada pieza del código en tiempo real.

---

## Recorrido del código antes de arrancar

Sigue este flujo abriendo cada archivo:

### 1. Mensaje llega al broker
El firmware o simulador publica en `sensors/{device_id}/raw`.
El broker Mosquitto reenvía el mensaje a todos los suscriptores.

### 2. El backend recibe el mensaje
`backend/app/core/mqtt_subscriber.py` línea donde se llama `on_message`:
```python
# El hilo de MQTT recibe el mensaje JSON
# y llama a DataProcessor.process(device_id, payload)
```

### 3. El procesador orquesta el pipeline
`backend/app/services/data_processor.py`:
1. Valida el payload (listas de 50 elementos)
2. Crea o actualiza el registro del sensor en la BD
3. Guarda la medición
4. Llama a `MLService.predict(ax, ay, az)`
5. Guarda la predicción

### 4. El ML Service extrae features y predice
`backend/app/ml/ml_service.py`:
1. Llama a `feature_extractor.extract_features_from_window(ax, ay, az)` → 25 floats
2. Aplica `scaler.transform()` (normalización)
3. Llama a `model.predict()` → etiqueta
4. Llama a `model.predict_proba()` → probabilidades de cada clase

---

## Paso 1 — Verificar el sistema completo

```powershell
python scripts\check_integration.py
```

Todos los checks deben ser `[OK]`, incluyendo `model_loaded = true`.

---

## Paso 2 — Simular diferentes movimientos y ver predicciones

**Terminal 3 — simulador:**
```powershell
# Simular 10 ventanas de vibración
python scripts\simulate_esp32.py --motion vibracion --count 10 --rate 2.0
```

**Mientras corre, en el navegador:**
- http://localhost:8000/docs → `GET /predictions/latest` → Execute
- Cada vez que ejecutas debería aparecer la predicción `vibracion`

Ahora cambia el movimiento:
```powershell
python scripts\simulate_esp32.py --motion reposo --count 10 --rate 2.0
```

Vuelve a ejecutar `GET /predictions/latest`. ¿Cambió la etiqueta?

---

## Paso 3 — Inferencia directa vía HTTP (sin MQTT)

El endpoint `POST /predict` permite enviar un payload y obtener una predicción
sin pasar por el broker. Útil para pruebas y durante el desarrollo.

En Swagger UI (http://localhost:8000/docs), expande `POST /predict` y usa
este body de ejemplo (copia y pega):

```json
{
  "device_id": "prueba_manual",
  "ax": [0.82, -0.75, 0.91, -0.88, 0.78, -0.71, 0.85, -0.80, 0.79, -0.76,
         0.83, -0.74, 0.87, -0.82, 0.77, -0.73, 0.84, -0.79, 0.81, -0.77,
         0.86, -0.75, 0.80, -0.83, 0.78, -0.72, 0.85, -0.81, 0.79, -0.76,
         0.83, -0.74, 0.87, -0.82, 0.77, -0.73, 0.84, -0.79, 0.81, -0.77,
         0.86, -0.75, 0.80, -0.83, 0.78, -0.72, 0.85, -0.81, 0.79, -0.76],
  "ay": [0.75, -0.70, 0.80, -0.77, 0.72, -0.68, 0.78, -0.74, 0.73, -0.71,
         0.76, -0.69, 0.81, -0.75, 0.71, -0.67, 0.79, -0.73, 0.74, -0.70,
         0.77, -0.68, 0.82, -0.76, 0.72, -0.66, 0.80, -0.74, 0.73, -0.71,
         0.76, -0.69, 0.81, -0.75, 0.71, -0.67, 0.79, -0.73, 0.74, -0.70,
         0.77, -0.68, 0.82, -0.76, 0.72, -0.66, 0.80, -0.74, 0.73, -0.71],
  "az": [9.82, 9.79, 9.83, 9.80, 9.81, 9.78, 9.84, 9.81, 9.82, 9.79,
         9.81, 9.80, 9.83, 9.79, 9.82, 9.80, 9.81, 9.78, 9.84, 9.81,
         9.82, 9.79, 9.81, 9.80, 9.83, 9.79, 9.82, 9.80, 9.81, 9.78,
         9.84, 9.81, 9.82, 9.79, 9.81, 9.80, 9.83, 9.79, 9.82, 9.80,
         9.81, 9.78, 9.84, 9.81, 9.82, 9.79, 9.81, 9.80, 9.83, 9.79]
}
```

El modelo debería predecir `vibracion` (la señal ax/ay oscila como un motor).

---

## Paso 4 — Prueba automática del pipeline completo

```powershell
python scripts\test_pipeline.py --send-mqtt
```

Este script:
1. Verifica todos los endpoints del API
2. Publica 3 ventanas reales vía MQTT
3. Espera y verifica que las predicciones fueron guardadas

Resultado esperado: `✓ Pipeline verificado correctamente`

---

## Paso 5 — Explorar las predicciones en Python

```python
import json
import urllib.request

def get(url):
    with urllib.request.urlopen(url) as r:
        return json.loads(r.read())

# Obtener las últimas 5 predicciones
predicciones = get("http://localhost:8000/predictions/latest")
for p in predicciones[:5]:
    device  = p.get("device_id", "?")
    label   = p.get("label", "?")
    conf    = p.get("confidence", 0)
    print(f"{device:20s} → {label:12s} ({conf:.1%})")
```

---

## ✅ Criterio de éxito

- El simulador en `vibracion` genera predicciones `vibracion` con confianza > 80%
- `POST /predict` con los datos del ejemplo devuelve la predicción correcta
- `test_pipeline.py --send-mqtt` pasa todas las pruebas

---

## Reflexión (5 min)

Discutir con el grupo:
- ¿Qué pasaría si un sensor nuevo envía un tipo de movimiento que el modelo nunca vio?
- ¿Cómo podría un sistema industrial reaccionar ante una predicción de "golpe"?
- ¿Qué información falta en este sistema para usarlo en producción real?
