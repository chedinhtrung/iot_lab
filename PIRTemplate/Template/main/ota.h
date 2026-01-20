#ifndef _OTA_H
#define _OTA_H

void do_firmware_upgrade(void);

#define CONFIG_IOT_PLATFORM_OTA_URL "http://192.168.0.103:30020/api/users/1/ota/download/firmware/latest"

#endif
