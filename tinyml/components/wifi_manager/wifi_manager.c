/**
 * @file wifi_manager.c
 * @brief WiFi con provisioning BLE (ESP BLE Prov) y mDNS.
 */

#include "wifi_manager.h"

#include <string.h>

#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"
#include "freertos/task.h"
#include "mdns.h"
#include "nvs_flash.h"
#include "wifi_provisioning/manager.h"
#include "wifi_provisioning/scheme_ble.h"

/* ── Configuración ──────────────────────────────────────────── */

/* IP fallback si mDNS no resuelve el broker */
#define BROKER_FALLBACK_IP       "192.168.1.71"

/* Nombre del dispositivo visible en BLE y mDNS */
#define DEVICE_HOSTNAME          "esp32s3-sensor"

/* Prefijo del nombre BLE durante el provisioning */
#define PROV_BLE_NAME_PREFIX     "PROV_"

static const char *TAG = "wifi_manager";

/* Bits del EventGroup para sincronización */
#define WIFI_CONNECTED_BIT       BIT0
#define WIFI_FAIL_BIT            BIT1

/* ── Variables de módulo ────────────────────────────────────── */

static EventGroupHandle_t s_wifi_event_group = NULL;
static int                s_retry_count      = 0;
static bool               s_in_provisioning  = false;
#define MAX_RETRY 5

/* ── Prototipos internos ────────────────────────────────────── */

static void _wifi_event_handler(void *arg, esp_event_base_t event_base,
                                int32_t event_id, void *event_data);
static void _ip_event_handler(void *arg, esp_event_base_t event_base,
                              int32_t event_id, void *event_data);
static void _prov_event_handler(void *arg, esp_event_base_t event_base,
                                int32_t event_id, void *event_data);
static void _start_ble_provisioning(void);
static void _mdns_init(void);



/* ── Handlers de eventos WiFi/IP ────────────────────────────── */

static void _wifi_event_handler(void *arg, esp_event_base_t event_base,
                                int32_t event_id, void *event_data)
{
    if (s_in_provisioning) return;  /* el mgr de provisioning controla WiFi */

    if (event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (event_id == WIFI_EVENT_STA_DISCONNECTED) {
        if (s_retry_count < MAX_RETRY) {
            esp_wifi_connect();
            s_retry_count++;
            ESP_LOGW(TAG, "Reconectando WiFi... intento %d/%d",
                     s_retry_count, MAX_RETRY);
        } else {
            xEventGroupSetBits(s_wifi_event_group, WIFI_FAIL_BIT);
            ESP_LOGE(TAG, "No se pudo conectar al WiFi");
            /* Borrar credenciales incorrectas y reiniciar provisioning */
            ESP_LOGW(TAG, "Credenciales incorrectas. Reiniciando provisioning BLE...");
            esp_wifi_disconnect();
            wifi_prov_mgr_reset_provisioning();
            esp_restart();
        }
    }
}

static void _ip_event_handler(void *arg, esp_event_base_t event_base,
                              int32_t event_id, void *event_data)
{
    if (event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t *event = (ip_event_got_ip_t *)event_data;
        ESP_LOGI(TAG, "IP asignada: " IPSTR, IP2STR(&event->ip_info.ip));
        s_retry_count = 0;
        xEventGroupSetBits(s_wifi_event_group, WIFI_CONNECTED_BIT);
    }
}

/* ── Callback del provisioning ──────────────────────────────── */

static void _prov_event_handler(void *arg, esp_event_base_t event_base,
                                int32_t event_id, void *event_data)
{
    if (event_base == WIFI_PROV_EVENT) {
        switch (event_id) {
        case WIFI_PROV_START:
            ESP_LOGI(TAG, "[Prov] Esperando credenciales por BLE...");
            break;
        case WIFI_PROV_CRED_RECV: {
            wifi_sta_config_t *cfg = (wifi_sta_config_t *)event_data;
            ESP_LOGI(TAG, "[Prov] Credenciales recibidas: SSID=%s", cfg->ssid);
            break;
        }
        case WIFI_PROV_CRED_FAIL: {
            wifi_prov_sta_fail_reason_t *reason =
                (wifi_prov_sta_fail_reason_t *)event_data;
            ESP_LOGE(TAG, "[Prov] Fallo de conexión: %s",
                     (*reason == WIFI_PROV_STA_AUTH_ERROR)
                         ? "Contraseña incorrecta"
                         : "AP no encontrado");
            break;
        }
        case WIFI_PROV_CRED_SUCCESS:
            ESP_LOGI(TAG, "[Prov] Credenciales guardadas correctamente");
            break;
        case WIFI_PROV_END:
            ESP_LOGI(TAG, "[Prov] Provisioning finalizado");
            wifi_prov_mgr_deinit();
            s_in_provisioning = false;
            esp_wifi_connect();  /* conectar con las credenciales recién guardadas */
            break;
        default:
            break;
        }
    }
}

/* ── Iniciar provisioning BLE ────────────────────────────────── */

static void _start_ble_provisioning(void)
{
    /* Nombre BLE: "PROV_<últimos 3 bytes MAC>" */
    uint8_t mac[6];
    esp_wifi_get_mac(WIFI_IF_STA, mac);
    char ble_name[32];
    snprintf(ble_name, sizeof(ble_name), "%s%02X%02X%02X",
             PROV_BLE_NAME_PREFIX, mac[3], mac[4], mac[5]);

    wifi_prov_security_t security = WIFI_PROV_SECURITY_1;
    const char *pop = "abcd1234";  /* Proof of Possession — cámbialo si quieres */

    ESP_LOGI(TAG, "Iniciando provisioning BLE");
    ESP_LOGI(TAG, "Nombre BLE: %s", ble_name);
    ESP_LOGI(TAG, "Abre la app \"ESP BLE Prov\" en tu teléfono");
    ESP_LOGI(TAG, "PIN de emparejamiento: %s", pop);

    ESP_ERROR_CHECK(wifi_prov_mgr_start_provisioning(
        security, (const void *)pop, ble_name, NULL));
}

/* ── mDNS ────────────────────────────────────────────────────── */

static void _mdns_init(void)
{
    ESP_ERROR_CHECK(mdns_init());
    ESP_ERROR_CHECK(mdns_hostname_set(DEVICE_HOSTNAME));
    ESP_ERROR_CHECK(mdns_instance_name_set("Smart Sensor ESP32-S3"));
    ESP_LOGI(TAG, "mDNS iniciado: %s.local", DEVICE_HOSTNAME);
}

/* ── API pública ─────────────────────────────────────────────── */

esp_err_t wifi_manager_init(void)
{
    /* NVS — necesario para guardar credenciales WiFi */
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES ||
        ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_LOGW(TAG, "NVS corrupto, borrando...");
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    /* Event group para sincronización */
    s_wifi_event_group = xEventGroupCreate();

    /* Inicializar TCP/IP stack */
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();

    /* Configurar WiFi en modo STA */
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    /* Registrar handlers de eventos WiFi/IP */
    ESP_ERROR_CHECK(esp_event_handler_instance_register(
        WIFI_EVENT, ESP_EVENT_ANY_ID, &_wifi_event_handler, NULL, NULL));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(
        IP_EVENT, IP_EVENT_STA_GOT_IP, &_ip_event_handler, NULL, NULL));

    /* Configurar el gestor de provisioning con esquema BLE */
    wifi_prov_mgr_config_t prov_cfg = {
        .scheme               = wifi_prov_scheme_ble,
        .scheme_event_handler = WIFI_PROV_EVENT_HANDLER_NONE,  /* NimBLE */
    };
    ESP_ERROR_CHECK(wifi_prov_mgr_init(prov_cfg));

    /* Registrar handler de eventos de provisioning */
    ESP_ERROR_CHECK(esp_event_handler_instance_register(
        WIFI_PROV_EVENT, ESP_EVENT_ANY_ID, &_prov_event_handler, NULL, NULL));

    /* Verificar si el dispositivo ya fue provisionado */
    bool provisioned = false;
    ESP_ERROR_CHECK(wifi_prov_mgr_is_provisioned(&provisioned));

    if (!provisioned) {
        ESP_LOGI(TAG, "Sin credenciales WiFi — iniciando provisioning BLE");
        s_in_provisioning = true;
        ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
        ESP_ERROR_CHECK(esp_wifi_start());
        _start_ble_provisioning();
    } else {
        ESP_LOGI(TAG, "Credenciales encontradas en NVS — conectando...");
        wifi_prov_mgr_deinit();
        ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
        ESP_ERROR_CHECK(esp_wifi_start());
    }

    return ESP_OK;
}

