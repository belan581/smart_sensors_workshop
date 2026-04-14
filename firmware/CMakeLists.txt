cmake_minimum_required(VERSION 3.16)

# Registrar componentes propios del proyecto
set(EXTRA_COMPONENT_DIRS
    "${CMAKE_CURRENT_SOURCE_DIR}/components/wifi_manager"
    "${CMAKE_CURRENT_SOURCE_DIR}/components/sensor_manager"
    "${CMAKE_CURRENT_SOURCE_DIR}/components/mqtt_client_manager"
    "${CMAKE_CURRENT_SOURCE_DIR}/components/http_diag_server"
)

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(firmware)
