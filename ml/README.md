# ML Pipeline - Smart Sensors Workshop

Pipeline completo de Machine Learning para clasificación de actividades usando datos del sensor MPU6050.

## 📋 Estructura del Proyecto

```
ml/
├── scripts/
│   ├── 01_prepare_data.py       → Carga y limpia el dataset
│   ├── 02_extract_features.py   → Extrae características estadísticas
│   ├── 03_train.py              → Entrena modelos (RF, MLP)
│   ├── 04_evaluate.py           → Evaluación y métricas
│   ├── feature_extractor.py     → Módulo de extracción de features
│   ├── predict_activity.py      → Predicción en tiempo real (PRODUCCIÓN)
│   ├── evaluate_new_data.py     → Evalúa accuracy con datos nuevos
│   └── analyze_new_data.py      → Analiza comparación de escalas
├── data/
│   ├── raw/                     → Datos del MPU6050 (drinking.csv, driving.csv, throwing.csv)
│   └── processed/               → Datos procesados (cleaned_data.csv, features_dataset.csv)
├── outputs/
│   ├── model_rf.pkl             → Modelo Random Forest (95.99% accuracy) ⭐
│   ├── model_mlp.pkl            → Modelo MLP (92.85% accuracy)
│   ├── label_encoder.pkl        → Codificador de etiquetas
│   ├── scaler.pkl               → StandardScaler
│   └── metrics_report.txt       → Reporte de métricas
└── notebooks/
    └── 01_exploracion_dataset.ipynb → Análisis exploratorio
```

## 🎯 Dataset

**Datos actuales**: 9,000 muestras del sensor MPU6050
- **drinking.csv**: 3,000 muestras
- **driving.csv**: 3,000 muestras  
- **throwing.csv**: 3,000 muestras

**Características**: ax, ay, az (aceleración en g), gx, gy, gz (giroscopio)

## 🚀 Pipeline de Entrenamiento

### Opción 1: Pipeline Completo (Recomendado)

```bash
cd ml
python scripts/03_train.py --full-pipeline
```

### Opción 2: Paso a Paso

```bash
# 1. Preparar datos (combina CSVs, limpia outliers)
python scripts/01_prepare_data.py

# 2. Extraer características (ventanas de 50 muestras, 25 features)
python scripts/02_extract_features.py

# 3. Entrenar modelos (Random Forest + MLP)
python scripts/03_train.py

# 4. Evaluar resultados (métricas, confusion matrix)
python scripts/04_evaluate.py
```

## 🔮 Predicción en Tiempo Real

### Uso Principal (Producción)

```bash
# Predecir desde archivo CSV del MPU6050
python scripts/predict_activity.py --csv data/raw/drinking.csv

# Limitar ventanas procesadas
python scripts/predict_activity.py --csv data/raw/driving.csv --max-windows 10

# Ver características extraídas
python scripts/predict_activity.py --csv data/raw/throwing.csv --show-features

# Ventana personalizada
python scripts/predict_activity.py --csv data/raw/drinking.csv --window-size 100
```

### Evaluación de Accuracy

```bash
# Evaluar accuracy en todos los datos nuevos
python scripts/evaluate_new_data.py

# Analizar escalas de datos
python scripts/analyze_new_data.py
```

## 📊 Resultados del Modelo

| Modelo | Accuracy | Precision | Recall | F1-Score |
|--------|----------|-----------|--------|----------|
| **Random Forest** | **95.99%** | 96% | 96% | 96% |
| MLP | 92.85% | 93% | 93% | 93% |

**Evaluación con datos nuevos (9,000 muestras)**:
- **Accuracy Global**: 100.00%
- **Confianza Promedio**: 94.9%

## 🔧 Requisitos

```bash
# Instalar dependencias
pip install -r requirements-ml.txt
```

**Dependencias principales**:
- pandas, numpy
- scikit-learn
- joblib
- matplotlib, seaborn

## ⚙️ Configuración

### Tamaño de Ventana
- **Default**: 50 muestras
- **Modificable** en: `scripts/02_extract_features.py` (línea ~15)

### Features Extraídas (25 total)
Por cada eje (ax, ay, az):
- Media, desviación estándar
- Mínimo, máximo, rango
- RMS, energía
- Zero-crossing rate

Adicionales:
- Magnitud: sqrt(ax² + ay² + az²)

## 📝 Notas Importantes

1. **Sin Escalado Necesario**: Los datos del MPU6050 ya vienen en la escala correcta
2. **Modelo Recomendado**: Random Forest (95.99% accuracy)
3. **Ventana**: 50 muestras = ~1 segundo de datos a 50Hz
4. **Actividades**: drinking, driving, throwing

## 🎓 Uso en Producción

El script `predict_activity.py` está listo para integración con el ESP32-S3:

1. Capturar ventana de 50 muestras del sensor
2. Guardar en CSV con columnas: ax, ay, az
3. Ejecutar predicción
4. Obtener actividad y confianza
