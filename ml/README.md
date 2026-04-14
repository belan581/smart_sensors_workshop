# ML Pipeline - Smart Sensors Workshop

Pipeline completo de entrenamiento del clasificador de movimiento.

## Estructura

```
ml/
├── notebooks/
│   └── 01_exploracion_dataset.ipynb  → EDA, visualizaciones
├── scripts/
│   ├── 01_prepare_data.py   → Carga, limpia y segmenta el dataset
│   ├── 02_extract_features.py → Extrae features por ventana
│   ├── 03_train.py          → Entrena RandomForest y/o MLP, guarda modelo
│   └── 04_evaluate.py       → Métricas, confusion matrix, comparativa
├── data/
│   ├── raw/                 → Dataset original de Kaggle (CSV sin modificar)
│   └── processed/           → Features extraídas, listas para entrenar
└── outputs/
    ├── model_rf.pkl          → Modelo RandomForest entrenado
    ├── model_mlp.pkl         → Modelo MLP entrenado
    ├── label_encoder.pkl     → Codificador de etiquetas
    ├── scaler.pkl            → StandardScaler
    └── metrics_report.txt   → Reporte de métricas comparativo
```

## Dataset

Descargar de Kaggle: `mpu6050-3-axis-acceleration-dataset`
Colocar CSV en: `ml/data/raw/`

## Ejecutar pipeline

```bash
cd ml
python scripts/01_prepare_data.py
python scripts/02_extract_features.py
python scripts/03_train.py
python scripts/04_evaluate.py
```

O ejecutar todo junto:

```bash
python scripts/03_train.py --full-pipeline
```
