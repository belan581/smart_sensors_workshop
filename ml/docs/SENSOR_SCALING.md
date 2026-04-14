# Escalado de Datos del Sensor ESP32-S3

## 📊 Problema Identificado

Los datos del sensor ESP32-S3 vienen en unidades de **g (gravedad)**, mientras que el dataset de entrenamiento usa una escala diferente. Esto requiere un escalado antes de aplicar el modelo.

## ✅ Solución Implementada

Se creó `SensorDataScaler` que automáticamente escala los datos del sensor al formato del CSV.

### Factores de Escala Calculados

```
Factor X: 50.50x
Factor Y: 32.00x  
Factor Z: 1.28x
```

## 🚀 Cómo Usar

### Opción 1: Procesar datos JSON directamente

```python
from sensor_data_scaler import SensorDataScaler

# Tu JSON del sensor
sensor_data = {
    "id": 1190,
    "device_id": "esp32s3_001",
    "ax": [0.1831, 0.1855, 0.1838, ...],
    "ay": [0.0468, 0.0473, 0.0478, ...],
    "az": [1.0908, 1.0925, 1.0930, ...],
    "temperature": 32.8,
    "battery": 100
}

# Crear escalador
scaler = SensorDataScaler()

# Escalar el paquete
scaled_df = scaler.scale_packet(sensor_data)

# Resultado: DataFrame con columnas X, Y, Z en formato CSV
print(scaled_df)
```

### Opción 2: Procesar múltiples paquetes

```python
# Lista de paquetes JSON
sensor_packets = [ ... ]  # Tus paquetes del sensor

# Escalar todos los paquetes
scaled_df = scaler.scale_json_batch(sensor_packets)
```

### Opción 3: Escalar muestras individuales

```python
# Una muestra individual
X, Y, Z = scaler.scale_sample(ax=0.1831, ay=0.0468, az=1.0908)
print(f"Escalado: X={X:.2f}, Y={Y:.2f}, Z={Z:.2f}")
# Output: Escalado: X=9.25, Y=1.50, Z=1.40
```

## 📈 Ejemplo de Conversión

**Datos originales del sensor (g):**
```
ax = 0.1831, ay = 0.0468, az = 1.0908
```

**Datos escalados (formato CSV):**
```
X = 9.25, Y = 1.50, Z = 1.40
```

## 🔄 Flujo Completo

1. **Recibir datos del sensor** → JSON con arrays de ax, ay, az
2. **Escalar con `SensorDataScaler`** → Convertir a formato CSV
3. **Extraer características** → Usar `feature_extractor.py`
4. **Predecir actividad** → Aplicar modelo entrenado

## 📂 Archivos Creados

- `scripts/sensor_data_scaler.py` - Clase principal del escalador
- `scripts/process_sensor_json.py` - Ejemplo con datos reales
- `scripts/compare_sensor_data.py` - Análisis de diferencias

## ⚙️ Scripts Disponibles

### Probar el escalador
```bash
python scripts/sensor_data_scaler.py
```

### Procesar datos JSON de ejemplo
```bash
python scripts/process_sensor_json.py
```

### Comparar datos originales
```bash
python scripts/compare_sensor_data.py
```

## 📝 Notas Importantes

- Los datos del sensor están en reposo cuando `az ≈ 1.09g` (gravedad apuntando hacia arriba)
- El escalado es **determinista** y se calcula automáticamente del CSV
- Los datos escalados son compatibles con el pipeline de ML existente
- No es necesario re-entrenar el modelo

## 🎯 Próximos Pasos

1. ✅ Escalar datos del sensor (HECHO)
2. ⏳ Extraer características de los datos escalados
3. ⏳ Aplicar el modelo entrenado para predecir actividades
4. ⏳ Integrar en el sistema ESP32-S3 para predicción en tiempo real
