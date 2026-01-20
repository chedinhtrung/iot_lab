from sifec_base import LocalGateway, base_logger, PeriodicTrigger, ExampleEventFabric
from utils import *
from datetime import datetime

app = LocalGateway(mock=False)
app.local_port = "8001"

def handle_emergency(data:dict):
    print(f"emergency event received!")
    data = data.get("emergency_event").get("data")
    print(data)
    todo = Todo(
        text=data.get("task"),
        timestamp=datetime.fromisoformat(data.get("timestamp")) if data.get("timestamp") else None,
        priority=data.get("priority")
    )
    todo.push_to_influx()

    return

app.deploy(cb=handle_emergency, name="handle_emergency", evts="emergency_event", method="POST")

