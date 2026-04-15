/**
 * @file app_main.c
 * @brief Firmware de captura de datos MPU6050 para reconocimiento de gestos.
 *
 * Protocolo serie (UART0 / USB):
 *   PC → ESP32 : "START drinking\n"  |  "START driving\n"  |  "START throwing\n"
 *   ESP32 → PC : "READY <gesto>\n"   (grabación comienza inmediatamente)
 *   ESP32 → PC : 3000 líneas CSV  "ax,ay,az,gx,gy,gz\n"
 *   ESP32 → PC : "DONE\n"
 *
 * Parámetros:
 *   - Frecuencia de muestreo : 1 KHz  (CONFIG_FREERTOS_HZ=1000)
 *   - Muestras por grabación : 3000   (3 segundos)
 *   - I2C SDA / SCL          : GPIO 8 / GPIO 9
 *   - I2C frecuencia         : 1 MHz  (por defecto del driver mpu6050)
 *
 * Unidades de salida:
 *   ax, ay, az  →  g  (gravedad)
 *   gx, gy, gz  →  °/s
 *
 * NOTA sobre el console en ESP32-S3:
 *   COM7 = USB Serial/JTAG CDC. Se usa el driver usb_serial_jtag con
 *   ring-buffers propios (RX/TX). getchar()/printf() sin driver instalado
 *   solo hacen polling y pierden bytes, por eso se usan las APIs directas:
 *     usb_serial_jtag_read_bytes()  ← recibir comandos del PC
 *     usb_serial_jtag_write_bytes() → enviar datos al PC
 */

#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#include "driver/usb_serial_jtag.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "i2cdev.h"
#include "mpu6050.h"

static const char *TAG = "getdata";

/* ── Parámetros de captura ──────────────────────────────────── */
#define SAMPLE_RATE_HZ   1000
#define SAMPLES_PER_REC  3000   /**< 1 KHz × 3 s */
#define SDA_GPIO         8
#define SCL_GPIO         9
#define I2C_PORT         0

/* ── Estructura de una muestra ──────────────────────────────── */
typedef struct {
    float ax, ay, az;   /**< Aceleración (g)   */
    float gx, gy, gz;   /**< Giroscopio (°/s)  */
} sample_t;

/* ── Buffer estático: 3000 × 24 bytes = 72 KB ───────────────── */
static sample_t s_buf[SAMPLES_PER_REC];

/* ── Estado global ──────────────────────────────────────────── */
static mpu6050_dev_t     s_mpu      = {0};
static SemaphoreHandle_t s_start_sem = NULL;
static char              s_gesture[32] = {0};

/* ── Enviar string por USB-JTAG CDC ─────────────────────────── */
static void usb_send(const char *str)
{
    usb_serial_jtag_write_bytes(str, strlen(str), pdMS_TO_TICKS(100));
}

