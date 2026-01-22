
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from datetime import datetime
from datetime import datetime, timezone, timedelta
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client import Point, WritePrecision
import pandas as pd
import numpy as np
from config import *

ROOMINFO = {
    "kitchen": {"bucket": "1_7_12", "roomID": "door", "measurement": "door"},
    "fish": {"bucket": "1_8_13", "roomID": "fish", "measurement": "PIR"},
    "desk": {"bucket": "1_6_10", "roomID": "desk", "measurement": "PIR"}
}

import warnings
from influxdb_client.client.warnings import MissingPivotFunction
warnings.simplefilter("ignore", MissingPivotFunction)
        
class RoomInfo: 
    def __init__(self, roomname, infodict:dict=ROOMINFO):
        self.infodict = infodict
        
        self.bucket = self.infodict.get(roomname).get("bucket")
        self.roomID = self.infodict.get(roomname).get("roomID")
        self.measurement = self.infodict.get(roomname).get("measurement")


def timedelta_to_flux_min(td: timedelta) -> str:
    total_seconds = int(td.total_seconds())
    if total_seconds % 60 != 0:
        raise ValueError("Timedelta is not an exact number of minutes")
    minutes = total_seconds // 60
    if minutes <= 0:
        raise ValueError("Flux duration must be > 0")
    return f"{minutes}m"

def round_timestamp_to_nearest(timestamp:datetime, delta:timedelta):
    minutes = delta/timedelta(minutes=1)
    seconds = timestamp.timestamp()
    rounded = round(seconds/(minutes*60))*(minutes*60)
    return datetime.fromtimestamp(rounded, tz=timezone.utc)

def get_bucketized_occupancy(roomname, start:datetime, end:datetime, window:timedelta):
        """
        returns a bucketized series of timestamps of occupancy detections from start to end
        window = size of the bucket. Must be specified.
        Results are rounded to the nearest hour for ease

        1hr must be divisible by window, or window is a multiple of 1h
        """
        windowstr = timedelta_to_flux_min(window)
        client = influxdb_client.InfluxDBClient(
            url=URL_INFLUX,
            token=TOKEN_INFLUX,
            org=ORG
        )
        query_api = client.query_api()
        start = round_timestamp_to_nearest(start, window)
        end = round_timestamp_to_nearest(end, window)
        assert end > start

        start_buffered = start - timedelta(days=2)
        
        time_start = start.isoformat().replace("+00:00", "Z")
        time_end = end.isoformat().replace("+00:00", "Z")
        time_start_buffered = start_buffered.isoformat().replace("+00:00", "Z")

        # divide into buckets and count detections in each bucket
        room = RoomInfo(roomname)
        query = f"""
                from(bucket: "{room.bucket}")
                |> range(start: {time_start}, stop: {time_end})
                |> filter(fn: (r) => r["_measurement"] == "{room.measurement}" 
                                    and r["_field"] == "roomID" 
                                    and r["_value"] == "{room.roomID}")
                {f"|> aggregateWindow(every: {windowstr}, fn: count, createEmpty: true)" if window is not None else ""}
                """

        # zero df just in case there is nothing in influx 
        df = pd.DataFrame()
        df["_time"] = pd.date_range(start=pd.Timestamp(start + window), end=pd.Timestamp(end), freq=window, inclusive="both")
        df["_value"] = 0

        df_inflx = query_api.query_data_frame(org=ORG, query=query)
        if len(df_inflx) != 0: 
            df = df_inflx

        # when was the last detection with time <= current bucket?
        query = f"""
                lookback = 1d
                from(bucket: "{room.bucket}")
                |> range(start: {time_start_buffered}, stop: {time_end})
                |> filter(fn: (r) =>
                    r._measurement == "{room.measurement}" and
                    r._field == "roomID" and
                    r._value == "{room.roomID}"
                )
                |> keep(columns: ["_time", "_value"])
                |> map(fn: (r) => ({{ r with last_occupancy: r._time }}))
                |> aggregateWindow(every: {windowstr}, fn: last, createEmpty: true)
                |> fill(usePrevious: true, column: "last_occupancy")
                |> filter(fn: (r) => r._time > {time_start})
                |> keep(columns: ["_time", "last_occupancy"])
                """
        last_occupancy_time_df = pd.DataFrame()
        last_occupancy_time_df["_time"] = pd.date_range(start=pd.Timestamp(start), end=pd.Timestamp(end), freq=window)
        last_occupancy_time_df["last_occupancy"] = timedelta(days=2)

        last_occupancy_time_df_inflx = query_api.query_data_frame(org=ORG, query=query)
        if len(last_occupancy_time_df_inflx) != 0:
            last_occupancy_time_df = last_occupancy_time_df_inflx
        
        df["last_occupancy"] = last_occupancy_time_df["last_occupancy"]

        # make the boundaries explicit
        df = df.rename(columns={"_time":"end", "_value":"num_detections"})
        df["start"] = df["end"] - window
        df["name"] = roomname
        return df[["name", "start", "end", "num_detections", "last_occupancy"]]

