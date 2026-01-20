from config import *
from datetime import datetime, timezone, timedelta

from sifec_base import BaseEventFabric
from config import *
from influxdb_client import InfluxDBClient

class PeriodicFunctionEvent(BaseEventFabric):
    def __init__(self, func):
        super().__init__()
        self.func = func 
    
    def call(self):
        return self.func.__name__, None

class EmergencyEvent(BaseEventFabric):
    def __init__(self, data:dict):
        super().__init__()
        self.data = data 
    
    def call(self):
        return "emergency_event", self.data
    
def get_co2_level():
    query = """
        from(bucket: "1_8_14")
        |> range(start:-1d)
        |> filter(fn: (r) => r["_measurement"] == "air")
        |> filter(fn: (r) => r["_field"] == "co2")
        |> filter(fn: (r) => r["_type"] == "sensor-value")
        |> last()
    """
    client = InfluxDBClient(url=URL_INFLUX, token=TOKEN_INFLUX, org=ORG)
    query_api = client.query_api()
    df = query_api.query_data_frame(query)

    if len(df) != 0:
        return df["_value"][0]
    
    return None

    

if __name__ == "__main__":
    get_co2_level()