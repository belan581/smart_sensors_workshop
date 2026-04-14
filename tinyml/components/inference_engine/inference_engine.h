/**
 * @file inference_engine.h
 * @brief Motor de inferencia: extrae features y clasifica movimientos.
 *
 * API en C puro para que app_main.c (C) pueda usar el modelo C++.
 * Internamente usa el RandomForest generado por micromlgen (model_rf.h).
 *
 * Clases soportadas:
 *   INFERENCE_LABEL_DRINKING  →  se publica por MQTT
 *   INFERENCE_LABEL_DRIVING   →  ignorado
 *   INFERENCE_LABEL_THROWING  →  ignorado
 */

#pragma once

#include <stdint.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

/** Etiquetas de clasificación (orden = classmap del entrenamiento) */
typedef enum {
    INFERENCE_LABEL_DRINKING = 0,
    INFERENCE_LABEL_DRIVING  = 1,
    INFERENCE_LABEL_THROWING = 2,
    INFERENCE_LABEL_UNKNOWN  = -1,
} inference_label_t;

/**
 * @brief Clasifica una ventana de aceleración.
 *
 * Extrae las 25 features estadísticas y ejecuta el RandomForest.
 *
 * @param ax        Array de n_samples valores de aceleración X (g)
 * @param ay        Array de n_samples valores de aceleración Y (g)
 * @param az        Array de n_samples valores de aceleración Z (g)
 * @param n_samples Número de muestras (debe ser SENSOR_WINDOW_SIZE)
 * @return Etiqueta predicha, o INFERENCE_LABEL_UNKNOWN si hay error.
 */
inference_label_t inference_engine_predict(
    const float *ax,
    const float *ay,
    const float *az,
    int          n_samples
);

/**
 * @brief Convierte una etiqueta a su representación en texto.
 *
 * @param label Etiqueta retornada por inference_engine_predict()
 * @return String estático ("drinking", "driving", "throwing", "unknown")
 */
const char *inference_label_to_str(inference_label_t label);

#ifdef __cplusplus
}
#endif
