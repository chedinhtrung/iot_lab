#pragma once 
#include <stdint.h>
#include <i2cdev.h>

typedef struct {
    float co2;
    float temp;
    float hum;
    uint8_t valid;
} CO2_Data;

extern i2c_dev_t co2sensordev;

void init_co2_sensor();
CO2_Data read_co2_sensor();
