#pragma once

extern float voltage, rsoc, door_state;
void getRSOC();

#include <time.h>

typedef struct {
    time_t timestamp;
    float voltage;
    float soc;
    char roomID[10];
} RSOC;

typedef struct {
    time_t timestamp;
    float co2; 
    float hum;
    float temp;
    char roomID[10];
} AirData;

typedef struct {
    time_t timestamp; 
    char roomID[10];
} PIRData;

typedef struct {
    time_t timestamp;
    char roomID[10];
} DoorData;