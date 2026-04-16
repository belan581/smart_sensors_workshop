/**
 * @file wifi_manager.h
 * @brief Gestión de WiFi con provisioning BLE (ESP BLE Prov) y mDNS.
 *
 * Flujo de uso:
 *   1. wifi_manager_init()           → inicializa WiFi + NVS + provisioning
 *   2. wifi_manager_wait_connected() → bloquea hasta tener IP (o timeout)
 *
 * Provisioning:
 *   - La primera vez (sin credenciales en NVS), el ESP32 anuncia un
 *     dispositivo BLE con nombre "PROV_XXXXXX".
 *   - Abre la app "ESP BLE Prov" en tu teléfono, selecciona el dispositivo,
 *     introduce el PIN "abcd1234" y envía las credenciales WiFi.
 *   - Las credenciales se guardan en NVS y se reusan en reinicios.
 *   - Para re-provisionar: `idf.py erase-flash`.
 *   - El dispositivo queda accesible en la red como esp32s3-sensor.local
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
 * @brief Retorna true si el dispositivo tiene dirección IP asignada.
 */
bool wifi_manager_is_connected(void);

#ifdef __cplusplus
}
#endif
