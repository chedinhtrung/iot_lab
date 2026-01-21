from datetime import datetime
from datetime import datetime, timezone, timedelta
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client import Point, WritePrecision
import pandas as pd
import numpy as np

import warnings
from influxdb_client.client.warnings import MissingPivotFunction
warnings.simplefilter("ignore", MissingPivotFunction)
from config import *

ROOMINFO = {
    "kitchen": {"bucket": "1_7_12", "roomID": "door", "measurement": "door"},
    "fish": {"bucket": "1_8_13", "roomID": "fish", "measurement": "PIR"},
    "desk": {"bucket": "1_6_10", "roomID": "desk", "measurement": "PIR"}
}
        
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
            url=INFLUX_URL,
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
    start_buffered = start - timedelta(days=1)
    room_dfs = []
    for room in rooms: 
        room_df = get_bucketized_occupancy(room, start_buffered, end, window)
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

    for room in room_dfs: 
        occ = room["occupied"].astype(int)
        block_id = occ.ne(occ.shift(1)).cumsum()
        room["occupancy_time"] = (room.groupby(block_id).cumcount() + 1) * occ * window

    # join everything into one single dataframe 

    df = pd.DataFrame()
    df["start"] = room_dfs[0]["start"]
    df["end"] = room_dfs[0]["end"]
    df["occupancy_time"] = pd.to_timedelta(0)
    
    for room in room_dfs: 
        roomname = room["name"][0]
        df[f"{roomname}_occupied"] = room["occupied"]
        if roomname != "Void":
            df[f"{roomname}_t_since_last_visit"] = room["time_since_last_visit"]
        
        df["occupancy_time"] += room["occupancy_time"]  # only the active room has non zero occupancy time
    
    # cut the buffer part
    df = df[df["start"] > start]
    
    all_rooms = rooms + ["Void"]
    return df, all_rooms

def preprocess_to_features(data:pd.DataFrame, rooms) -> pd.DataFrame:
    """
        process the data from get_combined_bucketized_occupancy into features
    """

    feature_df = pd.DataFrame()

    # sin, cos of time since midnight
    t_since_midnight = (data["end"] - data["start"].dt.normalize()).dt.total_seconds()/60
    feature_df["sin_t_since_midnight"] = np.sin(2*np.pi*t_since_midnight/1440)
    feature_df["cos_t_since_midnight"] = np.cos(2*np.pi*t_since_midnight/1440)
    
    # onehot vector of weekday
    weekday = data["start"].dt.weekday
    for i in range(7):
        feature_df[f"is_weekday_{i}"] = weekday == i
    
    # onehot vector of rooms
    feature_df[[f"{room}_occupied" for room in rooms + ["Void"]]] = data[[f"{room}_occupied" for room in rooms + ["Void"]]]

    feature_df[[f"{room}_t_since_last_visit" for room in rooms]] = data[[f"{room}_t_since_last_visit" for room in rooms]].apply(lambda s: np.log(s.dt.total_seconds()/60 + 1))
    
    feature_df["occupancy_time"] = data["occupancy_time"].dt.total_seconds()/60
    feature_df["occupancy_time"] = np.log(feature_df["occupancy_time"] + 1)

    return feature_df
    

def preprocess_to_features_labels(data:pd.DataFrame, rooms, horizon:timedelta)->pd.DataFrame:
    """
        shifts the feature some steps into the future and compute the label vector (index of the occupied room) from the one hot
        meant to be used with the LogRegPredictive model
    """
    feature_df = preprocess_to_features(data, rooms)
   
    window = data["end"][0] - data["start"][0]
    horizon_index = int(horizon/window)
    labels = feature_df[[f"{room}_occupied" for room in rooms + ["Void"]]].shift(-horizon_index).values.argmax(axis=1)
    labels = labels[:-horizon_index]
    feature_df = feature_df.iloc[:-horizon_index]

    assert len(labels) == len(feature_df)
    return feature_df, labels

def export_csv_to_minio(df:pd.DataFrame, filename:str):
    pass

def get_individualized_occupancy(roomname:str, start:datetime, end: datetime, window: timedelta, 
                                    rooms:list=["kitchen", "fish", "desk"], priority:list=[1, 2, 0]):
    """
        processes exactly the same as get_combined_bucketized_occupancy, without the 
        "latest occupancy wins" part - meant for chatbot use
    """
    if roomname not in rooms + ["Void"]:
        return None, None
    
    start = round_timestamp_to_nearest(start, window)
    end = round_timestamp_to_nearest(end, window)
    start_buffered = start - timedelta(days=1)
    room_dfs = []
    for room in rooms: 
        room_df = get_bucketized_occupancy(room, start_buffered, end, window)
        room_dfs.append(room_df)
    
    # the special room Void = no other room is active

    Void = pd.DataFrame()
    Void["start"] = room_dfs[0]["start"]
    Void["end"] = room_dfs[0]["end"]
    Void["occupied"] = True
    Void["name"] = "Void"
    for room in room_dfs:
        room_occupied = room["num_detections"] > 0
        room["occupied"] = room_occupied
        Void["occupied"] &= ~room["occupied"]
    
    room_dfs.append(Void)
    all_rooms = rooms + ["Void"]

    room1 = room_dfs[all_rooms.index(roomname)]
    if roomname != "Void":
        room1_occupied = room1["num_detections"] > 0
        room1["occupied"] = room1_occupied
        CAP_MIN = timedelta(days=2)
        room1["time_since_last_visit"] = room1["end"] - room1["last_occupancy"]
        room1["time_since_last_visit"] = (room1["time_since_last_visit"]
            .fillna(CAP_MIN)
            .clip(upper=CAP_MIN)
            )
        room1["time_since_last_visit"] *= room1["time_since_last_visit"] > window
        room1["time_since_last_visit"] = room1["end"] - room1["last_occupancy"]
    
   

    # compute occupation time for each room by counting the number of continuosly 
    # occupied bucket until and including the current bucket

    occ = room1["occupied"].astype(int)
    block_id = occ.ne(occ.shift(1)).cumsum()
    room1["occupancy_time"] = (room1.groupby(block_id).cumcount() + 1) * occ * window
    
    # cut the buffer part
    room1 = room1[room1["start"] > start]
    
    return room1, all_rooms


if __name__ == "__main__":
    start = datetime(2026, 1, 19, tzinfo=timezone.utc)
    end = datetime(2026, 1, 20, tzinfo=timezone.utc)
    #get_bucketized_occupancy("fish", start, end, window=timedelta(minutes=30))
    room_df = get_individualized_occupancy(roomname="desk", start=start, end=end, window=timedelta(minutes=30))
    