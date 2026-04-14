# Programa del Taller — 2 Días
## "Sensores inteligentes, uso de IA en sistemas embebidos y emulación de envío de información como en la industria"

**Nivel:** Principiantes en robótica  
**Duración:** 2 días × 8 horas = 16 horas  
**Grupo:** 8–20 personas  
**Material por participante:** ESP32-S3 + MPU6050 + cable USB + PC con Python

---

## Resumen de los dos días

| Día | Enfoque | Resultado al final del día |
|-----|---------|---------------------------|
| 1   | Hardware → Comunicación | El ESP32 envía datos a tu PC via WiFi+MQTT y el instructor los visualiza en tiempo real |
| 2   | IA → Industria | El sistema clasifica movimientos automáticamente y responde como un sistema IIoT real |

---

## DÍA 1 — Hardware, sensores y comunicación

### Objetivo del día
> "Conectar un sensor físico a Internet y ver sus datos en tiempo real desde cualquier PC de la red."

---

### 08:00 – 09:00 | Presentación y contexto (60 min)

**Tipo:** Charla + preguntas  
**Material:** Presentación, pizarrón

| Minutos | Contenido |
|---------|----------|
| 0–15    | ¿Qué es IoT? ¿Qué es IIoT? Diferencias. Casos reales en fábricas |
| 15–30   | Arquitectura del sistema que van a construir (diagrama completo) |
| 30–45   | Tour del hardware: ESP32-S3, MPU6050, pines, I2C |
| 45–60   | Ronda de preguntas + distribuir kits de hardware |

**Puntos clave a comunicar:**
- El ESP32 no es "solo un Arduino más potente" — tiene WiFi y doble núcleo
- El MPU6050 habla I²C: solo 2 cables de datos (SDA + SCL)
- En industria, los datos viajan por protocolos como MQTT, OPC-UA, AMQP

---

### 09:00 – 10:30 | Setup del entorno (90 min)

**Tipo:** Hands-on individual  
**Archivo de referencia:** `workshop/dia1/ejercicio_01_setup.md`

| Minutos | Actividad |
|---------|----------|
| 0–20    | Instalar Python, VS Code + ESP-IDF Extension, drivers USB |
| 20–40   | Clonar/copiar el proyecto, ejecutar `setup_env.ps1` |
| 40–60   | Verificar que el backend arranca: abrir `localhost:8000/docs` |
| 60–90   | Instalar Mosquitto, lanzar broker, verificar con MQTT Explorer |

**Señales de éxito:**
- `python scripts\check_integration.py` muestra database_ok y puerto 1883 activo
- Swagger UI carga en el navegador

**Problemas frecuentes (ver Guía del Facilitador Día 1, sección 1):**
- Driver CH340/CP2102 no instalado → ESP32 no aparece como COM port
- PowerShell con política de ejecución restringida → `Set-ExecutionPolicy RemoteSigned`

---

### 10:30 – 10:45 | ☕ Descanso

---

### 10:45 – 12:15 | MQTT: el idioma de las máquinas (90 min)

**Tipo:** Demo + práctica guiada  
**Archivo de referencia:** `workshop/dia1/ejercicio_02_mqtt.md`

| Minutos | Actividad |
|---------|----------|
| 0–20    | Explicación: topics, publish/subscribe, QoS, retain, LWT |
| 20–40   | Demo en vivo: publicar y suscribirse con MQTT Explorer |
| 40–70   | Ejercicio: los alumnos publican mensajes manualmente desde Python |
| 70–90   | Explicar el payload JSON del firmware. Publicar una ventana fake a mano |

**Herramienta recomendada:** MQTT Explorer (gratuita, visual, muy clara para demostrar pub/sub)
- Descargar: https://mqtt-explorer.com/

**Ejercicio central:** Cada alumno publica en `taller/{su_nombre}/hola` y lee los mensajes de sus compañeros.

---

### 12:15 – 13:15 | 🍽️ Almuerzo

---

