/**
 * @file sensor_manager.h
 * @brief Lectura de MPU6050 y acumulación de ventanas de datos.
 *
 * El sensor_manager lee el MPU6050 a la frecuencia configurada y
 * acumula las muestras en un buffer circular. Cuando el buffer
 * tiene SENSOR_WINDOW_SIZE muestras, notifica mediante un semáforo
 * para que app_main extraiga la ventana y la publique por MQTT.
 *
 * Pines I2C por defecto (ajustar en sensor_manager.c si es necesario):
 *   SDA → GPIO 8
 *   SCL → GPIO 9
 */

#pragma once

#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ── Configuración de la ventana ─────────────────────────────── */

/** Número de muestras por ventana (debe coincidir con backend/ML) */
#define SENSOR_WINDOW_SIZE      50

/** Frecuencia de muestreo en Hz */
#define SENSOR_SAMPLE_RATE_HZ   100

/** Período entre muestras en ms */
#define SENSOR_SAMPLE_PERIOD_MS (1000 / SENSOR_SAMPLE_RATE_HZ)

/* ── Pines I2C ───────────────────────────────────────────────── */
#define SENSOR_SDA_GPIO     8
#define SENSOR_SCL_GPIO     9
#define SENSOR_I2C_PORT     0

/* ── Estructura de ventana ───────────────────────────────────── */

/**
 * @brief Una ventana completa de datos del sensor.
 * Usada para transferir datos entre la tarea sensor y app_main.
 */
typedef struct {
    float ax[SENSOR_WINDOW_SIZE];   /**< Aceleración eje X (g) */
    float ay[SENSOR_WINDOW_SIZE];   /**< Aceleración eje Y (g) */
    float az[SENSOR_WINDOW_SIZE];   /**< Aceleración eje Z (g) */
    float temperature;              /**< Temperatura del MPU (°C) */
    uint32_t count;                 /**< Ventanas generadas (para debug) */
} sensor_window_t;

/**
 * @brief Inicializa el I2C y el MPU6050.
 *
 * @param window_ready_sem Semáforo que se liberará cuando haya
 *        una ventana completa lista para leer.
 * @return ESP_OK si la inicialización fue exitosa.
 */
esp_err_t sensor_manager_init(SemaphoreHandle_t window_ready_sem);

/**
 * @brief Inicia la tarea FreeRTOS de muestreo.
 * Debe llamarse después de sensor_manager_init().
 */
void sensor_manager_start_task(void);

/**
 * @brief Copia la última ventana completa en el buffer destino.
 *
 * Debe llamarse cuando el semáforo window_ready_sem fue tomado.
 *
 * @param[out] window Buffer de destino.
 */
void sensor_manager_get_window(sensor_window_t *window);

/**
 * @brief Retorna true si el MPU6050 fue detectado y está operativo.
 */
bool sensor_manager_is_ready(void);

#ifdef __cplusplus
}
#endif
