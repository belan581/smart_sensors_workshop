/**
 * @file sensor_manager.c
 * @brief Lectura de MPU6050 y acumulación de ventanas de datos.
 */

#include "sensor_manager.h"

#include <string.h>

#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "i2cdev.h"
#include "mpu6050.h"

static const char *TAG = "sensor_manager";

/* ── Variables de módulo ────────────────────────────────────── */

static mpu6050_dev_t     s_mpu_dev       = {0};
static bool              s_ready         = false;
static SemaphoreHandle_t s_window_sem    = NULL;

/* Doble buffer: uno se llena mientras el otro se lee */
static sensor_window_t   s_buf_a         = {0};
static sensor_window_t   s_buf_b         = {0};
static sensor_window_t  *s_fill_buf      = &s_buf_a;  /* buffer en llenado */
static sensor_window_t  *s_ready_buf     = &s_buf_b;  /* buffer listo para leer */
static uint16_t          s_sample_idx    = 0;
static uint32_t          s_window_count  = 0;

/* ── Tarea de muestreo ──────────────────────────────────────── */

static void _sensor_task(void *pvParameters)
{
    ESP_LOGI(TAG, "Tarea de muestreo iniciada (%d Hz)", SENSOR_SAMPLE_RATE_HZ);

    TickType_t last_wake = xTaskGetTickCount();

    while (1) {
        /* Esperar al próximo período de muestreo (timing preciso) */
        vTaskDelayUntil(&last_wake, pdMS_TO_TICKS(SENSOR_SAMPLE_PERIOD_MS));

        if (!s_ready) continue;

        /* Leer aceleración y temperatura */
        mpu6050_acceleration_t accel = {0};
        mpu6050_rotation_t     gyro  = {0};  /* requerido aunque no se use */
        float temperature = 0.0f;

        esp_err_t err = mpu6050_get_motion(&s_mpu_dev, &accel, &gyro);
        if (err != ESP_OK) {
            ESP_LOGW(TAG, "Error leyendo aceleración: %s", esp_err_to_name(err));
            continue;
        }
        mpu6050_get_temperature(&s_mpu_dev, &temperature);

        /* Guardar muestra en el buffer de llenado */
        s_fill_buf->ax[s_sample_idx] = accel.x;
        s_fill_buf->ay[s_sample_idx] = accel.y;
        s_fill_buf->az[s_sample_idx] = accel.z;
        s_sample_idx++;

        /* Cuando la ventana está completa, hacer swap de buffers */
        if (s_sample_idx >= SENSOR_WINDOW_SIZE) {
            s_sample_idx = 0;
            s_window_count++;

            /* Guardar temperatura (promedio de la ventana sería más preciso,
               pero para el taller usamos el último valor) */
            s_fill_buf->temperature = temperature;
            s_fill_buf->count       = s_window_count;

            /* Swap: el buffer lleno pasa a ready, el otro empieza a llenarse */
            sensor_window_t *tmp = s_fill_buf;
            s_fill_buf  = s_ready_buf;
            s_ready_buf = tmp;

            /* Notificar a app_main que hay una ventana lista */
            xSemaphoreGive(s_window_sem);

            ESP_LOGD(TAG, "Ventana #%lu lista", s_window_count);
        }
    }
}

/* ── API pública ─────────────────────────────────────────────── */

esp_err_t sensor_manager_init(SemaphoreHandle_t window_ready_sem)
{
    s_window_sem = window_ready_sem;

    /* Inicializar bus I2C */
    ESP_ERROR_CHECK(i2cdev_init());

    /* Inicializar descriptor del MPU6050 */
    ESP_ERROR_CHECK(mpu6050_init_desc(
        &s_mpu_dev,
        MPU6050_I2C_ADDRESS_LOW,  /* AD0 = GND */
        SENSOR_I2C_PORT,
        SENSOR_SDA_GPIO,
        SENSOR_SCL_GPIO
    ));

    /* Verificar presencia del sensor */
    esp_err_t probe = i2c_dev_probe(&s_mpu_dev.i2c_dev, I2C_DEV_WRITE);
    if (probe != ESP_OK) {
        ESP_LOGE(TAG, "MPU6050 no encontrado en I2C (SDA=%d SCL=%d)",
                 SENSOR_SDA_GPIO, SENSOR_SCL_GPIO);
        ESP_LOGE(TAG, "Verifica conexiones y dirección I2C");
        return ESP_ERR_NOT_FOUND;
    }

    ESP_LOGI(TAG, "MPU6050 detectado");

    /* Inicializar sensor */
    ESP_ERROR_CHECK(mpu6050_init(&s_mpu_dev));

    ESP_LOGI(TAG, "Rango acelerómetro: %d | Rango giroscopio: %d",
             s_mpu_dev.ranges.accel, s_mpu_dev.ranges.gyro);

    s_ready = true;
    ESP_LOGI(TAG, "sensor_manager inicializado OK (ventana: %d muestras @ %d Hz)",
             SENSOR_WINDOW_SIZE, SENSOR_SAMPLE_RATE_HZ);

    return ESP_OK;
}

void sensor_manager_start_task(void)
{
    xTaskCreatePinnedToCore(
        _sensor_task,
        "sensor_task",
        4096,       /* Stack: 4KB, suficiente para la lectura MPU */
        NULL,
        5,          /* Prioridad alta para mantener timing preciso */
        NULL,
        1           /* Core 1 — Core 0 lo usa el stack WiFi/BT */
    );
    ESP_LOGI(TAG, "Tarea de sensor iniciada en Core 1");
}

void sensor_manager_get_window(sensor_window_t *window)
{
    memcpy(window, s_ready_buf, sizeof(sensor_window_t));
}

bool sensor_manager_is_ready(void)
{
    return s_ready;
}
