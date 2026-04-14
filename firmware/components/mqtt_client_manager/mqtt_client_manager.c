/**
 * @file mqtt_client_manager.c
 * @brief Implementación del cliente MQTT con reconexión automática.
 */

#include "mqtt_client_manager.h"

#include <stdio.h>
#include <string.h>
#include <time.h>

#include "cJSON.h"
#include "esp_log.h"
#include "mqtt_client.h"
#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"

static const char *TAG = "mqtt_client";

/* ── Variables de módulo ────────────────────────────────────── */

static esp_mqtt_client_handle_t s_client        = NULL;
static bool                     s_connected     = false;
static uint32_t                 s_publish_count = 0;

/* Topic de publicación: sensors/{device_id}/raw */
static char s_topic_raw[64];

/* ── Callback de eventos MQTT ───────────────────────────────── */

static void _mqtt_event_handler(void *handler_args,
                                esp_event_base_t base,
                                int32_t event_id,
                                void *event_data)
{
    esp_mqtt_event_handle_t event = (esp_mqtt_event_handle_t)event_data;

    switch (event->event_id) {
    case MQTT_EVENT_CONNECTED:
        s_connected = true;
        ESP_LOGI(TAG, "Conectado al broker MQTT");
        /* Publicar mensaje de estado al conectar */
        esp_mqtt_client_publish(
            s_client,
            "sensors/" MQTT_DEVICE_ID "/status",
            "{\"status\":\"online\",\"device\":\"" MQTT_DEVICE_ID "\"}",
            0, 1, 1   /* qos=1, retain=1 para que el broker lo guarde */
        );
        break;

    case MQTT_EVENT_DISCONNECTED:
        s_connected = false;
        ESP_LOGW(TAG, "Desconectado del broker. Reconectando...");
        break;

    case MQTT_EVENT_PUBLISHED:
        ESP_LOGD(TAG, "Mensaje publicado (msg_id=%d)", event->msg_id);
        break;

    case MQTT_EVENT_ERROR:
        ESP_LOGE(TAG, "Error MQTT: tipo=%d", event->error_handle->error_type);
        break;

    default:
        break;
    }
}

/* ── Serialización JSON ─────────────────────────────────────── */

/**
 * Construye el payload JSON de una ventana.
 * El caller debe llamar cJSON_Delete() en el objeto retornado.
 */
static cJSON *_build_payload(const sensor_window_t *window)
{
    cJSON *root = cJSON_CreateObject();
    if (root == NULL) return NULL;

    /* Metadata */
    cJSON_AddStringToObject(root, "device_id", MQTT_DEVICE_ID);

    /* Timestamp UNIX — requiere que el ESP32 tenga SNTP configurado.
       Para el taller usamos el contador de ventanas si no hay SNTP. */
    time_t now;
    time(&now);
    cJSON_AddNumberToObject(root, "timestamp", (double)now);

    /* Arrays de aceleración */
    cJSON *ax_arr = cJSON_CreateArray();
    cJSON *ay_arr = cJSON_CreateArray();
    cJSON *az_arr = cJSON_CreateArray();

    if (ax_arr == NULL || ay_arr == NULL || az_arr == NULL) {
        cJSON_Delete(root);
        return NULL;
    }

    for (int i = 0; i < SENSOR_WINDOW_SIZE; i++) {
        /* Redondear a 4 decimales para reducir tamaño del payload */
        cJSON_AddItemToArray(ax_arr, cJSON_CreateNumber(
            (double)((int)(window->ax[i] * 10000)) / 10000.0));
        cJSON_AddItemToArray(ay_arr, cJSON_CreateNumber(
            (double)((int)(window->ay[i] * 10000)) / 10000.0));
        cJSON_AddItemToArray(az_arr, cJSON_CreateNumber(
            (double)((int)(window->az[i] * 10000)) / 10000.0));
    }

    cJSON_AddItemToObject(root, "ax", ax_arr);
    cJSON_AddItemToObject(root, "ay", ay_arr);
    cJSON_AddItemToObject(root, "az", az_arr);

    /* Datos adicionales */
    cJSON_AddNumberToObject(root, "temperature",
                            (double)((int)(window->temperature * 10)) / 10.0);

    /* battery: placeholder — implementar con ADC si el hardware lo soporta */
    cJSON_AddNumberToObject(root, "battery", 100);

    return root;
}

