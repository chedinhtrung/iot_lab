#pragma once 
#define TABLE_SIZE 3

#include <stdint.h>
#include <string.h>
#include <esp_attr.h>
#define PIRDATA 0
#define DOORDATA 1
#define AIRDATA 2
#define BATDATA 3

typedef struct {
    uint8_t type;
    uint8_t len;
    uint8_t payload[254];
} EventTableData;

extern RTC_DATA_ATTR EventTableData event_table[TABLE_SIZE];  
extern RTC_DATA_ATTR int table_index;

int insert_data(uint8_t type, uint8_t len, uint8_t* buf);
