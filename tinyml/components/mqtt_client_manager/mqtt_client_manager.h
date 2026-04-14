/**
 * @file mqtt_client_manager.h
 * @brief Cliente MQTT para publicar ventanas de datos al broker local.
 *
 * Payload JSON publicado en topic: sensors/{device_id}/raw
 *
 * {
 *   "device_id": "esp32s3_001",
 *   "timestamp": 1712345678,
 *   "ax": [0.01, -0.02, ...],   // SENSOR_WINDOW_SIZE valores
 *   "ay": [...],
 *   "az": [...],
 *   "temperature": 28.5,
 *   "battery": 92
 * }
 */

#pragma once

#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"
#include "sensor_manager.h"

#ifdef __cplusplus
extern "C" {
#endif

/** Identificador único del dispositivo (cambia por nodo en el taller) */
#define MQTT_DEVICE_ID          "esp32s3_001"

/** QoS 1: el broker confirma la recepción */
#define MQTT_PUBLISH_QOS        1

/**
 * @brief Inicializa el cliente MQTT y conecta al broker.
 *
 * @param broker_ip  IP del broker (ej: "192.168.1.100")
 * @param broker_port Puerto del broker (ej: 1883)
 * @return ESP_OK si se inició la conexión correctamente.
 */
esp_err_t mqtt_client_manager_init(const char *broker_ip, uint16_t broker_port);

/**
 * @brief Publica una ventana de datos al broker MQTT.
 *
 * Serializa la ventana como JSON y publica en sensors/{device_id}/raw.
 * Si el cliente no está conectado, descarta el mensaje.
 *
 * @param window Ventana de datos a publicar.
 * @return ESP_OK si el mensaje fue encolado para envío.
 */
esp_err_t mqtt_client_manager_publish_window(const sensor_window_t *window);

/**
 * @brief Retorna true si el cliente está conectado al broker.
 */
bool mqtt_client_manager_is_connected(void);

/**
 * @brief Retorna el número total de mensajes publicados.
 */
uint32_t mqtt_client_manager_get_publish_count(void);

/**
 * @brief Publica un evento de movimiento "drinking" al broker MQTT.
 *
 * Topic: sensors/{device_id}/drinking
 * Payload: {"device_id":"...","label":"drinking","timestamp":...,"temperature":...}
 *
 * @param temperature Temperatura del MPU6050 en el momento de la detección.
 * @param window_count Número de ventana (para correlacionar en el backend).
 * @return ESP_OK si el mensaje fue encolado, ESP_ERR_INVALID_STATE si no conectado.
 */
esp_err_t mqtt_client_manager_publish_drinking(float temperature, uint32_t window_count);

#ifdef __cplusplus
}
#endif