### 13:15 – 15:00 | Flashear firmware y ver datos en vivo (105 min)

**Tipo:** Hands-on individual  
**Archivo de referencia:** `workshop/dia1/ejercicio_03_firmware.md`

| Minutos | Actividad |
|---------|----------|
| 0–15    | Explicar el código del firmware: app_main.c, sensor_manager, mqtt_client_manager |
| 15–40   | Flashear el firmware con `idf.py flash monitor` |
| 40–70   | Configurar WiFi con BluFi (app en teléfono) o cambiar credenciales en código |
| 70–105  | Verificar que los datos llegan al backend: `GET /sensors/{device_id}/latest` |

> **Alternativa si el flash falla:** usar el simulador en su lugar  
> `python scripts\simulate_esp32.py --device nombre_{alumno} --motion reposo`

**Señales de éxito:**
- Monitor serie muestra "MQTT publish OK window=0"
- `GET /sensors` en Swagger devuelve el device_id del alumno
- MQTT Explorer muestra mensajes llegando en tiempo real

---

### 15:00 – 15:15 | ☕ Descanso

---

### 15:15 – 16:30 | Explorar los datos (75 min)

**Tipo:** Práctica con Swagger + Python  
**Archivo de referencia:** `workshop/dia1/ejercicio_04_explorar_api.md`

| Minutos | Actividad |
|---------|----------|
| 0–20    | Tour de la Swagger UI: probar todos los endpoints |
| 20–50   | Ejercicio: script Python que consulta el API cada segundo y muestra los datos |
| 50–75   | Discusión: ¿por qué no enviar features pre-calculadas desde el firmware? |

---

### 16:30 – 17:00 | Retrospectiva Día 1 (30 min)

**Tipo:** Discusión guiada

- ¿Qué pasó en el sistema hoy? Recorrido conceptual completo
- ¿Qué haría este sistema diferente en una fábrica real? (seguridad, TLS, autenticación)
- Preview del Día 2: "mañana vamos a hacer que la máquina entienda qué está pasando"

---
---

## DÍA 2 — Inteligencia artificial e integración industrial

### Objetivo del día
> "Agregar un modelo de ML que clasifica el movimiento del sensor en tiempo real, como haría un sistema predictivo en la industria."

---

### 08:00 – 09:30 | Introducción al aprendizaje automático (90 min)

**Tipo:** Charla + demo visual  
**Material:** Notebook `ml/notebooks/01_exploracion_dataset.ipynb`

| Minutos | Contenido |
|---------|----------|
| 0–20    | ¿Qué es el ML? Pipeline: datos → features → modelo → predicción |
| 20–40   | El problema de clasificación: 6 tipos de movimiento |
| 40–60   | Demo en vivo: abrir el notebook, visualizar señales por clase |
| 60–75   | Explicar ventana deslizante y las 25 features extraídas |
| 75–90   | ¿Por qué Random Forest? Ventajas para principiantes en IIoT |

**Herramienta:** Jupyter Notebook o VS Code Jupyter extension

---

### 09:30 – 10:30 | Entrenar el modelo (60 min)

**Tipo:** Hands-on  
**Archivo de referencia:** `workshop/dia2/ejercicio_05_entrenar.md`

| Minutos | Actividad |
|---------|----------|
| 0–10    | Generar dataset sintético: `python scripts\generate_fake_dataset.py` |
| 10–30   | Ejecutar pipeline: `.\scripts\train_model.ps1 -Synthetic` |
| 30–45   | Analizar resultados: reporte de clasificación, matriz de confusión |
| 45–60   | Copiar modelos: `.\scripts\copy_models.ps1` |

**Señales de éxito:**
- `backend/models/` tiene los 3 archivos `.pkl`
- El reporte muestra accuracy > 85% (datos sintéticos son fácilmente separables)

---

### 10:30 – 10:45 | ☕ Descanso

---

### 10:45 – 12:15 | El sistema completo en acción (90 min)

**Tipo:** Demo guiada + hands-on  
**Archivo de referencia:** `workshop/dia2/ejercicio_06_sistema_completo.md`

