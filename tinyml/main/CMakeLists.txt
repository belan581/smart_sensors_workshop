idf_component_register(
    SRCS        "app_main.c"
    INCLUDE_DIRS "."
    REQUIRES
        wifi_manager
        sensor_manager
        mqtt_client_manager
        inference_engine
)
