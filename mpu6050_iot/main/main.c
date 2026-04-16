#include <stdio.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/semphr.h>
#include <esp_err.h>
#include <esp_log.h>
#include <mpu6050.h>
#include "esp_http_server.h"
#include "wifi_manager.h"

#define CONFIG_EXAMPLE_SCL_GPIO 9
#define CONFIG_EXAMPLE_SDA_GPIO 8
#define ADDR                    MPU6050_I2C_ADDRESS_LOW

static const char *TAG = "mpu6050_iot";

static mpu6050_dev_t s_mpu_dev = { 0 };

/* ── Últimos datos del sensor (compartidos con el servidor HTTP) ── */
static SemaphoreHandle_t     s_sensor_mutex;
static float                 s_temp     = 0.0f;
static mpu6050_acceleration_t s_accel   = { 0 };
static mpu6050_rotation_t     s_rotation = { 0 };

/* ── Página HTML principal ─────────────────────────────────────── */
static const char INDEX_HTML[] =
    "<!DOCTYPE html><html lang='es'><head>"
    "<meta charset='UTF-8'>"
    "<meta name='viewport' content='width=device-width,initial-scale=1'>"
    "<title>ESP32-S3 &middot; MPU6050</title>"
    "<style>"
    "body{margin:0;background:#1a1a2e;color:#eee;font-family:sans-serif;"
    "display:flex;flex-direction:column;align-items:center;"
    "justify-content:center;min-height:100vh;}"
    "h1{color:#e94560;margin-bottom:24px;}"
    ".card{background:#16213e;border-radius:12px;padding:24px 40px;margin:8px;"
    "min-width:280px;box-shadow:0 4px 16px #0006;}"
    ".card h2{margin:0 0 12px;font-size:.9rem;color:#0f9;text-transform:uppercase;"
    "letter-spacing:1px;}"
    ".row{display:flex;justify-content:space-between;margin:6px 0;}"
    ".label{color:#aaa;}.value{font-weight:bold;color:#e94560;}"
    "#status{margin-top:16px;font-size:.8rem;color:#555;}"
    "</style></head><body>"
    "<h1>ESP32-S3 &middot; MPU6050</h1>"
    "<div class='card'><h2>Aceleración (g)</h2>"
    "<div class='row'><span class='label'>X</span><span class='value' id='ax'>—</span></div>"
    "<div class='row'><span class='label'>Y</span><span class='value' id='ay'>—</span></div>"
    "<div class='row'><span class='label'>Z</span><span class='value' id='az'>—</span></div>"
    "</div>"
    "<div class='card'><h2>Giroscopio (°/s)</h2>"
    "<div class='row'><span class='label'>X</span><span class='value' id='gx'>—</span></div>"
    "<div class='row'><span class='label'>Y</span><span class='value' id='gy'>—</span></div>"
    "<div class='row'><span class='label'>Z</span><span class='value' id='gz'>—</span></div>"
    "</div>"
    "<div class='card'><h2>Temperatura</h2>"
    "<div class='row'><span class='label'>°C</span><span class='value' id='temp'>—</span></div>"
    "</div>"
    "<p id='status'>Conectando...</p>"
    "<script>"
    "function fmt(v){return v.toFixed(4);}"
    "function update(){"
    "fetch('/data').then(r=>r.json()).then(d=>{"
    "document.getElementById('ax').textContent=fmt(d.ax);"
    "document.getElementById('ay').textContent=fmt(d.ay);"
    "document.getElementById('az').textContent=fmt(d.az);"
    "document.getElementById('gx').textContent=fmt(d.gx);"
    "document.getElementById('gy').textContent=fmt(d.gy);"
    "document.getElementById('gz').textContent=fmt(d.gz);"
    "document.getElementById('temp').textContent=d.temp.toFixed(1);"
    "document.getElementById('status').textContent="
    "'Actualizado: '+new Date().toLocaleTimeString();"
    "}).catch(()=>{"
    "document.getElementById('status').textContent='Error al obtener datos';});}"
    "update();setInterval(update,1000);"
    "</script></body></html>";

/* ── GET / ── */
static esp_err_t index_handler(httpd_req_t *req)
{
    httpd_resp_set_type(req, "text/html");
    return httpd_resp_send(req, INDEX_HTML, sizeof(INDEX_HTML) - 1);
}

