#pragma once


//#define EXAMPLE_ESP_WIFI_SSID      "CAPS-Seminar-Room"
//#define EXAMPLE_ESP_WIFI_PASS      "caps-schulz-seminar-room-wifi"
//#define SNTP_SERVER_NAME           "ntp1.in.tum.de"

#define EXAMPLE_ESP_WIFI_SSID      "Rover_Wifi"
#define EXAMPLE_ESP_WIFI_PASS      "10172002"
#define SNTP_SERVER_NAME           "pool.ntp.org"

#define MQTT_BROKER                "192.168.0.103" 

#define DEVICE_ID_DESK                  "6"
#define DEVICE_TOPIC_DESK               "1/6/data"
#define DEVICE_KEY_DESK                 "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3NjE1OTY4NDksImlzcyI6ImlvdHBsYXRmb3JtIiwic3ViIjoiMS82In0.sYOwasaKz40wNL58b1S9l_0qMga77zef1Ca5JykxFSYxHQxZxLVhDTQgMkjqJUjTMuAIbB7NsO_feDEe8DcQHa74KyZcUa3o1Ogn8uKHDkMLhIQK4FrixoudYdjGXw9DXkaZIivR8mvBIhgcKHv8pHZjpSQBx7l6H9lyINyVCx9qDxRElI1kX53-xR0RGuybOYQW3mREYDepiK6N8LOY9N50UWSk1zoz3qZUz3me0JhhMLsabUWl5MVO0C2ga12Jayg4OkUHluRBg5qa9TD_bJZTT28T-zGmw_aQWCmYHrUrLT8VyX59a7NxKiNwYxeiCy1h6QbGjxDIUFU5qDbMOzsIMApkgrDT2IMsgaob8GOIqK6TZh5qu5neRoaHehiNptoZk4I4bWpoUgHM4u26y6qV7WRr9ZtzSNZ8EO63oO8wfht1-MWqBCUE6eUvl_UE3cDdYqi-AjSfcU20ZSLCiSOykTg-Ya2ibfV0olvmG4YSaW6kLLqwj-maehI7pesc4anYPF9UghRgH5sHMIpCYF1b03Y8N11hwFI-DnFz7Th1JXOfZMHqOjjhKcQc_mHjDhaTVHElbrISaMp-S0EVaa2V9lzhqa-Wn56bwLP3a4rFfKTWVd4d91tnWC_udWdDXU2Ciun1g4Q5CdNoKjeSkvKjEWkQzZVS9Vols11ayoE"

#define DEVICE_ID_DOOR                  "7"
#define DEVICE_TOPIC_DOOR               "1/7/data"
#define DEVICE_KEY_DOOR                 "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3NjIxMTg3NTcsImlzcyI6ImlvdHBsYXRmb3JtIiwic3ViIjoiMS83In0.wDN4p11illmaE80iNLWNTIk0r6U83h8MGQw8tq8rX0Nr3aFx2ExZ6uw0X5wPRMPVbiazmkT7zkQiKGc_vhQnAxc3rdU4BM1W9nt48tWfijhNHeGmXURsYF54XMiXNc2dRWjSUczqxJkyOr3M7SmTH8DorHwqdberkxzB3-s1wI5nm7CjQpktGpi-aalBiG3CHL663WFttrBBoDNCNjl0zQYIGrpNW8V-J6hzLDHgtEY5C32vhVrT82u-4YihGFJ4PvfavEhrGz5X8FSpzJ29S_BtfSTx0YNhKuYWWsiGAjaHYyoIxxsMnee0rBsJFGfPdUR1mjvXK1jhzCdhrjRCWCNdxlu2nBPnKpQfNzSmwBAcD_bESWhZhq8813l4WZG6f3cz6FNNKAzuBX6-u1qAAesPG5_mqdX-ix-wzy3RqyjinvzpRnVVxgpL0j27zgM2vDgVqVM8ReeHW7CEj8XxBGwMydxoDfxVC0giIc-vRTr4FdouSSDVmm0uXlTK7oCoI2DpqyCfbJ-ZYpwnwG5vOTEJPMsnT-hU3pKt3H0jewaCuKk_HS2EYKsxZaSaLR75VaEvwR0h8tnw1hW7QAn8m4q4JAGZEVmRP0lCygNhHjbpOiZZvllHI4qvNyewI_Dl79IAMVc8dLewQlhBAtxNnaC3bw5tVVQHbBYCU7rIyUA"

#define DEVICE_ID_FISH                  "8"
#define DEVICE_TOPIC_FISH               "1/8/data"
#define DEVICE_KEY_FISH                 "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3NjIyNTU5NjksImlzcyI6ImlvdHBsYXRmb3JtIiwic3ViIjoiMS84In0.a-K6XNbjGSPUJrlY3bN2ts3aVqK6JBLkpaP47QeOSFjmFiJfJyZqYGFBqih-oIZueSYLPYXkh_bBIE2dzjxDO5jlS1wN5Fl25K9G8Wnb-yU7Fnso8ce4lFk4kWouFiHFefBxweUNZMJzatatxWY24Pt2lsPLxd7tdeUP8ixscI2SwdWHQKWm1v2-leS7NERgRKrq9PChJLp8oJJTvIiRV7G5MclUTJwOGos2DAvvjtQxAQXi1Ilib2pb6jlb9rzLctlmd8kWH9ekwTbGmUhygixiJDX0QIK_AD8YbtOxhMEIz7DuyrzW6jUIh3JucTgfFomtJiZX9b76cfaw4j__IqwOQtTmDbeM6ZbDLyO4ZO78-T2djp6fzMzF1mecrIYFZBXusB1tBkD0lhVci2GccyBjV8MAtojJveTFiziwVYYqZ6xZ5UnYDvF5iA4k_PcrBVTNO12Is8tAfXJabeoN3SJC0qgGP7yvew4YRPs6zCNziiZmPU49MM4hpEs80E0I9gwrs3ruXktE97e_MZqPPsvO8s-wXxTqO0wGET-GdkfIShhS5IBrdWpWOQcTrUhLKVJ_iZkFdcOFO2rgYkMBjtYBrK-MfLGovD3Oog3cpUPm18mvwP2sJddsmE1W2xhzMoBdxAVG9rw002gObnL98klffMX1LvS8Ozzn-Ij-Cao"

#define PIR_PIN 27 

#define DEV_A_MAC 259907273942976
#define DEV_B_MAC 163524408132084
#define DEV_C_MAC 163524409355540

#define LED 17
#define RTC_WU_PIN 33
#define SDA_PIN 14
#define SCL_PIN 15

#define RSSI_TH -69
