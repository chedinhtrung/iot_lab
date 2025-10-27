#include "main.h"

#include <stdio.h>
#include <string.h>

#include "driver/gpio.h"
#include "esp_log.h"
#include "esp_system.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "gauge.h"
#include "mqtt.h"
#include "nvs_flash.h"
#include "sntp.h"
#include "wifi.h"
#include "esp_sleep.h"


#include "esp_mac.h"


void app_main() {
  uint8_t mac[6];
  esp_read_mac(mac, ESP_MAC_WIFI_STA);
  ESP_LOGI("MAC", "");
  ESP_LOGI("progress", "[APP] Free memory: %d bytes", esp_get_free_heap_size());
  ESP_LOGI("progress", "[APP] IDF version: %s", esp_get_idf_version());

  esp_log_level_set("*", ESP_LOG_ERROR);
  esp_log_level_set("mqtt", ESP_LOG_INFO);
  esp_log_level_set("progress", ESP_LOG_INFO);
  esp_log_level_set("gauge", ESP_LOG_INFO);

  getRSOC();
  esp_err_t ret = nvs_flash_init();
  if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
    ESP_ERROR_CHECK(nvs_flash_erase());
    ret = nvs_flash_init();
  }
  ESP_ERROR_CHECK(ret);

  ESP_LOGI("progress", "Starting Wifi");
  start_wifi();

  ESP_LOGI("progress", "Starting Clock");
  start_clock();

  ESP_LOGI("progress", "Starting MQTT");
  start_mqtt();

  ESP_LOGI("progress", "Sending battery status to MQTT");
  sendBatteryStatusToMQTT();

  ESP_LOGI("progress", "Sending PIR event to MQTT");
  sendPIReventToMQTT();

  ESP_ERROR_CHECK(gpio_set_direction(PIR_PIN, GPIO_MODE_INPUT));
  ESP_ERROR_CHECK(rtc_gpio_pulldown_en(PIR_PIN));

  ESP_LOGI("progress", "Installing wakeup");
  while (gpio_get_level(PIR_PIN)==1){
    vTaskDelay(pdMS_TO_TICKS(1000));
  }
  ESP_ERROR_CHECK(esp_sleep_enable_ext0_wakeup(PIR_PIN, 1));
  ESP_LOGI("progress", "Going to sleep");
  esp_deep_sleep_start();
}