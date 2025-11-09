#include <stdio.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include "esp_wifi.h"
#include "esp_system.h"
#include "nvs_flash.h"
#include "esp_event.h"
#include "esp_netif.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "freertos/queue.h"
#include "freertos/event_groups.h"

#include "lwip/sockets.h"
#include "lwip/dns.h"
#include "lwip/netdb.h"

#include "esp_log.h"
#include "mqtt_client.h"
#include "main.h"
#include "gauge.h"
#include "mqtt.h"

#include "event_table.h"

esp_mqtt_client_handle_t mqtt_client = NULL;
EventGroupHandle_t mqtt_event_group;
static int qos_test = 1;

const static int CONNECTED_BIT = BIT0;
extern char device_topic[20];
extern char device_key[800];

void mqtt_event_handler(void *handler_args, esp_event_base_t base, int32_t event_id, void *event_data) {
  esp_mqtt_event_t *data = (esp_mqtt_event_t *)event_data;
  switch (event_id) {
    case MQTT_EVENT_CONNECTED:
      ESP_LOGI("mqtt", "MQTT_EVENT_CONNECTED\n");
      xEventGroupSetBits(mqtt_event_group, CONNECTED_BIT);
      break;

    case MQTT_EVENT_DISCONNECTED:
      ESP_LOGI("mqtt", "MQTT_EVENT_DISCONNECTED\n");
      break;

    case MQTT_EVENT_SUBSCRIBED:
      ESP_LOGI("mqtt", "MQTT_EVENT_SUBSCRIBED, msg_id=%d\n", data->msg_id);
      break;

    case MQTT_EVENT_UNSUBSCRIBED:
      ESP_LOGI("mqtt", "MQTT_EVENT_UNSUBSCRIBED, msg_id=%d\n", data->msg_id);
      break;

    case MQTT_EVENT_PUBLISHED:
      ESP_LOGI("mqtt", "MQTT_EVENT_PUBLISHED, msg_id=%d\n", data->msg_id);
      break;

    case MQTT_EVENT_DATA:
      ESP_LOGI("mqtt", "MQTT_EVENT_DATA\n");
      ESP_LOGI("mqtt", "TOPIC=%.*s\r\n", data->topic_len, data->topic);
      ESP_LOGI("mqtt", "DATA=%.*s\r\n", data->data_len, data->data);
      ESP_LOGI("mqtt", "ID=%d, total_len=%d, data_len=%d, current_data_offset=%d\n", data->msg_id, data->total_data_len, data->data_len, data->current_data_offset);
      // count++;
      break;

    case MQTT_EVENT_ERROR:
      ESP_LOGI("mqtt", "MQTT_EVENT_ERROR\n");
      break;

    case MQTT_EVENT_BEFORE_CONNECT:
      ESP_LOGI("mqtt", "MQTT_EVENT_BEFORE_CONNECT\n");
      break;

    default:
      ESP_LOGI("mqtt", "Other event id:%d\n", data->event_id);
      break;
  }
}

void start_mqtt(void) {
  esp_mqtt_client_config_t mqtt_cfg = {};
  mqtt_cfg.broker.address.hostname = MQTT_BROKER;
  mqtt_cfg.broker.address.port = 1883;
  mqtt_cfg.broker.address.transport = MQTT_TRANSPORT_OVER_TCP;
  mqtt_cfg.session.protocol_ver = MQTT_PROTOCOL_V_3_1_1;
  mqtt_cfg.credentials.username = "JWT";
  mqtt_cfg.network.timeout_ms = 30000;
  mqtt_cfg.credentials.authentication.password = device_key;

  ESP_LOGI("mqtt", "[APP] Free memory: %d bytes", esp_get_free_heap_size());
  mqtt_client = esp_mqtt_client_init(&mqtt_cfg);
  esp_mqtt_client_register_event(mqtt_client, MQTT_EVENT_ANY, mqtt_event_handler, NULL);

  mqtt_event_group = xEventGroupCreate();
  esp_mqtt_client_start(mqtt_client);
  ESP_LOGI("mqtt", "Note free memory: %d bytes", esp_get_free_heap_size());
  ESP_LOGI("mqtt", "Waiting for connection to MQTT\n");
  xEventGroupWaitBits(mqtt_event_group, CONNECTED_BIT, false, true, portMAX_DELAY);
  ESP_LOGI("mqtt", "Connected to MQTT\n");
}