/* ── API pública ─────────────────────────────────────────────── */

esp_err_t mqtt_client_manager_init(const char *broker_ip, uint16_t broker_port)
{
    /* Construir topic de publicación */
    snprintf(s_topic_raw, sizeof(s_topic_raw),
             "sensors/%s/raw", MQTT_DEVICE_ID);

    /* Construir URI del broker */
    char broker_uri[64];
    snprintf(broker_uri, sizeof(broker_uri),
             "mqtt://%s:%d", broker_ip, broker_port);

    ESP_LOGI(TAG, "Conectando a broker: %s", broker_uri);
    ESP_LOGI(TAG, "Topic de publicación: %s", s_topic_raw);

    /* LWT (Last Will and Testament): mensaje automático al desconectarse */
    const esp_mqtt_client_config_t mqtt_cfg = {
        .broker.address.uri = broker_uri,
        .credentials.client_id = MQTT_DEVICE_ID,
        .session.last_will = {
            .topic = "sensors/" MQTT_DEVICE_ID "/status",
            .msg   = "{\"status\":\"offline\",\"device\":\"" MQTT_DEVICE_ID "\"}",
            .qos   = 1,
            .retain = 1,
        },
        .network.reconnect_timeout_ms = 5000,
        .network.timeout_ms = 10000,
    };

    s_client = esp_mqtt_client_init(&mqtt_cfg);
    if (s_client == NULL) {
        ESP_LOGE(TAG, "Error inicializando cliente MQTT");
        return ESP_FAIL;
    }

    ESP_ERROR_CHECK(esp_mqtt_client_register_event(
        s_client, ESP_EVENT_ANY_ID, _mqtt_event_handler, NULL));
    ESP_ERROR_CHECK(esp_mqtt_client_start(s_client));

    return ESP_OK;
}

esp_err_t mqtt_client_manager_publish_window(const sensor_window_t *window)
{
    if (!s_connected) {
        ESP_LOGW(TAG, "Sin conexión MQTT — descartando ventana #%lu",
                 window->count);
        return ESP_ERR_INVALID_STATE;
    }

    /* Construir JSON */
    cJSON *payload = _build_payload(window);
    if (payload == NULL) {
        ESP_LOGE(TAG, "Error construyendo JSON");
        return ESP_ERR_NO_MEM;
    }

    char *json_str = cJSON_PrintUnformatted(payload);
    cJSON_Delete(payload);

    if (json_str == NULL) {
        ESP_LOGE(TAG, "Error serializando JSON");
        return ESP_ERR_NO_MEM;
    }

    /* Publicar */
    int msg_id = esp_mqtt_client_publish(
        s_client,
        s_topic_raw,
        json_str,
        0,                   /* len=0 → calcula longitud automáticamente */
        MQTT_PUBLISH_QOS,
        0                    /* retain=0 */
    );

    free(json_str);

    if (msg_id < 0) {
        ESP_LOGE(TAG, "Error publicando mensaje");
        return ESP_FAIL;
    }

    s_publish_count++;
    ESP_LOGI(TAG, "Ventana #%lu publicada → %s (msg_id=%d, %d muestras)",
             window->count, s_topic_raw, msg_id, SENSOR_WINDOW_SIZE);

    return ESP_OK;
}

bool mqtt_client_manager_is_connected(void)
{
    return s_connected;
}

uint32_t mqtt_client_manager_get_publish_count(void)
{
    return s_publish_count;
}
