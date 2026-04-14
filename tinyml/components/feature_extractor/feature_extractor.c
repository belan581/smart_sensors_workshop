/**
 * @file feature_extractor.c
 * @brief Implementación C de las 25 features estadísticas del pipeline ML.
 *
 * Mantiene el mismo orden y cálculo que feature_extractor.py del proyecto ml/.
 */

#include "feature_extractor.h"

#include <math.h>
#include "esp_err.h"

/* ── Helpers estadísticos ────────────────────────────────────── */

static float _mean(const float *v, int n)
{
    float s = 0.0f;
    for (int i = 0; i < n; i++) s += v[i];
    return s / (float)n;
}

static float _std(const float *v, int n, float mean)
{
    float s = 0.0f;
    for (int i = 0; i < n; i++) {
        float d = v[i] - mean;
        s += d * d;
    }
    return sqrtf(s / (float)n);
}

static float _min(const float *v, int n)
{
    float m = v[0];
    for (int i = 1; i < n; i++) if (v[i] < m) m = v[i];
    return m;
}

static float _max(const float *v, int n)
{
    float m = v[0];
    for (int i = 1; i < n; i++) if (v[i] > m) m = v[i];
    return m;
}

/** energy = sum(x^2) / n  |  rms = sqrt(energy) */
static float _energy(const float *v, int n)
{
    float s = 0.0f;
    for (int i = 0; i < n; i++) s += v[i] * v[i];
    return s / (float)n;
}

/**
 * Rellena 7 features de un eje en positions [offset .. offset+6]
 * Orden: mean, std, min, max, range, rms, energy
 */
static void _axis_features(const float *v, int n, float *feat, int offset)
{
    float mn  = _mean(v, n);
    float mn2 = _min(v, n);
    float mx  = _max(v, n);
    float en  = _energy(v, n);

    feat[offset + 0] = mn;
    feat[offset + 1] = _std(v, n, mn);
    feat[offset + 2] = mn2;
    feat[offset + 3] = mx;
    feat[offset + 4] = mx - mn2;          /* range */
    feat[offset + 5] = sqrtf(en);         /* rms   */
    feat[offset + 6] = en;                /* energy */
}

/* ── API pública ─────────────────────────────────────────────── */

esp_err_t feature_extractor_extract(
    const float *ax,
    const float *ay,
    const float *az,
    int          n_samples,
    float       *features)
{
    if (n_samples < 2 || ax == NULL || ay == NULL ||
        az == NULL || features == NULL) {
        return ESP_ERR_INVALID_ARG;
    }

    /* ── Features por eje (7 × 3 = 21) ─ */
    _axis_features(ax, n_samples, features,  0);  /* ax → [0..6]  */
    _axis_features(ay, n_samples, features,  7);  /* ay → [7..13] */
    _axis_features(az, n_samples, features, 14);  /* az → [14..20] */

    /* ── Magnitud del vector 3D (3) ─── */
    float mag_sum  = 0.0f;
    float mag_sum2 = 0.0f;
    float mag_max  = 0.0f;

    for (int i = 0; i < n_samples; i++) {
        float m = sqrtf(ax[i]*ax[i] + ay[i]*ay[i] + az[i]*az[i]);
        mag_sum  += m;
        mag_sum2 += m * m;
        if (m > mag_max) mag_max = m;
    }

    float mag_mean = mag_sum / (float)n_samples;
    float mag_var  = (mag_sum2 / (float)n_samples) - (mag_mean * mag_mean);
    float mag_std  = sqrtf(mag_var < 0.0f ? 0.0f : mag_var);

    features[21] = mag_mean;  /* magnitude_mean */
    features[22] = mag_std;   /* magnitude_std  */
    features[23] = mag_max;   /* magnitude_max  */

    /* ── Tasa de cruces por cero de ax (zcr_ax) (1) ─── */
    float ax_mean = features[0];  /* ya calculado */
    int   crossings = 0;
    float prev_centered = ax[0] - ax_mean;

    for (int i = 1; i < n_samples; i++) {
        float curr_centered = ax[i] - ax_mean;
        /* Cruce cuando el signo cambia (excluyendo cero exacto) */
        if ((prev_centered > 0.0f && curr_centered < 0.0f) ||
            (prev_centered < 0.0f && curr_centered > 0.0f)) {
            crossings++;
        }
        prev_centered = curr_centered;
    }

    features[24] = (float)crossings / (float)n_samples;  /* zcr_ax */

    return ESP_OK;
}
