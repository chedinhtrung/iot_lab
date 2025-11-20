from config import *
from datetime import datetime, timezone, timedelta
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
import pandas as pd
from time import sleep

import threading

class Stay:
    def __init__(self,start_time):
        self.start = start_time
        self.end = start_time
    
    def is_valid(self):
        return (self.end - self.start)/60.0 > MIN_STAY_DURATION

class Activity:
    def __init__(self,start_time):
        self.start = start_time
        self.end = start_time

class StayAggregator:
    def __init__(self, source_bucket:str, sensor_type:str, roomname:str, dest_bucket:str="stays", run_freq:int=AGGR_FREQ):
        self.sensor_type = sensor_type
        self.thread = threading.Thread(target=self.loop)
        self.last_run = datetime.now(tz=timezone.utc)
        self.last_run = self.last_run - timedelta(minutes=run_freq+1)
        self.roomname = roomname
        self.source_bucket = source_bucket
        self.dest_bucket = dest_bucket
        self.run_every = timedelta(minutes=run_freq)

        self.client = influxdb_client.InfluxDBClient(
            url=url,
            token=token,
            org=org
        )
        self.query_api = self.client.query_api()
       
    
    def loop(self):
        while True:
            if datetime.now() - self.last_run < self.run_every:
                sleep(AGGR_FREQ * 60)
                continue

            # start from GENESIS_TIME when the destination bucket is empty
            aggr_t_start = GENESIS_TIME
            # get the last aggregate
            query = f"""
            from(bucket: "{self.dest_bucket}")
            |> range(start: 0)
            |> filter(fn: (r) => r["_measurement"] == "roomID")
            |> filter(fn: (r) => r["_value"] == "{self.roomname}")
            |> filter(fn: (r) => r["_value"] == "{self.roomname}")
            |> last()
            """
            result = self.query_api.query_data_frame(org=org, query=query)
            if len(result)!= 0:
                aggr_t_start = result["start"]
            
            # query the source bucket
            query = f"""
            from(bucket: "{self.source_bucket}")
            |> range(start: {aggr_t_start})
            |> filter(fn: (r) => r["_field"] == "roomID")
            |> filter(fn: (r) => r["_value"] == "{self.roomname}")
            """
            df = self.query_api.query_data_frame(org=org, query=query)
            stays = [] 
            current_stay = {}
            current_event_t = datetime.fromisoformat(aggr_t_start)       
            for index, entry in df.iterrows():
                current_stay["start"] = df["_time"][0].to_pydatetime()    

           

class ActivityAggregator:
    def __init__(self):
        pass


