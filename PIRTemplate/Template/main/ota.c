#include "ota.h"

#include "esp_https_ota.h"
#include "esp_log.h"

extern char device_key[800];

static esp_err_t _handle_headers(esp_http_client_handle_t client)
{
    esp_err_t err = ESP_OK;
    err = esp_http_client_set_header(client, "Authorization", device_key);
    return err;
}

void do_firmware_upgrade()
{
    esp_http_client_config_t config = {
        .url = CONFIG_IOT_PLATFORM_OTA_URL,
        .buffer_size_tx = 1024,
    };
    esp_https_ota_config_t ota_config = {
        .http_config = &config,
        .http_client_init_cb = _handle_headers,
    };

    esp_err_t ret = esp_https_ota(&ota_config);
    if (ret == ESP_OK)
    {
        esp_restart();
    }
    else
    {
        ESP_LOGE("OTA", "Firmware upgrade failed");
    }
}
