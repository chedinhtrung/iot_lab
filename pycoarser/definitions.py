from config import *
from datetime import datetime, timezone, timedelta
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client import Point, WritePrecision
import pandas as pd
from time import sleep

import threading

class StayAggregator:
    def __init__(self, source_bucket:str, sensor_type:str, roomname:str, dest_bucket:str="stays", run_freq:int=30, cfg=default_cfg):
        self.sensor_type = sensor_type
        self.thread = threading.Thread(target=self.loop)
        self.last_run = datetime.now(tz=timezone.utc)
        self.last_run = self.last_run - timedelta(minutes=run_freq+1)
        self.roomname = roomname
        self.source_bucket = source_bucket
        self.dest_bucket = dest_bucket
        self.run_every = timedelta(minutes=run_freq)
        self.MAX_IDLE_TIME = cfg["MAX_IDLE_TIME"]
        self.MIN_STAY_DURATION = cfg["MIN_STAY_DURATION"]

        self.client = influxdb_client.InfluxDBClient(
            url=URL,
            token=TOKEN,
            org=ORG
        )
        self.query_api = self.client.query_api()
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
       
    
    def loop(self):
        while True:
            #if datetime.now() - self.last_run < self.run_every:
            #    sleep(AGGR_FREQ * 60)
            #    continue

            # start from GENESIS_TIME when the destination bucket is empty
            # aggr_t_start = GENESIS_TIME
            aggr_t_start = "-1d"

            # get the last stay and begin aggregating from its end
            query = f"""
            from(bucket: "{self.dest_bucket}")
            |> range(start: 0)
            |> pivot(
                rowKey: ["_time"],
                columnKey: ["_field"],
                valueColumn: "_value"
            )
            |> filter(fn: (r) => r["roomID"] == "{self.roomname}")
            |> sort(columns: ["_time"], desc: true)
            |> limit(n: 1)
            """
            result = self.query_api.query_data_frame(org=ORG, query=query)
            if len(result)!= 0:
                aggr_t_start = result["end"][0]
            
            # query the source bucket
            query = f"""
            from(bucket: "{self.source_bucket}")
            |> range(start: {aggr_t_start})
            |> pivot(
                rowKey: ["_time"],
                columnKey: ["_field"],
                valueColumn: "_value"
            )
            |> filter(fn: (r) => r["roomID"] == "{self.roomname}")
            """
            df = self.query_api.query_data_frame(org=ORG, query=query)
            stays = [] 
            current_stay = {}
            last_event_t = None
            # iterate thru the events, aggregate according to definition of "stays"     
            for index, entry in df.iterrows():
                if last_event_t is None:
                    last_event_t = entry["_time"].to_pydatetime() 

                if current_stay.get("start") is None: 
                    current_stay["start"] = entry["_time"].to_pydatetime()    

                current_event_t = entry["_time"].to_pydatetime()  
                if current_event_t - last_event_t < timedelta(minutes=self.MAX_IDLE_TIME):     # skip immediately following events
                    last_event_t = current_event_t
                    continue
                
                stay_duration = last_event_t - current_stay["start"]
                if stay_duration < timedelta(minutes=self.MIN_STAY_DURATION):  # skip if stay too short
                    last_event_t = current_event_t
                    current_stay = {}
                    continue
                    
                current_stay["end"] = last_event_t
                stays.append(current_stay)
                current_stay = {}
                last_event_t = current_event_t
            print(f"aggregated {len(stays)}")

            for stay in stays:
                duration = int((stay["end"] - stay["start"]).total_seconds())
                p = (Point("stay_aggr").time(stay["start"], WritePrecision.S)     # timestamp of the point is the same as start of the stay
                                        .field("start", stay["start"].isoformat().replace("+00:00", "Z"))
                                        .field("end", stay["end"].isoformat().replace("+00:00", "Z"))
                                        .field("duration", duration)
                                        .field("roomID", self.roomname))
                self.write_api.write(bucket=self.dest_bucket, org=ORG, record=p)

