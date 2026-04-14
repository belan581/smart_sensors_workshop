cmake_minimum_required(VERSION 3.16)

set(EXTRA_COMPONENT_DIRS
    "${CMAKE_CURRENT_SOURCE_DIR}/components/wifi_manager"
    "${CMAKE_CURRENT_SOURCE_DIR}/components/sensor_manager"
    "${CMAKE_CURRENT_SOURCE_DIR}/components/mqtt_client_manager"
    "${CMAKE_CURRENT_SOURCE_DIR}/components/feature_extractor"
    "${CMAKE_CURRENT_SOURCE_DIR}/components/inference_engine"
)

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(tinyml)
