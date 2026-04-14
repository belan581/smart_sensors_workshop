# Ejercicio 07 — Desafío: añadir una nueva clase de movimiento

**Tiempo:** 90 minutos  
**Día 2 — 13:15 a 14:45**  
**Formato:** Equipos de 2–3 personas

---

## Objetivo

Agregar una nueva clase de movimiento al sistema completo — desde el generador
de señal hasta la predicción — y presentar el resultado al grupo.

---

## El desafío

Elige un movimiento que represente algo real e interesante:

| Ideas | Descripción física |
|-------|-------------------|
| **sacudida** | Movimiento brusco repetido en eje X/Y |
| **circular** | Movimiento circular en el plano XY |
| **escalera** | Pasos regulares (impactos periódicos) |
| **conveyor** | Cinta transportadora: vibración baja frecuencia + tendencia |
| **desequilibrio** | Motor desbalanceado: vibración + componente DC |
| *tu idea* | Cualquier movimiento que puedas describir matemáticamente |

---

## Paso 1 — Crear el generador de señal

Abre `scripts/simulate_esp32.py` y localiza el diccionario `MOTION_GENERATORS`.

Agrega tu nuevo generador siguiendo el patrón de los existentes:

```python
def gen_sacudida(amp: float = 5.0, freq: float = 4.0) -> tuple[list, list, list]:
    """Sacudida brusca repetida a baja frecuencia."""
    import math
    t = [i / SAMPLE_HZ for i in range(WINDOW_SIZE)]
    # La sacudida se modela como una sinusoide de baja frecuencia de alta amplitud
    ax = [amp * math.sin(2 * math.pi * freq * ti) * abs(math.sin(2 * math.pi * freq * ti))
          + _noise(0.1) for ti in t]
    ay = [amp * 0.3 * math.cos(2 * math.pi * freq * ti) + _noise(0.1) for ti in t]
    az = [GRAVITY + _noise(0.05) for _ in t]
    return ax, ay, az
```

Registrarlo en el diccionario:
```python
MOTION_GENERATORS: dict[str, Callable] = {
    # ... los existentes ...
    "sacudida": gen_sacudida,   # ← agregar aquí
}
```

---

## Paso 2 — Probar visualmente la señal

Antes de entrenar, verifica que la señal se vea distinta de las clases existentes:

```python
# prueba_visual.py
import matplotlib.pyplot as plt
import sys
sys.path.insert(0, "scripts")
from simulate_esp32 import MOTION_GENERATORS

fig, axes = plt.subplots(len(MOTION_GENERATORS), 3, figsize=(12, 2*len(MOTION_GENERATORS)))
fig.suptitle("Comparación de señales por clase")

for i, (name, gen) in enumerate(MOTION_GENERATORS.items()):
    ax, ay, az = gen()
    t = [j/100 for j in range(50)]
    axes[i, 0].plot(t, ax, linewidth=0.8); axes[i, 0].set_ylabel(name, fontsize=8)
    axes[i, 1].plot(t, ay, linewidth=0.8, color="orange")
    axes[i, 2].plot(t, az, linewidth=0.8, color="green")
    for j, title in enumerate(["ax", "ay", "az"]):
        axes[i, j].set_title(title if i == 0 else "")
        axes[i, j].tick_params(labelsize=7)

plt.tight_layout()
plt.show()
```

¿Tu nueva clase es visualmente distinguible de las demás?

---

## Paso 3 — Re-generar el dataset y re-entrenar

```powershell
# Generar dataset con la nueva clase incluida
python scripts\generate_fake_dataset.py --samples-per-class 200

# Entrenar (el script detecta automáticamente todas las clases en el CSV)
.\scripts\train_model.ps1 -Synthetic -Copy
```

---

## Paso 4 — Reiniciar el backend con el nuevo modelo

```powershell
# Ctrl+C en la terminal del backend, luego:
.\scripts\start_backend.ps1
```

Verificar que `model_loaded: true` en `GET /health`.

---

## Paso 5 — Probar la nueva clase

```powershell
python scripts\simulate_esp32.py --motion sacudida --count 10 --rate 2.0
```

Ver las predicciones:
```powershell
python scripts\test_pipeline.py
# Y revisar GET /predictions/latest en Swagger
```

---

## Paso 6 — Analizar los resultados

```powershell
python ml\scripts\04_evaluate.py
```

Observar en la matriz de confusión:
- ¿Se predice bien la nueva clase?
- ¿Confunde con alguna clase existente?
- Si la precisión es baja, ¿qué podrías cambiar en el generador?

---

## Presentación al grupo (5–7 minutos por equipo)

Preparar una mini-presentación respondiendo:

1. **¿Qué movimiento eligieron?** ¿A qué proceso industrial representa?
2. **¿Cómo generaron la señal?** Describir las fórmulas usadas
3. **¿Qué accuracy obtuvo?** ¿La nueva clase se confunde con alguna existente?
4. **¿Qué cambiarían** si tuvieran datos reales de un sensor físico?

---

## ✅ Criterio de éxito

- El nuevo movimiento aparece como opción en `--list-motions` del simulador
- El modelo predice correctamente la nueva clase con confianza > 70%
- La matriz de confusión muestra la nueva clase sin confusión grave con otras
- La presentación explica la lógica detrás de la señal generada

---

## Extensiones opcionales (si terminan antes)

### Opción A — Agregar el movimiento al firmware
En `firmware/components/sensor_manager/sensor_manager.c`, la señal real vendrá
del MPU6050. Pero puedes ver si el movimiento físico que describes existe en
el entorno (vibrar la mesa, girar el sensor, etc.) y comparar la predicción.

### Opción B — Endpoint de alerta
Agrega en el backend una lógica simple: si se predice `golpe` o `sacudida`
con confianza > 90%, imprimir una alerta en los logs del backend.
Busca en `backend/app/services/data_processor.py` el lugar donde se guarda la predicción.

### Opción C — Degradación del modelo
Reduce `--samples-per-class` a 20 y re-entrena. ¿Cómo afecta la cantidad
de datos al accuracy? ¿Cuántos datos mínimos necesitas?
