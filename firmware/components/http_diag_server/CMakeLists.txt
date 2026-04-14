idf_component_register(
    SRCS "http_diag_server.c"
    INCLUDE_DIRS "."
    REQUIRES
        esp_http_server
        log
        esp_wifi
        freertos
        sensor_manager
        mqtt_client_manager
)
