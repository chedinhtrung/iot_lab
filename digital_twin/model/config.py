import os

# Influx

ORG = os.getenv("INFLUX_ORG", "wise2025")

TOKEN = os.getenv(
    "INFLUX_TOKEN",
    "0NxTXKuB4iDmWJn0_FzwwQ45ZxZfpnDEQWAQItqHjx-rurBqwE8afYIRPwG2isnynumGim1FxdRyuSmqeEsQdg=="
)

INFLUX_URL = os.getenv(
    "INFLUX_URL",
    "http://192.168.0.103:8086"
)

# MinIO

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




