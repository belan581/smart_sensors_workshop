/**
 * @file http_diag_server.c
 * @brief Implementación del servidor HTTP de diagnóstico.
 */

#include "http_diag_server.h"

#include <stdio.h>
#include <time.h>

#include "cJSON.h"
#include "esp_http_server.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "mqtt_client_manager.h"
#include "sensor_manager.h"

static const char *TAG        = "http_diag";
static httpd_handle_t s_server = NULL;
static time_t s_start_time     = 0;

/* ── Handler de GET /status ─────────────────────────────────── */

static esp_err_t _status_handler(httpd_req_t *req)
{
    /* Construir JSON de estado */
    cJSON *root = cJSON_CreateObject();

    cJSON_AddStringToObject(root, "device_id", MQTT_DEVICE_ID);

    /* IP del dispositivo */
    esp_netif_ip_info_t ip_info = {0};
    esp_netif_t *netif = esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");
    if (netif) {
        esp_netif_get_ip_info(netif, &ip_info);
        char ip_str[16];
        snprintf(ip_str, sizeof(ip_str), IPSTR, IP2STR(&ip_info.ip));
        cJSON_AddStringToObject(root, "ip", ip_str);
    } else {
        cJSON_AddStringToObject(root, "ip", "0.0.0.0");
    }

    /* Estado de subsistemas */
    cJSON_AddBoolToObject(root, "wifi_connected",
                          (ip_info.ip.addr != 0));
    cJSON_AddBoolToObject(root, "mqtt_connected",
                          mqtt_client_manager_is_connected());
    cJSON_AddBoolToObject(root, "sensor_ready",
                          sensor_manager_is_ready());
    cJSON_AddNumberToObject(root, "windows_published",
                            (double)mqtt_client_manager_get_publish_count());

    /* Uptime */
    time_t now;
    time(&now);
    cJSON_AddNumberToObject(root, "uptime_s", (double)(now - s_start_time));

    /* Memoria libre */
    cJSON_AddNumberToObject(root, "free_heap",
                            (double)esp_get_free_heap_size());

    /* Versión del firmware (se puede personalizar) */
    cJSON_AddStringToObject(root, "firmware_version", "1.0.0");
    cJSON_AddStringToObject(root, "workshop", "smart_sensors_workshop");

    /* Serializar y enviar */
    char *json_str = cJSON_Print(root);
    cJSON_Delete(root);

    if (json_str == NULL) {
        httpd_resp_send_500(req);
        return ESP_FAIL;
    }

    httpd_resp_set_type(req, "application/json");
    /* Permitir acceso desde navegador en cualquier origen */
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    httpd_resp_sendstr(req, json_str);
    free(json_str);

    return ESP_OK;
}

/* ── Handler de GET / ────────────────────────────────────────── */

static esp_err_t _root_handler(httpd_req_t *req)
{
    const char *html =
        "<!DOCTYPE html><html><body>"
        "<h2>ESP32-S3 Smart Sensor</h2>"
        "<p><a href='/status'>GET /status</a> — Estado del dispositivo en JSON</p>"
        "<p>Device ID: " MQTT_DEVICE_ID "</p>"
        "</body></html>";
    httpd_resp_set_type(req, "text/html");
    httpd_resp_sendstr(req, html);
    return ESP_OK;
}

/* ── URI handlers ────────────────────────────────────────────── */

static const httpd_uri_t uri_status = {
    .uri      = "/status",
    .method   = HTTP_GET,
    .handler  = _status_handler,
    .user_ctx = NULL,
};

static const httpd_uri_t uri_root = {
    .uri      = "/",
    .method   = HTTP_GET,
    .handler  = _root_handler,
    .user_ctx = NULL,
};

/* ── API pública ─────────────────────────────────────────────── */

esp_err_t http_diag_server_start(void)
{
    time(&s_start_time);    /* Guardar tiempo de arranque para uptime */

    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.server_port    = 80;
    config.max_uri_handlers = 4;

    if (httpd_start(&s_server, &config) != ESP_OK) {
        ESP_LOGE(TAG, "Error iniciando servidor HTTP");
        return ESP_FAIL;
    }

    httpd_register_uri_handler(s_server, &uri_root);
    httpd_register_uri_handler(s_server, &uri_status);

    ESP_LOGI(TAG, "Servidor HTTP de diagnóstico iniciado");
    ESP_LOGI(TAG, "  → http://{ip_esp32}/status");

    return ESP_OK;
}

void http_diag_server_stop(void)
{
    if (s_server) {
        httpd_stop(s_server);
        s_server = NULL;
        ESP_LOGI(TAG, "Servidor HTTP detenido");
    }
}
