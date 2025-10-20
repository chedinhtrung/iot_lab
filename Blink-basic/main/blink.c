#include <stdio.h>

#include "driver/gpio.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define BLINK_GPIO 17

void app_main(void) {
  esp_log_level_set("*", ESP_LOG_ERROR);
  esp_log_level_set("led", ESP_LOG_INFO);

  ESP_LOGI("led", "Configure GPIO LED!");
  gpio_set_direction(BLINK_GPIO, GPIO_MODE_OUTPUT);

  while (true) {
    ESP_LOGI("led", "LED ON");
    gpio_set_level(BLINK_GPIO, 1);
    vTaskDelay(pdMS_TO_TICKS(500));
    ESP_LOGI("led", "LED OFF");
    gpio_set_level(BLINK_GPIO, 0);
    vTaskDelay(pdMS_TO_TICKS(500));
  }
}
