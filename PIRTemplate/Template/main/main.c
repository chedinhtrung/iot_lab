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
#include "ble.h"

#include "esp_pm.h"

typedef enum {
  POWER,
  EXTI0,
  EXTI1,
  RTC,
} WakeupCause;

WakeupCause wuc = 0;
RTC_DATA_ATTR uint64_t mac_int = 0;
RTC_DATA_ATTR char location[10] = {0};
RTC_DATA_ATTR char device_topic[20];
RTC_DATA_ATTR char device_key[800];
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

extern bool scan_done;
extern bool tag_found;
extern int bt_rssi;

void app_main() {

    // enable light sleep
  esp_pm_config_esp32_t pm_config = {
    .max_freq_mhz = 240,
    .min_freq_mhz = 80,
    .light_sleep_enable = true,
  };
  //esp_pm_configure(&pm_config);

  // misc. setups
  gpio_set_direction(LED, GPIO_MODE_OUTPUT);
  // setup i2c master
  ESP_ERROR_CHECK(i2cdev_init());
  
  // log level stuff 
  set_log_levels();

  // non volatile storage init for wifi & bt (always needed for bt)
  init_nvs();

  // init the rtc module
  ESP_ERROR_CHECK(ds3231_init_desc(
        &i2c_rtc,
        0,          // use I2C0
        15,        // sda 
        14         // scl 
  ));
  
  // wakeup reason
  esp_sleep_wakeup_cause_t wc = esp_sleep_get_wakeup_cause();
  switch (wc) {
        case ESP_SLEEP_WAKEUP_TIMER:     wuc=RTC; break;
        case ESP_SLEEP_WAKEUP_EXT0:      wuc=EXTI0; break;
        case ESP_SLEEP_WAKEUP_EXT1:      wuc=EXTI1; break;
        default: wuc = POWER; break;
  }

  printf("Woke up because %i \n", wuc);

  // Blink the led to signal. shut down if want to have low power
  { 
  gpio_set_level(LED, 0);
  vTaskDelay(pdMS_TO_TICKS(1000));
  }

  // handle first plugged in (not a wakeup)
  if (wuc == POWER){
    // start wifi and clock to get current time
    printf("Power up");
    ESP_LOGI("progress", "Starting Wifi");
    start_wifi();
    ESP_LOGI("progress", "Starting Clock");
    start_clock();

    // setup the RTC DS3231, sync the time 
    time_t now = 0;
    time(&now);
    struct tm t;
    gmtime_r(&now, &t);
    init_rtc(t);

    // get mac and copy device specific setups

    get_mac();
    // configure based on mac. only do once when powerup 
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

    // configure OTA
    set_wakeup_then_sleep();
  }
  

  // handle periodic wakeup for battery status (only gold esp)
  if (mac_int == DEV_A_MAC && wuc == EXTI1){
    ds3231_clear_alarm_flags(&i2c_rtc, DS3231_ALARM_1);
    ds3231_enable_alarm_ints(&i2c_rtc, DS3231_ALARM_1);
    getRSOC();
    start_wifi_mqtt();
    sendBatteryStatusToMQTT();
    set_wakeup_then_sleep();
  }

  // TODO: handle periodic wakeup for CO2, Humidity and Temp (only device C)
  if (mac_int == DEV_C_MAC && wuc == EXTI1){
    init_co2_sensor();
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
    set_wakeup_then_sleep();
  }

  // handle event wakeup

  // check ble tag (only for device B)
  if (mac_int == DEV_B_MAC){
    scan_ble();
    if (!(tag_found && bt_rssi >= RSSI_TH)){
      set_wakeup_then_sleep();
    }
  }
 

  // TODO: Check OTA update

  // record event into event table

  if (mac_int == DEV_A_MAC && wuc == EXTI0){      // PIR event for device A
    record_pir_data();
    set_wakeup_then_sleep();
  }

  if (mac_int == DEV_B_MAC && wuc == EXTI0){      // Door event for device B
    record_door_data();
    set_wakeup_then_sleep();
  }

  if (mac_int == DEV_C_MAC && wuc == EXTI0){      // PIR event for device C
    init_co2_sensor();
    record_pir_data();
    CO2_Data data = read_co2_sensor();
    if (data.valid){
      printf("CO2: %f, temp: %f, hum:%f", data.co2, data.temp, data.hum);
      record_air_data(data);
    } else {
      printf("Data invalid");
    }
    set_wakeup_then_sleep();
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
  printf("PIRdata to table at %i \n", table_index);

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
  printf("Airdata to table at %i \n", table_index);

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
  printf("Doordata to table at %i \n", table_index);

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

void set_log_levels(void){
  //ESP_LOGI("progress", "[APP] Free memory: %d bytes", esp_get_free_heap_size());
  //ESP_LOGI("progress", "[APP] IDF version: %s", esp_get_idf_version());

  esp_log_level_set("*", ESP_LOG_NONE);
  esp_log_level_set("mqtt", ESP_LOG_INFO);
  esp_log_level_set("progress", ESP_LOG_INFO);
  esp_log_level_set("gauge", ESP_LOG_INFO);
}

void init_nvs(void)
  {
  esp_err_t ret = nvs_flash_init();
  if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
    ESP_ERROR_CHECK(nvs_flash_erase());
    ret = nvs_flash_init();
  }
  ESP_ERROR_CHECK(ret);
}

void get_mac(void){
  uint8_t mac[6];
  esp_efuse_mac_get_default(mac);
  for (int i=0; i<6; i++){mac_int = (mac_int << 8) | mac[i];}
  printf("MAC = %llu\n", (unsigned long long)mac_int);
}
