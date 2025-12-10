from config import *
from datetime import datetime, timezone, timedelta
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
import pandas as pd
import numpy as np

import urllib3
import logging
import os

from sifec_base import BaseEventFabric

logger = logging.getLogger("fastapi_cli")

def get_latest_stay(roomname:str):
    client = influxdb_client.InfluxDBClient(
            url=URL,
            token=TOKEN,
            org=ORG
        )
    query_api = client.query_api()
    query = f"""
            from(bucket: "stays")
            |> range(start: 0)
            |> pivot(
                rowKey: ["_time"],
                columnKey: ["_field"],
                valueColumn: "_value"
            )
            |> filter(fn: (r) => r["roomID"] == "{roomname}")
            |> sort(columns: ["_time"], desc: true)
            |> limit(n: 1)
            """
    result = query_api.query_data_frame(org=ORG, query=query) 
    return result

def get_latest_model(roomname:str):
    return {"mean": 10, "var": 4}


def is_emergency(data, model):
    sigma = np.sqrt(model["var"])
    mu = model["mean"]
    prob = (1 / (np.sqrt(2 * np.pi) * sigma)) * np.exp(-0.5 * ((data - mu) / sigma)**2)
    return prob < 0.05, prob

def emit_emergency_event(data): 
    # Deprecated
    sch_url = os.environ.get("SCH_SERVICE_NAME", "http://localhost:8080")
    url = f"{sch_url}/api/event"
    try:
        http = urllib3.PoolManager()
        res = http.request('POST', url, json={"name":"EmergencyEvent", "data": [data]}, retries=urllib3.Retry(5))
        if res.status >= 300:
            logger.error(
                f"Failure emitting the event because {res.reason}")
    except Exception as err:
        logger.error(f"Failure emitting the event to scheduler {url}")
        logger.error(err)


class EmergencyEvent(BaseEventFabric):
    def __init__(self, data):
        super().__init__()
        self.data = data if isinstance(data, list) else [data]
        self.name = "EmergencyEvent"
    
    def call(self, *args, **kwargs):
        return self.name, self.data



class TrainOccupancyModelEvent(BaseEventFabric):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.name = "TrainOccupancyModelEvent"
    
    def call(self):
        return self.name, []
    

class CheckEmergencyEvent(BaseEventFabric):
    def __init__(self):
        super().__init__()
        self.name = "CheckEmergencyEvent"
    
    def call(self, *args, **kwargs):
        return self.name, []
    
if __name__ == "__main__":
    get_latest_stay("desk")