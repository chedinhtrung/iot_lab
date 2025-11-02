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
#include "event_table.h"


#include "esp_mac.h"
#define LED 17

typedef enum {
  POWER,
  EXTI0,
  EXTI1,
  RTC,
} WakeupCause;

WakeupCause wuc;
uint64_t mac_int = 0;
char location[40] = {0};
char device_topic[20];
char device_key[800];

void start_wifi_mqtt(){
  ESP_LOGI("progress", "Starting Wifi");
  start_wifi();

  ESP_LOGI("progress", "Starting Clock");
  start_clock();

  ESP_LOGI("progress", "Starting MQTT");
  start_mqtt();
}

void app_main() {
  //gpio_set_direction(LED, GPIO_MODE_OUTPUT);
  // log level stuff 
  ESP_LOGI("progress", "[APP] Free memory: %d bytes", esp_get_free_heap_size());
  ESP_LOGI("progress", "[APP] IDF version: %s", esp_get_idf_version());

  esp_log_level_set("*", ESP_LOG_NONE);
  esp_log_level_set("mqtt", ESP_LOG_INFO);
  esp_log_level_set("progress", ESP_LOG_INFO);
  esp_log_level_set("gauge", ESP_LOG_INFO);
  // non volatile storage init for wifi & bt
  {
  esp_err_t ret = nvs_flash_init();
  if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
    ESP_ERROR_CHECK(nvs_flash_erase());
    ret = nvs_flash_init();
  }
  ESP_ERROR_CHECK(ret);
  }
  // get mac 
  uint8_t mac[6];
  esp_efuse_mac_get_default(mac);
  for (int i=0; i<6; i++){mac_int = (mac_int << 8) | mac[i];}
  printf("MAC (uint64) = %llu\n", (unsigned long long)mac_int);
  // configure based on mac
  printf("mac: %llu, macC: %llu, eq: %i \n", mac_int, DEV_C_MAC, mac_int == DEV_C_MAC);
  if (mac_int == DEV_A_MAC){      // set locations
    strcpy(location, "desk");
    strcpy(device_topic, DEVICE_TOPIC_DESK);
    strcpy(device_key, DEVICE_KEY_DESK);
  } else if (mac_int == DEV_C_MAC){
    strcpy(location, "fish");
    strcpy(device_topic, DEVICE_TOPIC_FISH);
    strcpy(device_key, DEVICE_KEY_FISH);
  } else if (mac_int == DEV_B_MAC){
    strcpy(location, "door");
    strcpy(device_topic, DEVICE_TOPIC_DOOR);
    strcpy(device_key, DEVICE_KEY_DOOR);
  }

  printf("roomID: %s", location);

  // TODO: wakeup reason
  esp_sleep_wakeup_cause_t wc = esp_sleep_get_wakeup_cause();
  switch (wc) {
        case ESP_SLEEP_WAKEUP_TIMER:     ESP_LOGI("boot", "Woken by RTC timer"); wuc=RTC; break;
        case ESP_SLEEP_WAKEUP_EXT0:      ESP_LOGI("boot", "Woken by EXT0"); wuc=EXTI0; break;
        case ESP_SLEEP_WAKEUP_EXT1:      ESP_LOGI("boot", "Woken by EXT1"); wuc=EXTI1; break;
        default: ESP_LOGI("BOOT", "Power Up"); wuc=POWER; break;
  }

  printf("Woke up because %i \n", wc);
  // TODO: handle first plugged in (not a wakeup)
  if (wuc == POWER){
    ESP_LOGI("progress", "Starting Wifi");
    start_wifi();
    ESP_LOGI("progress", "Starting Clock");
    start_clock();
  }

  // TODO: setup the RTC DS3231

  // handle periodic wakeup for battery status (only gold esp)
  if (mac_int == DEV_A_MAC && wuc == RTC){
    getRSOC();
    start_wifi_mqtt();
    sendBatteryStatusToMQTT();
  }

  // TODO: handle periodic wakeup for CO2, Humidity and Temp (only device B)
  if (mac_int == DEV_C_MAC && wuc == RTC){
    // TODO: record event to table
    // TODO: publish if table full
  }

  // handle event wakeup

  // TODO: check ble tag (device independent)

  // TODO: record event into event table
  int table_full = 0;
  if (mac_int == DEV_A_MAC){      // PIR event for device A
    
  }

  else if (mac_int == DEV_B_MAC){      // Door event for device B

  }

  else if (mac_int == DEV_C_MAC && wuc == EXTI0){      // PIR event for device C
  
    PIRData d = {0}; 
    time_t now = 0;
    time(&now);
    d.timestamp = now * 1000;
    strcpy(&(d.roomID), location);
    table_full = put_data(PIRDATA, sizeof(PIRData), &d);
    printf("Recorded into table at index %i \n", table_index);
    if (table_index > 0){
      PIRData d1;
      memcpy(&d1, &(event_table[table_index - 1].payload), event_table[table_index - 1].len);
      printf("Content: timestamp %llu \n", d1.timestamp);
    }
   
  }

  // TODO: if table is full, send the events in the table (device independent)
  if (table_full){
    printf("Table is full\n");
    start_wifi_mqtt();
    sendTableToMQTT();
    printf("Sent table\n");
  }

  // setup wakeup and go back to sleep

  ESP_ERROR_CHECK(gpio_set_direction(PIR_PIN, GPIO_MODE_INPUT));
  ESP_ERROR_CHECK(rtc_gpio_pulldown_en(PIR_PIN));

  ESP_LOGI("progress", "Installing wakeup");
  while (gpio_get_level(PIR_PIN)==1){
    vTaskDelay(pdMS_TO_TICKS(1000));    // debounce for 10 minutes
  }
  ESP_ERROR_CHECK(esp_sleep_enable_ext0_wakeup(PIR_PIN, 1));
  ESP_LOGI("progress", "Going to sleep");
  esp_deep_sleep_start();
}

