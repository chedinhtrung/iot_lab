import os

ORG = os.getenv("ORG", "wise2025") 
TOKEN_INFLUX = os.getenv("TOKEN_INFLUX", "0NxTXKuB4iDmWJn0_FzwwQ45ZxZfpnDEQWAQItqHjx-rurBqwE8afYIRPwG2isnynumGim1FxdRyuSmqeEsQdg==")
TOKEN_TODOS = os.getenv("TOKEN_TODOS", "FrE7QsTmmI9QMYlsE1_kJ_IC1ErCObNaqOBWN3FKkP4JX6DXXlGbBh_UsKON-lfKDwJyQhiVrwGoniRHylmamw==")

INFLUX_URL=os.getenv("INFLUX_URL", "http://192.168.0.103:8086")
TODO_BUCKET = "todos"

SCH_SERVICE_NAME = os.getenv("SCH_SERVICE_NAME", "http://192.168.0.103:30032")

MINIO_URL = os.getenv(
    "MINIO_URL",
    "192.168.0.103:9090"
)

MINIO_ACCESSKEY = os.getenv(
    "MINIO_ACCESSKEY",
    "bSYIFuEHZa3JHTKg6WE9"
)

MINIO_SECRETKEY = os.getenv(
    "MINIO_SECRETKEY",
    "u8TnjmYYEcUJNugWSOUZwXEDqu2FU2JToOIAx2Lt"
)

MODEL_SERVICE = os.getenv(
    "MODEL_SERVICE",
    "http://localhost:8000/api/predict"
)
