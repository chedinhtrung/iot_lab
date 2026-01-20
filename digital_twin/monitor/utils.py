from config import *
from datetime import datetime, timezone, timedelta

from sifec_base import BaseEventFabric
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client import Point, WritePrecision, InfluxDBClient
from datetime import datetime, timezone
from pydantic import BaseModel
import uuid
from config import *

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
    
## Helper class to insert ToDos into the database

class Todo:
    def __init__(self, text="", is_done=False, priority:int=10, uid:str=None, timestamp=None):
        self.text = text
        self.is_done = is_done == "True"
        self.raw_timestamp = datetime.now(tz=timezone.utc) if timestamp is None else timestamp
        self.priority = priority
        self.uid=uuid.uuid4() if uid is None else uuid.UUID(uid)
        self.timestamp = self.raw_timestamp.strftime("%Y-%m-%d %H:%M:%S")

    def to_influx_point(self)->Point:
        return (
            Point("todos")
            .tag("priority", self.priority)
            .tag("is_done", self.is_done)
            .field("text", self.text)
            .tag("uid", str(self.uid))
            .time(self.raw_timestamp)
        )
    
    def push_to_influx(self):
        with InfluxDBClient(url=URL, org=ORG, token=TOKEN_TODOS, verify_ssl=False) as client:
            write_api = client.write_api(write_options=SYNCHRONOUS)
            write_api.write(bucket=TODO_BUCKET, record=self.to_influx_point())
            print(f"Write todo {self.text} to Influx")

    def delete(self):
        with InfluxDBClient(url=URL, org=ORG, token=TOKEN_TODOS, verify_ssl=False) as client:
            delete_api = client.delete_api()

            start = datetime(1970, 1, 1, tzinfo=timezone.utc)  # "from the beginning"
            stop  = datetime.now(timezone.utc)

            predicate = f'_measurement="todos" AND uid="{str(self.uid)}"'

            delete_api.delete(
                start=start,
                stop=stop,
                predicate=predicate,
                bucket=TODO_BUCKET,
                org=ORG
            )

if __name__ == "__main__":
    pass