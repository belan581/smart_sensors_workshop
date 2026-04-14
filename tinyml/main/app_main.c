/**
 * @file app_main.c
 * @brief TinyML: Inferencia on-device de movimientos con ESP32-S3.
 *
 * Flujo de inicialización:
 *   1. wifi_manager_init()         → WiFi + BLE provisioning
 *   2. wifi_manager_wait_connected → espera IP (hasta 30 s)
 *   3. wifi_manager_resolve_broker → resuelve broker MQTT (mDNS o fallback)
 *   4. sensor_manager_init()       → init I2C + MPU6050
 *   5. mqtt_client_manager_init()  → conecta al broker MQTT
 *   6. sensor_manager_start_task() → muestreo en Core 1
 *
 * Tarea principal (Core 0):
 *   - Espera semáforo de ventana lista (cada ~500 ms a 50 muestras/100 Hz)
 *   - Ejecuta inferencia con el RandomForest (feature_extractor + modelo C)
 *   - Solo si el resultado es DRINKING → publica a MQTT
 *     Topic: sensors/esp32s3_001/drinking
 */

#include <stdio.h>
#include <string.h>

#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"

#include "inference_engine.h"
#include "mqtt_client_manager.h"
#include "sensor_manager.h"
#include "wifi_manager.h"

static const char *TAG = "app_main";

/* Semáforo: la tarea sensor lo libera cuando una ventana está lista */
static SemaphoreHandle_t s_window_ready_sem = NULL;

/* ── Tarea de inferencia y publicación ──────────────────────── */

static void _inference_task(void *pvParameters)
{
    sensor_window_t window = {0};

    ESP_LOGI(TAG, "Tarea de inferencia iniciada. Esperando ventanas...");

    while (1) {
        if (xSemaphoreTake(s_window_ready_sem, portMAX_DELAY) != pdTRUE) {
            continue;
        }

        /* Copiar ventana del buffer doble */
        sensor_manager_get_window(&window);

        /* Ejecutar inferencia */
        inference_label_t label = inference_engine_predict(
            window.ax, window.ay, window.az, SENSOR_WINDOW_SIZE);

        ESP_LOGI(TAG, "Ventana #%lu → %s",
                 window.count, inference_label_to_str(label));

        /* Solo publicar si se detecta DRINKING */
        if (label == INFERENCE_LABEL_DRINKING) {
            if (mqtt_client_manager_is_connected()) {
                mqtt_client_manager_publish_drinking(
                    window.temperature, window.count);
            } else {
                ESP_LOGW(TAG, "MQTT desconectado — evento drinking descartado "
                              "(ventana #%lu)", window.count);
            }
        }
    }
}

/* ── app_main ────────────────────────────────────────────────── */

void app_main(void)
{
    ESP_LOGI(TAG, "╔══════════════════════════════════════╗");
    ESP_LOGI(TAG, "║  TinyML Smart Sensors v1.0.0         ║");
    ESP_LOGI(TAG, "║  ESP32-S3 + MPU6050 + RandomForest   ║");
    ESP_LOGI(TAG, "╚══════════════════════════════════════╝");

    /* ── 1. Semáforo de sincronización sensor → inferencia ── */
    s_window_ready_sem = xSemaphoreCreateBinary();
    if (s_window_ready_sem == NULL) {
        ESP_LOGE(TAG, "Error creando semáforo. Reiniciando...");
        esp_restart();
    }

    /* ── 2. WiFi + BLE provisioning ─────────────────────── */
    ESP_LOGI(TAG, "[1/5] Iniciando WiFi manager (BLE provisioning)...");
    ESP_ERROR_CHECK(wifi_manager_init());

    ESP_LOGI(TAG, "[2/5] Esperando conexión WiFi (max %d s)...",
             WIFI_CONNECT_TIMEOUT_MS / 1000);
    bool wifi_ok = wifi_manager_wait_connected(WIFI_CONNECT_TIMEOUT_MS);
    if (!wifi_ok) {
        ESP_LOGW(TAG, "Sin WiFi. Inferencia local activa; MQTT en espera.");
    }

    /* ── 3. Resolver broker MQTT ───────────────────────────── */
    char     broker_ip[16] = {0};
    uint16_t broker_port   = 0;

    ESP_LOGI(TAG, "[3/5] Resolviendo broker MQTT...");
    wifi_manager_resolve_broker(broker_ip, &broker_port);
    ESP_LOGI(TAG, "Broker: %s:%d", broker_ip, broker_port);

    /* ── 4. Sensor MPU6050 ─────────────────────────────────── */
    ESP_LOGI(TAG, "[4/5] Inicializando MPU6050...");
    esp_err_t sensor_err = sensor_manager_init(s_window_ready_sem);
    if (sensor_err != ESP_OK) {
        ESP_LOGE(TAG, "MPU6050 no encontrado (SDA=GPIO%d SCL=GPIO%d).",
                 SENSOR_SDA_GPIO, SENSOR_SCL_GPIO);
        /* Continuar sin sensor para permitir debug de MQTT */
    }

    /* ── 5. Cliente MQTT ───────────────────────────────────── */
    ESP_LOGI(TAG, "[5/5] Conectando al broker MQTT...");
    esp_err_t mqtt_err = mqtt_client_manager_init(broker_ip, broker_port);
    if (mqtt_err != ESP_OK) {
        ESP_LOGW(TAG, "MQTT no disponible. Inferencia activa sin publicación.");
    }

    /* ── 6. Iniciar tarea de sensor (Core 1) ─────────────── */
    if (sensor_err == ESP_OK) {
        sensor_manager_start_task();
    }

    /* ── 7. Crear tarea de inferencia (Core 0) ───────────── */
    xTaskCreatePinnedToCore(
        _inference_task,
        "inference_task",
        8192,   /* 8 KB: suficiente para features + cJSON */
        NULL,
        4,
        NULL,
        0       /* Core 0 */
    );

    ESP_LOGI(TAG, "Sistema listo. Ventana: %d muestras @ %d Hz → ~%d ms/inferencia",
             SENSOR_WINDOW_SIZE,
             SENSOR_SAMPLE_RATE_HZ,
             SENSOR_WINDOW_SIZE * SENSOR_SAMPLE_PERIOD_MS);
    ESP_LOGI(TAG, "Topic MQTT: sensors/%s/drinking", MQTT_DEVICE_ID);
}