/* ── GET /data → JSON con los últimos valores del sensor ── */
static esp_err_t data_handler(httpd_req_t *req)
{
    char buf[128];

    if (xSemaphoreTake(s_sensor_mutex, pdMS_TO_TICKS(100)) == pdTRUE) {
        snprintf(buf, sizeof(buf),
                 "{\"ax\":%.4f,\"ay\":%.4f,\"az\":%.4f,"
                 "\"gx\":%.4f,\"gy\":%.4f,\"gz\":%.4f,"
                 "\"temp\":%.1f}",
                 s_accel.x, s_accel.y, s_accel.z,
                 s_rotation.x, s_rotation.y, s_rotation.z,
                 s_temp);
        xSemaphoreGive(s_sensor_mutex);
    } else {
        snprintf(buf, sizeof(buf), "{\"error\":\"busy\"}");
    }

    httpd_resp_set_type(req, "application/json");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    return httpd_resp_send(req, buf, strlen(buf));
}

/* ── Arranque del servidor HTTP ── */
static void start_webserver(void)
{
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.max_uri_handlers = 4;

    httpd_handle_t server = NULL;
    if (httpd_start(&server, &config) != ESP_OK) {
        ESP_LOGE(TAG, "Error al iniciar el servidor HTTP");
        return;
    }

    httpd_uri_t index_uri = { .uri = "/",      .method = HTTP_GET, .handler = index_handler };
    httpd_uri_t data_uri  = { .uri = "/data",  .method = HTTP_GET, .handler = data_handler  };

    httpd_register_uri_handler(server, &index_uri);
    httpd_register_uri_handler(server, &data_uri);

    ESP_LOGI(TAG, "Servidor HTTP iniciado → http://esp32s3-sensor.local/");
}

/* ── Tarea continua de lectura del MPU6050 ──────────────────── */

static void mpu6050_task(void *pvParameters)
{
    ESP_ERROR_CHECK(mpu6050_init_desc(&s_mpu_dev, ADDR, 0,
                                      CONFIG_EXAMPLE_SDA_GPIO,
                                      CONFIG_EXAMPLE_SCL_GPIO));

    while (i2c_dev_probe(&s_mpu_dev.i2c_dev, I2C_DEV_WRITE) != ESP_OK) {
        ESP_LOGE(TAG, "MPU60x0 no encontrado, reintentando...");
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
    ESP_LOGI(TAG, "MPU60x0 encontrado");
    ESP_ERROR_CHECK(mpu6050_init(&s_mpu_dev));

    while (1) {
        float temp;
        mpu6050_acceleration_t accel    = { 0 };
        mpu6050_rotation_t     rotation = { 0 };

        ESP_ERROR_CHECK(mpu6050_get_temperature(&s_mpu_dev, &temp));
        ESP_ERROR_CHECK(mpu6050_get_motion(&s_mpu_dev, &accel, &rotation));

        /* Guardar para el servidor HTTP */
        if (xSemaphoreTake(s_sensor_mutex, pdMS_TO_TICKS(100)) == pdTRUE) {
            s_temp     = temp;
            s_accel    = accel;
            s_rotation = rotation;
            xSemaphoreGive(s_sensor_mutex);
        }

        ESP_LOGI(TAG, "Accel: x=%.4f y=%.4f z=%.4f | Gyro: x=%.4f y=%.4f z=%.4f | Temp: %.1f°C",
                 accel.x, accel.y, accel.z,
                 rotation.x, rotation.y, rotation.z,
                 temp);

        vTaskDelay(pdMS_TO_TICKS(500));
    }
}

/* ── app_main ───────────────────────────────────────────────── */

void app_main(void)
{
    /* 1. WiFi con BLE provisioning */
    ESP_ERROR_CHECK(wifi_manager_init());
    if (!wifi_manager_wait_connected(WIFI_CONNECT_TIMEOUT_MS)) {
        ESP_LOGE(TAG, "No se pudo conectar al WiFi.");
    }

    /* 2. Mutex para proteger los datos del sensor */
    s_sensor_mutex = xSemaphoreCreateMutex();
    assert(s_sensor_mutex != NULL);

    /* 3. I2C + tarea de lectura MPU6050 */
    ESP_ERROR_CHECK(i2cdev_init());
    xTaskCreate(mpu6050_task, "mpu6050", configMINIMAL_STACK_SIZE * 6, NULL, 5, NULL);

    /* 4. Servidor HTTP */
    start_webserver();
}