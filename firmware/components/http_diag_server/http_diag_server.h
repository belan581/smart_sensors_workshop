/**
 * @file http_diag_server.h
 * @brief Servidor HTTP de diagnóstico embebido en el ESP32.
 *
 * Expone un endpoint GET /status que retorna un JSON con el estado
 * actual del dispositivo. Útil para verificar conectividad y estado
 * del sistema durante el taller sin necesitar el monitor serie.
 *
 * Ejemplo de respuesta:
 * {
 *   "device_id": "esp32s3_001",
 *   "ip": "192.168.1.42",
 *   "wifi_connected": true,
 *   "mqtt_connected": true,
 *   "sensor_ready": true,
 *   "windows_published": 142,
 *   "uptime_s": 3621,
 *   "free_heap": 248320
 * }
 *
 * Acceso: http://{ip_del_esp32}/status
 */

#pragma once

#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Inicia el servidor HTTP de diagnóstico en el puerto 80.
 *
 * Debe llamarse después de que WiFi esté conectado.
 *
 * @return ESP_OK si el servidor arrancó correctamente.
 */
esp_err_t http_diag_server_start(void);

/**
 * @brief Detiene el servidor HTTP.
 */
void http_diag_server_stop(void);

#ifdef __cplusplus
}
#endif
