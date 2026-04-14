/**
 * @file app_main.c
 * @brief Punto de entrada y orquestador principal del firmware.
 *
 * Flujo de inicialización:
 *   1. wifi_manager_init()         → prepara WiFi + BluFi provisioning
 *   2. wifi_manager_wait_connected → espera IP (hasta 30 s)
 *   3. wifi_manager_resolve_broker → resuelve IP del broker (mDNS o fallback)
 *   4. sensor_manager_init()       → init I2C + MPU6050
 *   5. mqtt_client_manager_init()  → conecta al broker MQTT
 *   6. http_diag_server_start()    → expone GET /status en puerto 80
 *   7. sensor_manager_start_task() → inicia muestreo en Core 1
 *
 * Task principal (Core 0):
 *   - Espera semáforo de ventana lista
 *   - Publica la ventana por MQTT
 *   - Repite indefinidamente
 */

#include <stdio.h>
#include <string.h>

#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"

#include "http_diag_server.h"
#include "mqtt_client_manager.h"
#include "sensor_manager.h"
#include "wifi_manager.h"

static const char *TAG = "app_main";

/* Semáforo: la tarea sensor lo libera cuando una ventana está lista */
static SemaphoreHandle_t s_window_ready_sem = NULL;

/* ── Tarea principal de publicación ─────────────────────────── */

static void _publish_task(void *pvParameters)
{
    sensor_window_t window = {0};

    ESP_LOGI(TAG, "Tarea de publicación iniciada. Esperando ventanas...");

    while (1) {
        /* Esperar hasta que el sensor_manager libere el semáforo */
        if (xSemaphoreTake(s_window_ready_sem, portMAX_DELAY) == pdTRUE) {

            /* Copiar ventana del buffer doble */
            sensor_manager_get_window(&window);

            /* Publicar solo si MQTT está conectado */
            if (mqtt_client_manager_is_connected()) {
                esp_err_t err = mqtt_client_manager_publish_window(&window);
                if (err != ESP_OK) {
                    ESP_LOGW(TAG, "No se pudo publicar la ventana #%lu",
                             window.count);
                }
            } else {
                ESP_LOGW(TAG, "MQTT desconectado — ventana #%lu descartada",
                         window.count);
            }

            /* Log periódico cada 20 ventanas (≈10 s a 50 muestras/100Hz) */
            if (window.count % 20 == 0) {
                ESP_LOGI(TAG,
                    "─── Status ─── ventana #%lu | wifi:%s | mqtt:%s | "
                    "temp:%.1f°C | heap:%lu",
                    window.count,
                    wifi_manager_is_connected()          ? "OK" : "OFF",
                    mqtt_client_manager_is_connected()   ? "OK" : "OFF",
                    window.temperature,
                    (unsigned long)esp_get_free_heap_size()
                );
            }
        }
    }
}

/* ── app_main ────────────────────────────────────────────────── */

void app_main(void)
{
    ESP_LOGI(TAG, "╔══════════════════════════════════╗");
    ESP_LOGI(TAG, "║  Smart Sensors Workshop v1.0.0   ║");
    ESP_LOGI(TAG, "║  ESP32-S3 + MPU6050 + MQTT       ║");
    ESP_LOGI(TAG, "╚══════════════════════════════════╝");

    /* ── 1. Semáforo de sincronización sensor → publish ── */
    s_window_ready_sem = xSemaphoreCreateBinary();
    if (s_window_ready_sem == NULL) {
        ESP_LOGE(TAG, "Error creando semáforo. Reiniciando...");
        esp_restart();
    }

    /* ── 2. WiFi + BluFi provisioning ─────────────────── */
    ESP_LOGI(TAG, "[1/6] Iniciando WiFi manager...");
    ESP_ERROR_CHECK(wifi_manager_init());

    ESP_LOGI(TAG, "[2/6] Esperando conexión WiFi (max %d s)...",
             WIFI_CONNECT_TIMEOUT_MS / 1000);
    bool wifi_ok = wifi_manager_wait_connected(WIFI_CONNECT_TIMEOUT_MS);

    if (!wifi_ok) {
        ESP_LOGE(TAG, "Sin conexión WiFi. Verifica credenciales con la app EspBluFi.");
        ESP_LOGE(TAG, "El sistema continuará intentando conectar...");
        /* No reiniciar: el WiFi stack reintenta en segundo plano */
    }

    /* ── 3. Resolver broker MQTT ───────────────────────── */
    char broker_ip[16] = {0};
    uint16_t broker_port = 0;

    ESP_LOGI(TAG, "[3/6] Resolviendo broker MQTT...");
    wifi_manager_resolve_broker(broker_ip, &broker_port);
    ESP_LOGI(TAG, "Broker: %s:%d", broker_ip, broker_port);

    /* ── 4. Sensor MPU6050 ─────────────────────────────── */
    ESP_LOGI(TAG, "[4/6] Inicializando MPU6050...");
    esp_err_t sensor_err = sensor_manager_init(s_window_ready_sem);
    if (sensor_err != ESP_OK) {
        ESP_LOGE(TAG, "MPU6050 no encontrado. Verifica conexiones I2C.");
        ESP_LOGE(TAG, "  SDA=GPIO%d  SCL=GPIO%d", SENSOR_SDA_GPIO, SENSOR_SCL_GPIO);
        /* Continuar sin sensor: permite probar MQTT independientemente */
    }

    /* ── 5. Cliente MQTT ───────────────────────────────── */
    ESP_LOGI(TAG, "[5/6] Conectando al broker MQTT...");
    esp_err_t mqtt_err = mqtt_client_manager_init(broker_ip, broker_port);
    if (mqtt_err != ESP_OK) {
        ESP_LOGE(TAG, "Error inicializando cliente MQTT");
    }

    /* ── 6. Servidor HTTP de diagnóstico ───────────────── */
    ESP_LOGI(TAG, "[6/6] Iniciando servidor HTTP de diagnóstico...");
    if (wifi_ok) {
        http_diag_server_start();
        ESP_LOGI(TAG, "Diagnóstico: http://%s/status", broker_ip);
    }

    /* ── 7. Iniciar tarea de sensor (Core 1) ───────────── */
    if (sensor_err == ESP_OK) {
        sensor_manager_start_task();
    }

    /* ── 8. Crear tarea de publicación (Core 0) ────────── */
    xTaskCreatePinnedToCore(
        _publish_task,
        "publish_task",
        8192,       /* Stack: 8KB — cJSON puede usar bastante stack */
        NULL,
        4,          /* Prioridad media */
        NULL,
        0           /* Core 0 */
    );

    ESP_LOGI(TAG, "Sistema listo. Publicando cada ~%d ms",
             SENSOR_WINDOW_SIZE * SENSOR_SAMPLE_PERIOD_MS);
    ESP_LOGI(TAG, "Topic: sensors/%s/raw", MQTT_DEVICE_ID);
}
