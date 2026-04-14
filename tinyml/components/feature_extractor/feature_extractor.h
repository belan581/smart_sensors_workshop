/**
 * @file feature_extractor.h
 * @brief Extracción de features estadísticas de una ventana IMU.
 *
 * Calcula el mismo vector de 25 features que el script Python
 * feature_extractor.py del proyecto ml/.
 *
 * Orden del vector (debe coincidir exactamente con el entrenamiento):
 *   [0–6]   ax: mean, std, min, max, range, rms, energy
 *   [7–13]  ay: mean, std, min, max, range, rms, energy
 *   [14–20] az: mean, std, min, max, range, rms, energy
 *   [21]    magnitude_mean
 *   [22]    magnitude_std
 *   [23]    magnitude_max
 *   [24]    zcr_ax
 */

#pragma once

#include <stdint.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

/** Número total de features extraídas */
#define FEATURE_COUNT   25

/**
 * @brief Extrae el vector de features de una ventana de aceleración.
 *
 * @param ax        Array de muestras de aceleración en X (n_samples valores)
 * @param ay        Array de muestras de aceleración en Y (n_samples valores)
 * @param az        Array de muestras de aceleración en Z (n_samples valores)
 * @param n_samples Número de muestras en cada array
 * @param features  Buffer de salida; debe tener al menos FEATURE_COUNT floats
 * @return ESP_OK si la extracción fue exitosa, ESP_ERR_INVALID_ARG si n_samples < 2
 */
esp_err_t feature_extractor_extract(
    const float *ax,
    const float *ay,
    const float *az,
    int          n_samples,
    float       *features
);

#ifdef __cplusplus
}
#endif
