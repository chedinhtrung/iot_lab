import os

ORG = os.getenv("ORG", "wise2025") 
TOKEN_INFLUX = os.getenv("TOKEN_INFLUX", "0NxTXKuB4iDmWJn0_FzwwQ45ZxZfpnDEQWAQItqHjx-rurBqwE8afYIRPwG2isnynumGim1FxdRyuSmqeEsQdg==")
TOKEN_TODOS = os.getenv("TOKEN_TODOS", "FrE7QsTmmI9QMYlsE1_kJ_IC1ErCObNaqOBWN3FKkP4JX6DXXlGbBh_UsKON-lfKDwJyQhiVrwGoniRHylmamw==")

INFLUX_URL=os.getenv("INFLUX_URL", "http://192.168.0.103:8086")