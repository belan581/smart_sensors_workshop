idf_component_register(
    SRCS "sensor_manager.c"
    INCLUDE_DIRS "."
    REQUIRES
        mpu6050
        i2cdev
        log
        freertos
)
