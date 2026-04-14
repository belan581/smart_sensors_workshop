# Ejercicio 05 — Entrenar el modelo de clasificación

**Tiempo:** 60 minutos  
**Día 2 — 09:30 a 10:30**

---

## Objetivo

Entrenar un clasificador de movimientos usando scikit-learn y entender qué
hace el modelo que luego usará el backend en tiempo real.

---

## Contexto: el pipeline completo

```
Datos crudos (ax/ay/az arrays)
        │
        ▼
  Ventana de 50 muestras
        │
        ▼
  25 features estadísticas    ← feature_extractor.py
  (media, std, RMS, energía...)
        │
        ▼
  RandomForest (modelo .pkl)  ← 03_train.py
        │
        ▼
  Predicción: "vibracion" (92%)
```

---

## Paso 1 — Generar el dataset sintético

```powershell
python scripts\generate_fake_dataset.py --samples-per-class 200
```

Esto crea `ml/data/raw/synthetic_dataset.csv` con:
- 6 clases × 200 muestras = 1200 filas
- Columnas: `label, ax_0..ax_49, ay_0..ay_49, az_0..az_49`

Abrir el CSV para inspeccionarlo:
```powershell
# Ver las primeras 3 filas
python -c "import pandas as pd; df=pd.read_csv('ml/data/raw/synthetic_dataset.csv'); print(df.head(3))"
```

---

## Paso 2 — Explorar el dataset en el notebook

Abre el notebook interactivo:
```powershell
# Desde VS Code: abrir ml/notebooks/01_exploracion_dataset.ipynb
# O desde consola:
python -m jupyter notebook ml/notebooks/01_exploracion_dataset.ipynb
```

Ejecuta las celdas y observa:
- Distribución de clases (debe ser balanceada, 200 por clase)
- Señales graficadas por clase — ¿puedes identificarlas a ojo?
- Boxplots de las features

---

## Paso 3 — Entender las features

Abre `ml/scripts/feature_extractor.py` y localiza la función `extract_features_from_window`.

Las 25 features son:

| Nº | Feature | Descripción |
|----|---------|------------|
| 1–7 | ax_mean, ax_std, ax_min, ax_max, ax_range, ax_rms, ax_energy | Estadísticas del eje X |
| 8–14 | ay_* | Estadísticas del eje Y |
| 15–21 | az_* | Estadísticas del eje Z |
| 22 | mag_mean | Media de la magnitud total |
| 23 | mag_std | Desviación de la magnitud |
| 24 | mag_max | Máximo de la magnitud |
| 25 | zcr_ax | Zero-crossing rate en eje X |

**Pregunta:** ¿Por qué el `zcr_ax` (cruces por cero) es útil para detectar vibración?

---

## Paso 4 — Ejecutar el pipeline de entrenamiento

```powershell
# Opción A: script todo-en-uno (recomendado para el taller)
.\scripts\train_model.ps1 -Synthetic -Copy

# Opción B: paso a paso (para entender el proceso)
python ml\scripts\01_prepare_data.py
python ml\scripts\02_extract_features.py
python ml\scripts\03_train.py
.\scripts\copy_models.ps1
```

Al terminar verás un reporte como:
```
              precision    recall  f1-score   support

       golpe       0.98      0.97      0.97        40
       libre       0.96      0.98      0.97        40
      random       1.00      1.00      1.00        40
      reposo       0.99      0.99      0.99        40
    rotacion       0.97      0.96      0.97        40
   vibracion       0.98      0.98      0.98        40

    accuracy                           0.98       240
```

Los datos sintéticos son muy "limpios" — en datos reales el accuracy será menor.

---

## Paso 5 — Verificar que el backend cargó el modelo

Reiniciar el backend para que cargue los nuevos modelos:

```powershell
# Ctrl+C en la terminal del backend, luego:
.\scripts\start_backend.ps1
```

Verificar en http://localhost:8000/health:
```json
{
  "model_loaded": true,   ← ahora debe ser true
  "mqtt_connected": true,
  "database_ok": true
}
```

---

## Parte opcional — Evaluar el modelo en detalle

```powershell
python ml\scripts\04_evaluate.py
```

Genera:
- `ml/outputs/confusion_matrix.png` — matriz de confusión
- `ml/outputs/feature_importance.png` — qué features importan más al modelo

**Pregunta:** Según `feature_importance.png`, ¿cuáles son las 3 features más importantes?
¿Tiene sentido intuitivamente?

---

## ✅ Criterio de éxito

- `ml/outputs/` contiene `model_rf.pkl`, `scaler.pkl`, `label_encoder.pkl`
- `backend/models/` contiene los mismos archivos (copiados)
- `GET /health` muestra `model_loaded: true`
- Accuracy en el reporte de entrenamiento > 90%
