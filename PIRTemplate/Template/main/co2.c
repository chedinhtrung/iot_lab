#include "co2.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

extern i2c_config_t i2c_conf;

i2c_dev_t co2sensordev = {
    .port = 0,
    .addr = 0x62,          
};

CO2_Data read_co2_sensor()
{
    // get data ready status 
    uint16_t status;
    int tries = 0;
    while (!status && tries < 5){
        uint8_t cmd[2] = {0xE4, 0xB8};
        i2c_dev_write(&co2sensordev, cmd, 1, cmd+1, sizeof(cmd));
        vTaskDelay(pdMS_TO_TICKS(5));
        uint8_t resp[3];
        i2c_dev_read(&co2sensordev, NULL, 0, resp, sizeof(resp));
        status = (resp[0] << 8) | resp[1];
        status = status << 11;
        tries++;
        if (!status){vTaskDelay(pdMS_TO_TICKS(1000));}
    }
    if (tries == 5){
        CO2_Data invalid = {0};
        return invalid;
    }
    uint8_t cmd[2] = {0xec, 0x05};
    i2c_dev_write(&co2sensordev, cmd, 1, cmd+1, sizeof(cmd));
    vTaskDelay(pdMS_TO_TICKS(5));
    uint8_t resp[9];
    i2c_dev_read(&co2sensordev, NULL, 0, resp, sizeof(resp));
    uint16_t co2 = resp[0] << 8 | resp[1];
    uint16_t temp = resp[3] << 8 | resp[4];
    uint16_t hum = resp[6] << 8 | resp[7];

    CO2_Data data = {0}; 
    data.co2 = co2*1.0;
    data.temp = -45.0 + 175.0*temp/65535;
    data.hum = 100.0*hum/65535;
    data.valid = 1;
    return data;

}

void init_co2_sensor()
{
    co2sensordev.cfg = i2c_conf;
    ESP_ERROR_CHECK(i2c_dev_create_mutex(&co2sensordev));
    // start low power mode reads 
    uint8_t cmd[2] = {0x21, 0xac};
    i2c_dev_write(&co2sensordev, cmd, 1, cmd+1, sizeof(cmd));
}

