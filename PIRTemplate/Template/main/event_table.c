#include <stdint.h>
#include "event_table.h"

RTC_DATA_ATTR EventTableData event_table[TABLE_SIZE] = {0};  
RTC_DATA_ATTR int table_index = -1;

int put_data(uint8_t type, uint8_t len, uint8_t* buf){
    if (table_index + 1 == TABLE_SIZE){
        return 1;          // Table full
    }
    table_index += 1;
    event_table[table_index].type = type;
    event_table[table_index].len = len;
    memcpy(&(event_table[table_index].payload), buf, len);
    return table_index + 1 == TABLE_SIZE;
}

void clear_table(void){
    table_index = -1;
}

void force_insert_data(uint8_t type, uint8_t len, uint8_t* buf){
    table_index = 0; 
    put_data(type, len, buf);
}