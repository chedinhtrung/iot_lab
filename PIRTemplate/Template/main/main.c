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

#include <driver/i2c.h>

#include "esp_mac.h"
#include "co2.h"
#include <ds3231.h>
#include <time.h>
#include <sys/time.h>

#define LED 17
#define RTC_WU_PIN 33

typedef enum {
  POWER,
  EXTI0,
  EXTI1,
  RTC,
} WakeupCause;

WakeupCause wuc = 0;
uint64_t mac_int = 0;
char location[40] = {0};
char device_topic[20];
char device_key[800];
int table_full = 0;

i2c_config_t i2c_conf = {
    .mode = I2C_MODE_MASTER,
    .sda_io_num = 15,        
    .sda_pullup_en = GPIO_PULLUP_ENABLE,
    .scl_io_num = 14,         
    .scl_pullup_en = GPIO_PULLUP_ENABLE,
    .master.clk_speed = 100000, 
};

i2c_dev_t i2c_rtc;

void app_main() {

  // misc. setups
  gpio_set_direction(LED, GPIO_MODE_OUTPUT);
  // setup i2c master
  //i2c_init();
  ESP_ERROR_CHECK(i2cdev_init());
  
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

  ESP_ERROR_CHECK(ds3231_init_desc(
        &i2c_rtc,
        0,          // use I2C0
        15,        // sda 
        14         // scl 
  ));
  
  // wakeup reason
  esp_sleep_wakeup_cause_t wc = esp_sleep_get_wakeup_cause();
  switch (wc) {
        case ESP_SLEEP_WAKEUP_TIMER:     ESP_LOGI("boot", "Woken by RTC timer"); wuc=RTC; break;
        case ESP_SLEEP_WAKEUP_EXT0:      ESP_LOGI("boot", "Woken by EXT0"); wuc=EXTI0; break;
        case ESP_SLEEP_WAKEUP_EXT1:      ESP_LOGI("boot", "Woken by EXT1"); wuc=EXTI1; break;
        default: ESP_LOGI("BOOT", "Power Up"); wuc=POWER; break;
  }

  printf("Woke up because %i \n", wc);
  gpio_set_level(LED, 0);
  vTaskDelay(pdMS_TO_TICKS(1000));
  // TODO: handle first plugged in (not a wakeup)
  if (wuc == POWER){
    printf("Power up");
    ESP_LOGI("progress", "Starting Wifi");
    start_wifi();
    ESP_LOGI("progress", "Starting Clock");
    start_clock();
    // TODO: setup the RTC DS3231
    time_t now = 0;
    time(&now);
    struct tm t;
    gmtime_r(&now, &t);
    init_rtc(t);
  }

  // get mac 
  uint8_t mac[6];
  esp_efuse_mac_get_default(mac);
  for (int i=0; i<6; i++){mac_int = (mac_int << 8) | mac[i];}
  printf("MAC (uint64) = %llu\n", (unsigned long long)mac_int);
  // configure based on mac
  printf("mac: %llu, macC: %llu, eq: %i \n", mac_int, DEV_C_MAC, mac_int == DEV_C_MAC);
  if (mac_int == DEV_A_MAC){       // golden esp
    strcpy(location, "desk");
    strcpy(device_topic, DEVICE_TOPIC_DESK);
    strcpy(device_key, DEVICE_KEY_DESK);

    // set rtc alarm once a day at 8AM to send rsoc
   
    struct tm time = {
      .tm_hour = 8,
      .tm_min  = 0,
      .tm_sec  = 0
    };
    ds3231_set_alarm(&i2c_rtc, DS3231_ALARM_1, &time, DS3231_ALARM1_MATCH_SECMINHOUR, 0, 0);
    ESP_ERROR_CHECK(gpio_set_direction(RTC_WU_PIN, GPIO_MODE_INPUT));
    ESP_ERROR_CHECK(rtc_gpio_pullup_en(RTC_WU_PIN));
    ESP_ERROR_CHECK(esp_sleep_enable_ext1_wakeup((1ULL << RTC_WU_PIN), 0));
    ds3231_clear_alarm_flags(&i2c_rtc, DS3231_ALARM_1);
    ds3231_enable_alarm_ints(&i2c_rtc, DS3231_ALARM_1);


  } else if (mac_int == DEV_C_MAC){
    strcpy(location, "fish");
    strcpy(device_topic, DEVICE_TOPIC_FISH);
    strcpy(device_key, DEVICE_KEY_FISH);
    init_co2_sensor();
    struct tm time = {
      .tm_hour = 8,
      .tm_min  = 31,
      .tm_sec  = 0
    };
    ds3231_set_alarm(&i2c_rtc, DS3231_ALARM_1, &time, DS3231_ALARM1_MATCH_SECMIN, 0, 0);
    ESP_ERROR_CHECK(gpio_set_direction(RTC_WU_PIN, GPIO_MODE_INPUT));
    ESP_ERROR_CHECK(rtc_gpio_pullup_en(RTC_WU_PIN));
    ESP_ERROR_CHECK(esp_sleep_enable_ext1_wakeup((1ULL << 33), 0));
    ds3231_clear_alarm_flags(&i2c_rtc, DS3231_ALARM_1);
    ds3231_enable_alarm_ints(&i2c_rtc, DS3231_ALARM_1);

  } else if (mac_int == DEV_B_MAC){
    strcpy(location, "door");
    strcpy(device_topic, DEVICE_TOPIC_DOOR);
    strcpy(device_key, DEVICE_KEY_DOOR);
  }
  printf("roomID: %s \n", location);

  // handle periodic wakeup for battery status (only gold esp)
  if (mac_int == DEV_A_MAC && wuc == EXTI1){
    ds3231_clear_alarm_flags(&i2c_rtc, DS3231_ALARM_1);
    ds3231_enable_alarm_ints(&i2c_rtc, DS3231_ALARM_1);
    getRSOC();
    start_wifi_mqtt();
    sendBatteryStatusToMQTT();
  }

  // TODO: handle periodic wakeup for CO2, Humidity and Temp (only device C)
  else if (mac_int == DEV_C_MAC && wuc == EXTI1){
    ds3231_clear_alarm_flags(&i2c_rtc, DS3231_ALARM_1);
    ds3231_enable_alarm_ints(&i2c_rtc, DS3231_ALARM_1);
    printf("Hourly record of CO2");
    CO2_Data data = read_co2_sensor();
    if (data.valid){
      printf("CO2: %f, temp: %f, hum:%f", data.co2, data.temp, data.hum);
      record_air_data(data);
    } else {
      printf("Data invalid");
    }
    
  }

  // handle event wakeup

  // TODO: check ble tag (device independent)

  // TODO: record event into event table

  else if (mac_int == DEV_A_MAC && wuc == EXTI0){      // PIR event for device A
    record_pir_data();
  }

  else if (mac_int == DEV_B_MAC && wuc == EXTI0){      // Door event for device B
    record_door_data();
  }

  else if (mac_int == DEV_C_MAC && wuc == EXTI0){      // PIR event for device C
    record_pir_data();
    CO2_Data data = read_co2_sensor();
    if (data.valid){
      printf("CO2: %f, temp: %f, hum:%f", data.co2, data.temp, data.hum);
      record_air_data(data);
    } else {
      printf("Data invalid");
    }
  }

  // setup wakeup and go back to sleep
  set_wakeup_then_sleep();
  
}