bool wifi_manager_wait_connected(uint32_t timeout_ms)
{
    TickType_t ticks = pdMS_TO_TICKS(timeout_ms);
    EventBits_t bits = xEventGroupWaitBits(
        s_wifi_event_group,
        WIFI_CONNECTED_BIT | WIFI_FAIL_BIT,
        pdFALSE,          /* no limpiar bits */
        pdFALSE,          /* cualquier bit activa el retorno */
        ticks
    );

    if (bits & WIFI_CONNECTED_BIT) {
        _mdns_init();     /* iniciar mDNS una vez conectado */
        return true;
    }

    if (bits & WIFI_FAIL_BIT) {
        ESP_LOGE(TAG, "Error de conexión WiFi");
    } else {
        ESP_LOGE(TAG, "Timeout esperando conexión WiFi (%lu ms)", timeout_ms);
    }
    return false;
}

bool wifi_manager_resolve_broker(char *ip_str, uint16_t *port)
{
    esp_ip4_addr_t addr;
    /* Buscar "_mqtt._tcp" en la red local */
    esp_err_t err = mdns_query_a(MQTT_MDNS_HOSTNAME, 2000, &addr);

    if (err == ESP_OK) {
        snprintf(ip_str, 16, IPSTR, IP2STR(&addr));
        *port = MQTT_DEFAULT_PORT;
        ESP_LOGI(TAG, "Broker resuelto vía mDNS: %s:%d", ip_str, *port);
        return true;
    }

    /* Fallback: IP hardcodeada */
    ESP_LOGW(TAG, "mDNS falló (%s). Usando IP de fallback: %s",
             esp_err_to_name(err), BROKER_FALLBACK_IP);
    strlcpy(ip_str, BROKER_FALLBACK_IP, 16);
    *port = MQTT_DEFAULT_PORT;
    return false;
}

bool wifi_manager_is_connected(void)
{
    if (s_wifi_event_group == NULL) return false;
    EventBits_t bits = xEventGroupGetBits(s_wifi_event_group);
    return (bits & WIFI_CONNECTED_BIT) != 0;
}
