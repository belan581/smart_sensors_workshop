idf_component_register(
    SRCS "main.c"
    INCLUDE_DIRS "."
    REQUIRES
        wifi_manager
        nvs_flash
        log
        esp_http_server
)
