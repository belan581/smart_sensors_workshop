idf_component_register(
    SRCS "mqtt_client_manager.c"
    INCLUDE_DIRS "."
    REQUIRES
        mqtt
        log
        freertos
        json
        sensor_manager
)
