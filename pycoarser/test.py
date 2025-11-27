import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
import pandas as pd

from definitions import *

bucket = "1_6_10"
ORG = "wise2025"
TOKEN = "8uBHEkrfX5j62cXcwlYdDticnx8QaTXQyW0ONBe1ebGS9Stxh0_32FbAjPx9Rfk5bqppNseTFAHJG2Qx3O8vRw=="
# Store the URL of your InfluxDB instance
URL="http://192.168.0.103:8086"

client = influxdb_client.InfluxDBClient(
    url=URL,
    token=TOKEN,
    org=ORG
)

# Query script
query_api = client.query_api()
query = f"""
 from(bucket: "{bucket}")
|> range(start: 0)
|> last()
"""

result = query_api.query_data_frame(org=ORG, query=query)

print(result)
