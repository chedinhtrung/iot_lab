#pragma once
#include "freertos/event_groups.h"
#include "esp_wifi.h"
#include "esp_event.h"

extern char location[40];

void start_mqtt(void);
void sendPIReventToMQTT(void);
void sendBatteryStatusToMQTT(void);
void sendDoorEventToMQTT(void);
void sendTableToMQTT(void);