/**
 * @file inference_engine.cpp
 * @brief Wrapper C++ → C que conecta el RandomForest con la app.
 *
 * model_rf.h usa namespaces y clases de C++, por lo que este
 * archivo debe compilarse como C++.  La API pública se expone en
 * C mediante extern "C" declarado en inference_engine.h.
 */

#include "inference_engine.h"
#include "feature_extractor.h"
#include "model_rf.h"   /* generado por scripts/export_model_to_c.py */

#include "esp_log.h"

static const char *TAG = "inference_engine";

/* Instancia estática del clasificador (sin memoria dinámica) */
static Eloquent::ML::Port::RandomForest s_rf;

/* ── API pública (linkada como C) ───────────────────────────── */

extern "C" inference_label_t inference_engine_predict(
    const float *ax,
    const float *ay,
    const float *az,
    int          n_samples)
{
    float features[FEATURE_COUNT];

    esp_err_t err = feature_extractor_extract(ax, ay, az, n_samples, features);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "Error extrayendo features: %s", esp_err_to_name(err));
        return INFERENCE_LABEL_UNKNOWN;
    }

    /* predict() retorna int: 0=drinking, 1=driving, 2=throwing */
    int class_idx = s_rf.predict(features);

    if (class_idx < 0 || class_idx > 2) {
        ESP_LOGW(TAG, "Clase inesperada: %d", class_idx);
        return INFERENCE_LABEL_UNKNOWN;
    }

    return static_cast<inference_label_t>(class_idx);
}

extern "C" const char *inference_label_to_str(inference_label_t label)
{
    switch (label) {
    case INFERENCE_LABEL_DRINKING: return "drinking";
    case INFERENCE_LABEL_DRIVING:  return "driving";
    case INFERENCE_LABEL_THROWING: return "throwing";
    default:                       return "unknown";
    }
}