| Minutos | Actividad |
|---------|----------|
| 0–15    | Ver el flujo completo en el código: MQTT → data_processor → ml_service → DB |
| 15–30   | Reiniciar el backend (para que cargue los modelos nuevos) |
| 30–50   | Usar el simulador y ver predicciones en tiempo real via `GET /predictions/latest` |
| 50–70   | Con ESP32 físico (si funciona): mover el sensor y ver la predicción correcta |
| 70–90   | `python scripts\test_pipeline.py --send-mqtt` — verificación automática |

---

### 12:15 – 13:15 | 🍽️ Almuerzo

---

### 13:15 – 14:45 | Ejercicio de integración (desafío) (90 min)

**Tipo:** Trabajo en equipos de 2-3 personas  
**Archivo de referencia:** `workshop/dia2/ejercicio_07_desafio.md`

> **Desafío:** Añadir una nueva clase de movimiento al sistema

| Paso | Actividad |
|------|----------|
| 1    | Agregar un nuevo generador de movimiento en `simulate_esp32.py` |
| 2    | Re-generar el dataset incluyendo la nueva clase |
| 3    | Re-entrenar el modelo y copiarlo al backend |
| 4    | Reiniciar el backend y verificar que el nuevo movimiento se predice |
| 5    | Presentar al grupo: ¿qué movimiento añadieron? ¿qué accuracy obtuvo? |

**Objetivo pedagógico:** Entender que el modelo es configurable, no magia. Agregar una clase es parte del proceso de ingeniería.

---

### 14:45 – 15:00 | ☕ Descanso

---

### 15:00 – 16:00 | IIoT en la industria real (60 min)

**Tipo:** Charla + discusión  
**Material:** Slides opcionales

| Minutos | Contenido |
|---------|----------|
| 0–20    | De este sistema al mundo real: OPC-UA, Kafka, SCADA |
| 20–35   | Seguridad: lo que falta (TLS, autenticación MQTT, JWT en el API) |
| 35–50   | Casos de uso industriales: mantenimiento predictivo, detección de anomalías |
| 50–60   | ¿Qué componente de este sistema aplicarías en tu trabajo/proyecto? |

---

### 16:00 – 16:45 | Presentaciones de equipos (45 min)

Cada equipo presenta su nueva clase de movimiento:
- ¿Qué movimiento implementaron y por qué?
- ¿Qué accuracy obtuvo?
- ¿Qué cambiarían si fuera para producción?

---

### 16:45 – 17:00 | Cierre y próximos pasos (15 min)

- Recursos para seguir aprendiendo (ESP-IDF docs, scikit-learn, FastAPI docs)
- Cómo adaptar este sistema a un proyecto propio
- Certificados / foto grupal

---

## Checklist pre-taller (instructor)

### Semana antes
- [ ] Instalar y probar ESP-IDF en la PC del instructor
- [ ] Flashear firmware en todos los ESP32 de repuesto
- [ ] Entrenar modelo con dataset sintético y verificar predicciones
- [ ] Probar BluFi con la red WiFi del aula
- [ ] Preparar MQTT Explorer instalado en un USB de respaldo
- [ ] Verificar que `python scripts\check_integration.py` pasa todo en verde
- [ ] Preparar 2-3 ESP32 extra en caso de fallos de hardware

### Día antes
- [ ] Preparar red WiFi dedicada para el taller (evitar filtros de broadcast)
- [ ] Tener IP del broker anotada para configurar como fallback en código
- [ ] Copiar el proyecto completo a un USB por si la descarga falla
- [ ] Crear imagen pre-configurada de la VM/entorno Python (opcional)

### 30 min antes de cada día
- [ ] Arrancar broker: `.\scripts\start_broker.ps1`
- [ ] Arrancar backend: `.\scripts\start_backend.ps1`
- [ ] Verificar: `python scripts\check_integration.py`
- [ ] Proyectar Swagger UI en pantalla grande
