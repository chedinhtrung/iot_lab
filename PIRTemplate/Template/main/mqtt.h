#pragma once
#include "freertos/event_groups.h"
#include "esp_wifi.h"
#include "esp_event.h"

extern char location[10];

void start_mqtt(void);
void sendBatteryStatusToMQTT(void);

int sendTableToMQTT(void);