class ActivityAggregator:
    def __init__(self, source_bucket:str, roomname:str, dest_bucket:str="activities", run_freq:int=30, cfg=default_cfg):
        self.thread = threading.Thread(target=self.loop)
        self.last_run = datetime.now(tz=timezone.utc)
        self.last_run = self.last_run - timedelta(minutes=run_freq+1)
        self.roomname = roomname
        self.source_bucket = source_bucket
        self.dest_bucket = dest_bucket
        self.run_every = timedelta(minutes=run_freq)
        self.MAX_AWAY_TIME = cfg["MAX_AWAY_TIME"]

        self.client = influxdb_client.InfluxDBClient(
            url=URL,
            token=TOKEN,
            org=ORG
        )
        self.query_api = self.client.query_api()
        self.write_api = self.client.write_api()

    def loop(self):
        while True:
            #if datetime.now() - self.last_run < self.run_every:
            #    sleep(AGGR_FREQ * 60)
            #    continue

            # start from GENESIS_TIME when the destination bucket is empty
            # aggr_t_start = GENESIS_TIME
            aggr_t_start = "-1d"
            # get the last aggregate
            query = f"""
            from(bucket: "{self.dest_bucket}")
            |> range(start: 0)
            |> pivot(
                rowKey: ["_time"],
                columnKey: ["_field"],
                valueColumn: "_value"
            )
            |> filter(fn: (r) => r["roomID"] == "{self.roomname}")
            |> sort(columns: ["_time"], desc: true)
            |> limit(n: 1)
            """

            result = self.query_api.query_data_frame(org=ORG, query=query)
            if len(result)!= 0:
                aggr_t_start = result["end"][0]
            
            # query the source bucket
            query = f"""
            from(bucket: "{self.source_bucket}")
            |> range(start: {aggr_t_start})
            |> pivot(
                rowKey: ["_time"],
                columnKey: ["_field"],
                valueColumn: "_value"
            )
            |> filter(fn: (r) => r["roomID"] == "{self.roomname}")
            """
            df = self.query_api.query_data_frame(org=ORG, query=query)
            activities = [] 
            current_activity = {}
            last_stay = None
            # iterate thru the stays, aggregate according to definition of "activities"     
            for index, entry in df.iterrows():
                current_stay_start = datetime.fromisoformat(entry["start"].replace("Z", "+00:00"))
                current_stay_end = datetime.fromisoformat(entry["end"].replace("Z", "+00:00"))
                if last_stay is None:
                   last_stay = entry
                if current_activity.get("start") is None: 
                    current_activity["start"] = current_stay_start
                
                last_stay_end = datetime.fromisoformat(last_stay["end"].replace("Z", "+00:00"))
                
                away_time = current_stay_start - last_stay_end
                if away_time < timedelta(minutes=self.MAX_AWAY_TIME):
                    last_stay = entry
                    continue

                current_activity["end"] = last_stay_end
                activities.append(current_activity)
                current_activity = {"start": current_stay_start}
                last_stay = entry
            
            if current_activity.get("end") is None and last_stay is not None:
                last_stay_end = datetime.fromisoformat(last_stay["end"].replace("Z", "+00:00"))
                current_activity["end"] = last_stay_end
                activities.append(current_activity)
                current_activity = {}

            print(f"aggregated {len(activities)} activities")

            for activity in activities:
                duration = int((activity["end"] - activity["start"]).total_seconds())
                p = (Point("stay_aggr").time(activity["start"], WritePrecision.S)     # timestamp of the point is the same as start of the stay
                                        .field("start", activity["start"].isoformat().replace("+00:00", "Z"))
                                        .field("end", activity["end"].isoformat().replace("+00:00", "Z"))
                                        .field("duration", duration)
                                        .field("roomID", self.roomname))
                self.write_api.write(bucket=self.dest_bucket, org=ORG, record=p)