/* Versión con formato (buffer de 64 bytes, suficiente para una línea CSV) */
static void usb_printf(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
static void usb_printf(const char *fmt, ...)
{
    char buf[64];
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    if (n > 0) {
        usb_serial_jtag_write_bytes(buf, (size_t)n, pdMS_TO_TICKS(100));
    }
}

/* ── Leer una línea por USB-JTAG CDC ──────────────────────── */
static bool read_line(char *buf, int maxlen)
{
    int i = 0;
    uint8_t c;

    while (i < maxlen - 1) {
        int n = usb_serial_jtag_read_bytes(&c, 1, pdMS_TO_TICKS(10));
        if (n <= 0) continue;
        if (c == '\r') continue;  /* ignorar CR (Windows \r\n) */
        if (c == '\n') break;
        buf[i++] = (char)c;
    }
    buf[i] = '\0';
    return (i > 0);
}

/* ── Tarea de muestreo y envío (Core 1, alta prioridad) ─────── */
static void sensor_task(void *pv)
{
    TickType_t last_wake;

    ESP_LOGI(TAG, "Tarea sensor lista. Esperando comandos...");

    while (1) {
        /* Esperar señal de la tarea de comandos */
        xSemaphoreTake(s_start_sem, portMAX_DELAY);

        /* Confirmar al script Python que la grabación empieza */
        usb_printf("READY %s\n", s_gesture);

        /* ── Fase de grabación: 3000 muestras a 1 KHz ── */
        last_wake = xTaskGetTickCount();

        for (int i = 0; i < SAMPLES_PER_REC; i++) {
            /* Esperar al próximo tick de 1 ms */
            vTaskDelayUntil(&last_wake, pdMS_TO_TICKS(1));

            mpu6050_acceleration_t accel = {0};
            mpu6050_rotation_t     gyro  = {0};

            if (mpu6050_get_motion(&s_mpu, &accel, &gyro) == ESP_OK) {
                s_buf[i].ax = accel.x;
                s_buf[i].ay = accel.y;
                s_buf[i].az = accel.z;
                s_buf[i].gx = gyro.x;
                s_buf[i].gy = gyro.y;
                s_buf[i].gz = gyro.z;
            }
        }

        /* ── Fase de envío: volcar buffer completo por USB-CDC ── */
        for (int i = 0; i < SAMPLES_PER_REC; i++) {
            usb_printf("%.4f,%.4f,%.4f,%.4f,%.4f,%.4f\n",
                       s_buf[i].ax, s_buf[i].ay, s_buf[i].az,
                       s_buf[i].gx, s_buf[i].gy, s_buf[i].gz);
        }

        usb_send("DONE\n");

        ESP_LOGI(TAG, "Grabación '%s' completada y enviada.", s_gesture);
    }
}

/* ── Tarea de comandos (Core 0) ──────────────────────────────── */
static void command_task(void *pv)
{
    char line[64];

    ESP_LOGI(TAG, "Comandos: START drinking | START driving | START throwing");

    while (1) {
        if (!read_line(line, sizeof(line))) {
            continue;
        }

        /* Parsear "START <gesto>" */
        if (strncmp(line, "START ", 6) != 0) {
            continue;
        }

        const char *g = line + 6;

        if (strcmp(g, "drinking") == 0 ||
            strcmp(g, "driving")  == 0 ||
            strcmp(g, "throwing") == 0)
        {
            strncpy(s_gesture, g, sizeof(s_gesture) - 1);
            s_gesture[sizeof(s_gesture) - 1] = '\0';
            xSemaphoreGive(s_start_sem);
        } else {
            usb_printf("ERROR gesto desconocido: %s\n", g);
        }
    }
}

/* ── Punto de entrada ────────────────────────────────────────── */
void app_main(void)
{
    /* ── Instalar driver USB Serial/JTAG ──────────────────────────────
     * Sin driver, getchar/printf usan polling directo de registros HW
     * y pierden bytes bajo carga. El driver instala ring-buffers con
     * ISR y hace la comunicación robusta. */
    {
        usb_serial_jtag_driver_config_t usb_cfg = {
            .rx_buffer_size = 512,
            .tx_buffer_size = 4096,   /* Buffer TX grande: 3000 líneas CSV */
        };
        usb_serial_jtag_driver_install(&usb_cfg);
    }

    ESP_LOGI(TAG, "=== GetData Firmware — MPU6050 @ 1 KHz ===");
    ESP_LOGI(TAG, "SDA=GPIO%d  SCL=GPIO%d  I2C_PORT=%d", SDA_GPIO, SCL_GPIO, I2C_PORT);

    /* ── Inicializar bus I2C ── */
    ESP_ERROR_CHECK(i2cdev_init());

    /* ── Inicializar descriptor MPU6050 ── */
    ESP_ERROR_CHECK(mpu6050_init_desc(
        &s_mpu,
        MPU6050_I2C_ADDRESS_LOW,   /* AD0 = GND → 0x68 */
        I2C_PORT,
        SDA_GPIO,
        SCL_GPIO
    ));

    /* ── Verificar presencia del sensor ── */
    if (i2c_dev_probe(&s_mpu.i2c_dev, I2C_DEV_WRITE) != ESP_OK) {
        ESP_LOGE(TAG, "MPU6050 no encontrado — verifica SDA=%d SCL=%d y alimentación",
                 SDA_GPIO, SCL_GPIO);
        return;
    }

    /* ── Inicializar sensor (rango accel ±2g, giroscopio ±250°/s) ── */
    ESP_ERROR_CHECK(mpu6050_init(&s_mpu));
    ESP_LOGI(TAG, "MPU6050 OK");

    /* ── Señal al script Python: firmware listo para recibir comandos ── */
    usb_send("FIRMWARE_OK\n");

    /* ── Semáforo binario de disparo ── */
    s_start_sem = xSemaphoreCreateBinary();
    configASSERT(s_start_sem);

    /* ── Crear tareas ── */
    xTaskCreatePinnedToCore(
        sensor_task, "sensor",
        8192,           /* Stack 8 KB — printf de 3000 líneas necesita espacio */
        NULL,
        5,              /* Prioridad alta: mantiene timing a 1 KHz */
        NULL,
        1               /* Core 1 */
    );

    xTaskCreatePinnedToCore(
        command_task, "command",
        4096,
        NULL,
        3,
        NULL,
        0               /* Core 0 */
    );
}