void sendPIReventToMQTT(void) {
  time_t now = 0;

  char msg[150];
  time(&now);

  int size = snprintf(msg, sizeof(msg), "{\"sensors\":[{\"name\":\"PIR\",\"values\":[{\"timestamp\":%llu, \"roomID\":\"%s\"}]}]}", now * 1000, location);
  ESP_LOGI("mqtt", "Sent <%s> to topic %s", msg, device_topic);
  auto err = esp_mqtt_client_publish(mqtt_client, device_topic, msg, size, 1, 0);
  if (err == -1) {
    printf("Error while publishing to mqtt\n");
    ESP_LOGI("functions", "SendToMqttFunction terminated");
    return ESP_FAIL;
  }
}

void sendBatteryStatusToMQTT(void) {
  time_t now = 0;

  char msg[150];
  time(&now);

  int size = snprintf(msg, sizeof(msg), "{\"sensors\":[{\"name\":\"battery\",\"values\":[{\"timestamp\":%llu, \"voltage\":%.1f, \"soc\":%.1f}]}]}", now * 1000, voltage, rsoc);
  ESP_LOGI("mqtt", "Sent <%s> to topic %s", msg, device_topic);
  auto err = esp_mqtt_client_publish(mqtt_client, device_topic, msg, size, 1, 0);
  if (err == -1) {
    printf("Error while publishing to mqtt\n");
    ESP_LOGI("functions", "SendToMqttFunction terminated");
    return ESP_FAIL;
  }
}

void sendDoorEventToMQTT(void) {
  time_t now = 0;

  char msg[150];
  time(&now);

  int size = snprintf(msg, sizeof(msg), "{\"sensors\":[{\"name\":\"door\",\"values\":[{\"timestamp\":%llu, \"roomID\":%s}]}]}", now * 1000, location);
  ESP_LOGI("mqtt", "Sent <%s> to topic %s", msg, device_topic);
  auto err = esp_mqtt_client_publish(mqtt_client, device_topic, msg, size, 1, 0);
  if (err == -1) {
    printf("Error while publishing to mqtt\n");
    ESP_LOGI("functions", "SendToMqttFunction terminated");
    return ESP_FAIL;
  }
}

int sendTableToMQTT(void){
  char msg[200*TABLE_SIZE];     // Buffer for the giant message
  char entry_str[200];
  int size;
  // copy the initial part 
  strcpy(msg, "{\"sensors\":[");
  
  for (int i=0; i<TABLE_SIZE; i++){
    EventTableData entry = event_table[i];
    switch (entry.type){
      case PIRDATA:
        PIRData pir_data = {0};
        memcpy(&pir_data, &(entry.payload), entry.len);
        size = snprintf(entry_str, sizeof(entry_str), "{\"name\":\"PIR\",\"values\":[{\"timestamp\":%llu, \"roomID\":\"%s\"}]}", pir_data.timestamp, pir_data.roomID);
        strcpy(msg+strlen(msg), entry_str);
        break;
      
      case DOORDATA:
        DoorData door_data = {0};
        memcpy(&door_data, &(entry.payload), entry.len);
        size = snprintf(entry_str, sizeof(entry_str), "{\"name\":\"door\",\"values\":[{\"timestamp\":%llu, \"roomID\":\"%s\"}]}", pir_data.timestamp, pir_data.roomID);
        strcpy(msg+strlen(msg), entry_str);
        break;
        
      case AIRDATA:
        AirData air_data = {0};
        memcpy(&air_data, &(entry.payload), entry.len);
        size = snprintf(entry_str, sizeof(entry_str), "{\"name\":\"air\",\"values\":[{\"timestamp\":%llu, \"co2\":%.1f, \"temp\":%.1f, \"hum\":%.1f, \"roomID\":\"%s\"}]}", pir_data.timestamp, pir_data.roomID);
        strcpy(msg+strlen(msg), entry_str);
        break;
      
    }
    if (i != TABLE_SIZE-1){
      strcpy(msg+strlen(msg), ",");
    }
  }
  // close the brackets 
  strcpy(msg+strlen(msg), "]}");
  auto err = esp_mqtt_client_publish(mqtt_client, device_topic, msg, strlen(msg), 1, 0);
  if (err == -1) {
    printf("Error while publishing to mqtt\n");
    ESP_LOGE("functions", "SendToMqttFunction terminated");
    return ESP_FAIL;
  }
  ESP_LOGI("mqtt", "Sent <%s> to topic %s", msg, device_topic);
}