void init_rtc(struct tm time){
  ESP_ERROR_CHECK(ds3231_set_time(&i2c_rtc, &time));
  char strftime_buf[64];
  strftime(strftime_buf, sizeof(strftime_buf), "%c", &time);
  printf("Set DS3231 time to be: %s", strftime_buf);
}

void set_wakeup_then_sleep(void)
{
  ESP_ERROR_CHECK(gpio_set_direction(PIR_PIN, GPIO_MODE_INPUT));
  ESP_ERROR_CHECK(rtc_gpio_pulldown_en(PIR_PIN));

  ESP_ERROR_CHECK(gpio_set_direction(RTC_WU_PIN, GPIO_MODE_INPUT));
  ESP_ERROR_CHECK(rtc_gpio_pullup_en(RTC_WU_PIN));
  ESP_ERROR_CHECK(esp_sleep_enable_ext1_wakeup((1ULL << 33), 0));

  ESP_LOGI("progress", "Installing wakeup");
  while (gpio_get_level(PIR_PIN)==1){
    vTaskDelay(pdMS_TO_TICKS(1000));    // debounce for 10 minutes
  }
  ESP_ERROR_CHECK(esp_sleep_enable_ext0_wakeup(PIR_PIN, 1));
  ESP_LOGI("progress", "Going to sleep");
  gpio_set_level(LED, 1);
  esp_deep_sleep_start();
}

void i2c_init(void){
  i2c_driver_install(0, i2c_conf.mode, 0, 0, 0);
}

void start_wifi_mqtt(){
  ESP_LOGI("progress", "Starting Wifi");
  start_wifi();

  ESP_LOGI("progress", "Starting Clock");
  start_clock();

  ESP_LOGI("progress", "Starting MQTT");
  start_mqtt();
}

void record_pir_data(void){
  PIRData d = {0}; 
  time_t now = 0;
  // get the timestamp
  struct tm rtc_time;
  ds3231_get_time(&i2c_rtc, &rtc_time);
  now = mktime(&rtc_time);
  d.timestamp = now * 1000;

  strcpy(&(d.roomID), location);
  table_full = put_data(PIRDATA, sizeof(PIRData), &d);
  printf("Recorded PIR into table at index %i, timestamp %llu \n", table_index, d.timestamp);

  time_t internal_time = 0;
  time(&internal_time);
  printf("Time according to time(): %llu \n", internal_time);

  if (table_full){
    printf("Table is full\n");
    start_wifi_mqtt();
    int send_success = sendTableToMQTT();
    if (send_success != -1){
        clear_table();
        printf("Sent table\n");
    }
  }
}

void record_air_data(CO2_Data data){
  AirData d = {0}; 
  time_t now = 0;
  // get the timestamp
  struct tm rtc_time;
  ds3231_get_time(&i2c_rtc, &rtc_time);
  now = mktime(&rtc_time);
  d.timestamp = now * 1000;

  strcpy(&(d.roomID), location);
  d.co2 = data.co2;
  d.temp = data.temp;
  d.hum = data.hum;
  table_full = put_data(AIRDATA, sizeof(AirData), &d);
  printf("Recorded Air into table at index %i, timestamp %llu \n", table_index, d.timestamp);

  if (table_full){
    printf("Table is full\n");
    start_wifi_mqtt();
    int send_success = sendTableToMQTT();
    if (send_success != -1){
        clear_table();
        printf("Sent table\n");
    }
  }
}

void record_door_data(void){
  DoorData d = {0}; 
  time_t now = 0;
  // get the timestamp
  struct tm rtc_time;
  ds3231_get_time(&i2c_rtc, &rtc_time);
  now = mktime(&rtc_time);

  d.timestamp = now * 1000;
  strcpy(&(d.roomID), location);
  table_full = put_data(DOORDATA, sizeof(DoorData), &d);
  printf("Recorded Door into table at index %i \n", table_index);

  if (table_full){
    printf("Table is full\n");
    start_wifi_mqtt();
    int send_success = sendTableToMQTT();
    if (send_success != -1){
        clear_table();
        printf("Sent table\n");
    }
  }
}