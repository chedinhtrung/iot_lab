#pragma once
#include <stdio.h>
#include <string.h>
#include <limits.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "esp_err.h"
#include "esp_bt.h"

#include "esp_gap_ble_api.h"
#include "esp_log.h"

#define BLE_TAG_MAC 238854470186547
#define WATCH_TAG_MAC 80692477660580

void init_ble(void);
void gap_event_handler(esp_gap_ble_cb_event_t event, esp_ble_gap_cb_param_t *param);

void get_device_name(esp_ble_gap_cb_param_t *param, char *name, int name_len);

void scan_ble(void);