def get_combined_bucketized_occupancy(start:datetime, end: datetime, window: timedelta, 
                                    rooms:list=["kitchen", "fish", "desk"], priority:list=[1, 2, 0]):
    
    """
    combine occupancy of rooms. If two bucket at the same time of two different rooms are both occupied 
    only the one with the most recent last_occupancy wins
    additionally there is a room NONE that gets occupied if no other room is occupied
    results are joined into a single dataset-ready dataframe: 

    start   end   <roomname>_occupied     occupancy_time        <roomname>_t_since_last_visit

    """
    
    start = round_timestamp_to_nearest(start, window)
    end = round_timestamp_to_nearest(end, window)

    room_dfs = []
    for room in rooms: 
        room_df = get_bucketized_occupancy(room, start, end, window)
        room_dfs.append(room_df)

    # latest occupancy wins

    for room1 in room_dfs: 
        room1_occupied = room1["num_detections"] > 0
        room1_name = room1["name"][0]
        for room2 in room_dfs:
            room2_name = room2["name"][0]
            if room1_name == room2_name:
                continue
            room2_occupied = room2["num_detections"] > 0
            conflicts = room2_occupied & room1_occupied
            room1_occupied &= (room1["last_occupancy"] > room2["last_occupancy"]) 
            #room1_occupied[conflicts] &= priority[rooms.index(room1_name)] > priority[rooms.index(room2_name)]
        
        room1["occupied"] = room1_occupied
        room1["time_since_last_visit"] = room1["end"] - room1["last_occupancy"]
        CAP_MIN = timedelta(days=2)
        room1["time_since_last_visit"] = (room1["time_since_last_visit"]
        .fillna(CAP_MIN)
        .clip(upper=CAP_MIN)
        )
        room1["time_since_last_visit"] *= room1["time_since_last_visit"] > window
    
    # the special room Void = no other room is active

    Void = pd.DataFrame()
    Void["start"] = room_dfs[0]["start"]
    Void["end"] = room_dfs[0]["end"]
    Void["occupied"] = True
    Void["name"] = "Void"
    
    for room in room_dfs:
        Void["occupied"] &= ~room["occupied"]
    
    room_dfs.append(Void)

    # compute occupation time for each room by counting the number of continuosly 
    # occupied bucket until and including the current bucket

    for i, room in enumerate(room_dfs): 
        occ = room["occupied"].astype(int)
        block_id = occ.ne(occ.shift(1)).cumsum()
        room["occupancy_time"] = (room.groupby(block_id).cumcount() + 1) * occ * window
        room["expected_occupancy_time"] = room.groupby(block_id)["occupancy_time"].transform("max")
    
    all_rooms = rooms + ["Void"]
    return room_dfs, all_rooms

def preprocess_to_features_labels(room_dfs:list):
    """
        process the data from get_combined_bucketized_occupancy into features and labels
    """

    features = []
    labels = []
    rooms = []
    for data in room_dfs:
        if len(data) == 0:
            features.append(pd.DataFrame())
            labels.append(pd.DataFrame())
            continue
        name = data["name"].iloc[0]
        rooms.append(name)
        feature_df = pd.DataFrame()
        label_df = pd.DataFrame()
        
        # onehot vector of weekday
        weekday = data["start"].dt.weekday
        for i in range(7):
            feature_df[f"is_weekday_{i}"] = weekday == i

        if name != "Void":
            feature_df["t_since_last_visit"] = np.log(data["time_since_last_visit"].dt.total_seconds()/60 + 1)
        
        feature_df["occupancy_time"] = data["occupancy_time"].dt.total_seconds()/60
        feature_df["occupancy_time"] = np.log(feature_df["occupancy_time"] + 1)

        label_df["expected_occupancy_time"] = data["expected_occupancy_time"].dt.total_seconds()/60
        label_df["expected_occupancy_time"] = np.log(label_df["expected_occupancy_time"] + 1)

        # sin, cos of time since midnight
        t_since_midnight = (data["end"] - data["start"].dt.normalize()).dt.total_seconds()/60
        feature_df["sin_t"] = np.sin(2*np.pi*t_since_midnight/1440)
        feature_df["cos_t"] = np.cos(2*np.pi*t_since_midnight/1440)

        feature_df["occupied"] = data["occupied"]

        features.append(feature_df)
        labels.append(label_df)


    return features, labels, rooms


if __name__ == "__main__":
    start = datetime(2026, 1, 14, tzinfo=timezone.utc)
    end = datetime(2026, 1, 15, tzinfo=timezone.utc)
    #get_bucketized_occupancy("fish", start, end, window=timedelta(minutes=30))
    room_dfs, rooms = get_combined_bucketized_occupancy(start=start, end=end, window=timedelta(minutes=15))
    preprocess_to_features_labels(room_dfs)
    print(room_dfs)
    