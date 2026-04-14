# Ejercicio 01 — Setup del entorno

**Tiempo:** 90 minutos  
**Día 1 — 09:00 a 10:30**

---

## Objetivo

Al terminar este ejercicio tendrás:
- Python instalado y el entorno virtual creado
- El backend corriendo en tu PC
- El broker MQTT activo
- La verificación del sistema en verde

---

## Paso 1 — Verificar Python

Abre una terminal PowerShell y ejecuta:

```powershell
python --version
```

Debes ver `Python 3.11.x` o superior. Si no:
- Windows: descargar desde https://python.org/downloads
- **Importante:** marcar "Add Python to PATH" durante la instalación

---

## Paso 2 — Instalar Mosquitto

1. Descargar desde https://mosquitto.org/download/ (instalador `.exe` para Windows)
2. Instalar con opciones por defecto
3. Verificar que funciona:

```powershell
mosquitto -v
```

Debe mostrar la versión. Si no lo encuentra, agregar `C:\Program Files\mosquitto\` al PATH.

---

## Paso 3 — Obtener el proyecto

```powershell
# Opción A: copiar desde USB del instructor
# Copiar la carpeta smart_sensors_workshop a C:\taller\

# Opción B: clonar desde repositorio (si hay conexión)
git clone <url_del_repo> C:\taller\smart_sensors_workshop
```

---

## Paso 4 — Setup del entorno Python

```powershell
cd C:\taller\smart_sensors_workshop

# Crear entorno virtual, instalar todas las dependencias
.\scripts\setup_env.ps1 -IncludeML
```

Esto puede tardar 3–5 minutos. Verás mensajes como:
```
  [OK] Entorno virtual creado
  [OK] pip actualizado
  [OK] Backend instalado
  [OK] Creado backend/.env desde .env.example
```

> **Si aparece: "la ejecución de scripts está deshabilitada"**
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```
> Luego vuelve a ejecutar `setup_env.ps1`

---

## Paso 5 — Arrancar el broker MQTT

Abre una **nueva ventana de terminal** y ejecuta:

```powershell
cd C:\taller\smart_sensors_workshop
.\scripts\start_broker.ps1
```

Deja esta terminal abierta. Verás líneas de log de Mosquitto.

---

## Paso 6 — Arrancar el backend

Abre **otra nueva ventana de terminal** y ejecuta:

```powershell
cd C:\taller\smart_sensors_workshop
.\scripts\start_backend.ps1
```

Verás:
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## Paso 7 — Verificar el sistema

En la terminal original:

```powershell
python scripts\check_integration.py
```

**Resultado esperado:**
```
  [OK]  Backend: app/main.py
  [OK]  Puerto 1883 escuchando (Mosquitto)
  [OK]  Puerto 8000 escuchando (FastAPI)
  [OK]  .env existe en backend/
  ...
```

---

## Paso 8 — Abrir la documentación del API

Abre en tu navegador: **http://localhost:8000/docs**

Debes ver la interfaz Swagger con todos los endpoints. Expande `GET /health` y haz clic en "Try it out" → "Execute".

**Resultado esperado:**
```json
{
  "status": "ok",
  "database_ok": true,
  "mqtt_connected": true,
  "model_loaded": false
}
```

`model_loaded: false` es normal — el modelo se entrena en el Día 2.

---

## ✅ Criterio de éxito

- Terminal 1: Mosquitto corriendo sin errores
- Terminal 2: FastAPI corriendo en puerto 8000
- Navegador: Swagger UI accesible
- `check_integration.py`: sin líneas `[FAIL]` en los primeros 6 checks

---

## Preguntas para pensar

1. ¿Por qué usamos un entorno virtual de Python en lugar de instalar los paquetes globalmente?
2. ¿Qué pasaría si dos alumnos usan el mismo `device_id` en el taller?
3. ¿Por qué el broker MQTT y el backend son programas separados?
