/**
 * @file wifi_manager.h
 * @brief Gestión de WiFi con provisioning BLE (ESP BLE Prov) y mDNS.
 *
 * Flujo de uso:
 *   1. wifi_manager_init()           → inicializa WiFi + NVS + provisioning
 *   2. wifi_manager_wait_connected() → bloquea hasta tener IP (o timeout)
 *   3. wifi_manager_resolve_broker() → resuelve "mqtt.local" vía mDNS
 *
 * Provisioning:
 *   - La primera vez (sin credenciales en NVS), el ESP32 anuncia un
 *     dispositivo BLE con nombre "PROV_XXXXXX".
 *   - Abre la app "ESP BLE Prov" en tu teléfono, selecciona el dispositivo,
 *     introduce el PIN "abcd1234" y envía las credenciales WiFi.
 *   - Las credenciales se guardan en NVS y se reusan en reinicios.
 *   - Para re-provisionar: `idf.py erase-flash`.
 */

#pragma once

#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Timeout máximo esperando conexión WiFi (ms) */
#define WIFI_CONNECT_TIMEOUT_MS     30000

/* Nombre mDNS del broker MQTT en la red local */
#define MQTT_MDNS_HOSTNAME          "mqtt"

/* Puerto MQTT por defecto */
#define MQTT_DEFAULT_PORT           1883

/**
 * @brief Inicializa el stack WiFi, NVS y eventos de red.
 *
 * Debe llamarse una sola vez al arrancar, antes de cualquier otra
 * función de wifi_manager.
 *
 * @return ESP_OK si la inicialización fue exitosa.
 */
esp_err_t wifi_manager_init(void);

/**
 * @brief Bloquea hasta obtener dirección IP o hasta timeout.
 *
 * @param timeout_ms Tiempo máximo de espera en ms.
 * @return true  → conectado con IP válida.
 *         false → timeout o error.
 */
bool wifi_manager_wait_connected(uint32_t timeout_ms);

/**
 * @brief Intenta resolver la IP del broker MQTT vía mDNS.
 *
 * Busca el servicio "_mqtt._tcp.local".
 * Si mDNS falla, retorna la IP de fallback del sdkconfig.
 *
 * @param[out] ip_str Buffer donde se escribe la IP resuelta (mínimo 16 bytes).
 * @param[out] port   Puerto del broker.
 * @return true si se resolvió correctamente.
 */
bool wifi_manager_resolve_broker(char *ip_str, uint16_t *port);

/**
 * @brief Retorna true si el dispositivo tiene dirección IP asignada.
 */
bool wifi_manager_is_connected(void);

#ifdef __cplusplus
}
#endif
