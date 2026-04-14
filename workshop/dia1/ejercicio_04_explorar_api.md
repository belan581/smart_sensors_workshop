# Ejercicio 04 — Explorar el API y visualizar datos

**Tiempo:** 75 minutos  
**Día 1 — 15:15 a 16:30**

---

## Objetivo

Consultar los datos de tu sensor desde Python usando el API REST del backend.
Entender la estructura de datos y preparar el terreno para el ML del Día 2.

---

## Parte A — Tour de la Swagger UI

Ve a **http://localhost:8000/docs** y prueba cada endpoint:

### 1. GET /health
Verifica el estado del sistema. Campos importantes:
- `database_ok`: la base de datos SQLite funciona
- `mqtt_connected`: el backend recibe mensajes del broker
- `model_loaded`: el modelo ML está listo (hoy es `false`, mañana será `true`)

### 2. GET /sensors
Lista todos los dispositivos que han publicado datos.
- Nota el campo `windows_received`: cuántas ventanas ha enviado cada sensor

### 3. GET /sensors/{device_id}/latest
La medición más reciente. Contiene arrays `ax`, `ay`, `az` de 50 floats.

### 4. GET /sensors/{device_id}/history
Las últimas N mediciones. Útil para graficar tendencias.

### 5. GET /stats
Estadísticas globales: total de mediciones, conteo por clase de predicción.

---

## Parte B — Script de monitoreo en tiempo real

Crea `mi_monitor.py`:

```python
"""
Script que consulta el API cada segundo y muestra el resumen de datos.
Ejecución: python mi_monitor.py --device esp32s3_001
"""
import argparse
import json
import time
import urllib.request

def get(url):
    try:
        with urllib.request.urlopen(url, timeout=3) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}

def calcular_magnitud(ax, ay, az):
    import math
    magnitudes = [math.sqrt(a**2 + b**2 + c**2) for a, b, c in zip(ax, ay, az)]
    return sum(magnitudes) / len(magnitudes)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", default="esp32s3_001")
    parser.add_argument("--backend", default="http://localhost:8000")
    args = parser.parse_args()

    print(f"Monitoreando: {args.device}")
    print(f"Backend:      {args.backend}")
    print("-" * 50)

    while True:
        data = get(f"{args.backend}/sensors/{args.device}/latest")

        if "error" in data:
            print(f"Error: {data['error']}")
        elif data is None or (isinstance(data, dict) and "detail" in data):
            print("Sin datos todavía. Espera a que el sensor envíe una ventana...")
        else:
            ax = data.get("ax", [])
            ay = data.get("ay", [])
            az = data.get("az", [])

            if ax:
                mag = calcular_magnitud(ax, ay, az)
                ax_mean = sum(ax) / len(ax)
                ay_mean = sum(ay) / len(ay)
                az_mean = sum(az) / len(az)
                temp = data.get("temperature", "N/A")

                print(
                    f"ax={ax_mean:+.3f}  ay={ay_mean:+.3f}  az={az_mean:+.3f}  "
                    f"mag={mag:.3f}  temp={temp}°C"
                )

        time.sleep(1)

if __name__ == "__main__":
    main()
```

Ejecutar:
```powershell
python mi_monitor.py --device esp32s3_001
# o con el nombre que usaste en el simulador:
python mi_monitor.py --device mi_esp32
```

Mientras el script corre, mueve el sensor (o cambia el `--motion` del simulador)
y observa cómo cambian los valores.

---

## Parte C — Graficar una ventana de datos

Crea `mi_grafico.py`:

```python
"""
Grafica la última ventana del sensor usando matplotlib.
Ejecutar: python mi_grafico.py --device esp32s3_001
"""
import argparse
import json
import urllib.request

try:
    import matplotlib.pyplot as plt
except ImportError:
    print("Instalar matplotlib: pip install matplotlib")
    raise SystemExit(1)

def get(url):
    with urllib.request.urlopen(url, timeout=3) as r:
        return json.loads(r.read())

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", default="esp32s3_001")
    args = parser.parse_args()

    data = get(f"http://localhost:8000/sensors/{args.device}/latest")

    ax = data["ax"]
    ay = data["ay"]
    az = data["az"]
    t  = [i / 100 for i in range(len(ax))]  # tiempo en segundos

    fig, axes = plt.subplots(3, 1, figsize=(10, 7), sharex=True)
    fig.suptitle(f"Ventana de aceleración — {args.device}", fontsize=13)

    for axis_data, label, color, ax_obj in [
        (ax, "ax (m/s²)", "tab:blue",   axes[0]),
        (ay, "ay (m/s²)", "tab:orange", axes[1]),
        (az, "az (m/s²)", "tab:green",  axes[2]),
    ]:
        ax_obj.plot(t, axis_data, color=color, linewidth=1.2)
        ax_obj.set_ylabel(label)
        ax_obj.grid(True, alpha=0.4)
        ax_obj.axhline(0, color="black", linewidth=0.5)

    axes[2].set_xlabel("Tiempo (s)")
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()
```

Ejecutar:
```powershell
python mi_grafico.py --device mi_esp32
```

---

## Preguntas para pensar

1. La señal de `az` en reposo está cerca de **9.81 m/s²** (la gravedad). ¿Por qué?

2. Cambia el simulador a `--motion vibracion` y luego a `--motion reposo`.  
   ¿En qué eje se ve más diferencia en el gráfico?

3. ¿Por qué crees que el sistema envía *ventanas* de 50 muestras en lugar de
   enviar cada muestra individualmente?

4. Mira el campo `windows_received` en `GET /sensors`.  
   ¿Cuántas ventanas por segundo llegan? ¿Coincide con lo que esperas a 100 Hz / 50 muestras?

---

## ✅ Criterio de éxito

- `mi_monitor.py` muestra valores actualizados cada segundo
- `mi_grafico.py` genera una gráfica con 3 subplots (ax, ay, az)
- Puedes distinguir visualmente entre `--motion reposo` y `--motion vibracion`
