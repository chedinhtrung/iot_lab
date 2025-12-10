from config import *
from datetime import datetime, timezone, timedelta
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
import pandas as pd
import numpy as np

def get_latest_stay_stats(roomname, range:str="-7d"):
    client = influxdb_client.InfluxDBClient(
            url=URL,
            token=TOKEN,
            org=ORG
        )
    query_api = client.query_api()
    query = f"""
            from(bucket: "stays")
            |> range(start: {range})
            |> pivot(
                rowKey: ["_time"],
                columnKey: ["_field"],
                valueColumn: "_value"
            )
            |> filter(fn: (r) => r["roomID"] == "{roomname}")
            |> sort(columns: ["_time"], desc: true)
            """
    result = query_api.query_data_frame(org=ORG, query=query)
    if len(result)!= 0:
        print(f"Warning: did not find any stay in the past {range}")
        return {"valid": False}
    
    return {"valid": True, "mean": np.mean(result["duration"]), "var": np.var(result["duration"])}

    

if __name__ == "__main__":
    get_latest_stay_stats("desk")


    