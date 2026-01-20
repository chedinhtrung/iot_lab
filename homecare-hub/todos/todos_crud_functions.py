import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client import Point, WritePrecision, InfluxDBClient
from datetime import datetime, timezone
from pydantic import BaseModel
import uuid

ORG = "wise2025"
TOKEN = "FrE7QsTmmI9QMYlsE1_kJ_IC1ErCObNaqOBWN3FKkP4JX6DXXlGbBh_UsKON-lfKDwJyQhiVrwGoniRHylmamw=="
URL="http://192.168.0.103:8086"

TODO_BUCKET = "todos"


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
        with InfluxDBClient(url=URL, org=ORG, token=TOKEN, verify_ssl=False) as client:
            write_api = client.write_api(write_options=SYNCHRONOUS)
            write_api.write(bucket=TODO_BUCKET, record=self.to_influx_point())
            print(f"Write todo {self.text} to Influx")

    def delete(self):
        with InfluxDBClient(url=URL, org=ORG, token=TOKEN, verify_ssl=False) as client:
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

def get_todos():
    query = f"""
        from(bucket: "{TODO_BUCKET}")
        |> range(start: -30d)
        |> filter(fn: (r) => r._measurement == "todos")
        |> pivot(
            rowKey: ["_time"],
            columnKey: ["_field"],
            valueColumn: "_value"
        )
    """
    with InfluxDBClient(url=URL, org=ORG, token=TOKEN, verify_ssl=False) as client:
        read_api = client.query_api()
        tables = read_api.query(query)
    
    todos: list[Todo] = []

    for table in tables:
        for rec in table.records:
            v = rec.values

            todos.append(
                Todo(
                    uid=v["uid"],
                    text=v["text"],
                    priority=v["priority"],   # tag → already a column
                    is_done=v["is_done"],     # tag → already a column
                    timestamp=v["_time"],
                )
            )
    return todos
    

if __name__ == "__main__":
    todos = get_todos()
    print(todos)
    todos[0].delete()
    