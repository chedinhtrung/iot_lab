from datetime import datetime
from datetime import datetime, timezone, timedelta
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client import Point, WritePrecision
import pandas as pd


ROOMINFO = {
    "kitchen": {"bucket": "1_7_12", "roomID": "door", "measurement": "door"},
    "fish": {"bucket": "1_8_13", "roomID": "fish", "measurement": "PIR"},
    "desk": {"bucket": "1_6_10", "roomID": "desk", "measurement": "PIR"}
}


ORG = "wise2025"
TOKEN = "0NxTXKuB4iDmWJn0_FzwwQ45ZxZfpnDEQWAQItqHjx-rurBqwE8afYIRPwG2isnynumGim1FxdRyuSmqeEsQdg=="
URL="http://192.168.0.103:8086"
        
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

def get_occupancy(roomname, start:datetime, end:datetime, window:timedelta=None):
        """
        returns a raw series of timestamps of occupancy detections from start to end,
        rounded to days by default
        if window is specifed, a bucketized version is returned with _time aligned to the bucket's end time
        """
        windowstr = timedelta_to_flux_min(window)
        client = influxdb_client.InfluxDBClient(
            url=URL,
            token=TOKEN,
            org=ORG
        )
        query_api = client.query_api()
        """ returns all detections of the room from time start to time end """
        
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = end.replace(hour=0, minute=0, second=0, microsecond=0)
        
        time_start = start.isoformat().replace("+00:00", "Z")
        time_end = end.isoformat().replace("+00:00", "Z")

        room = RoomInfo(roomname)
        query = f"""
                from(bucket: "{room.bucket}")
                |> range(start: {time_start}, stop: {time_end})
                |> filter(fn: (r) => r["_measurement"] == "{room.measurement}" 
                                    and r["_field"] == "roomID" 
                                    and r["_value"] == "{roomname}")
                {f"|> aggregateWindow(every: {windowstr}, fn: count, createEmpty: true)" if window is not None else ""}
                """

        df = query_api.query_data_frame(org=ORG, query=query)

        query = f"""
                from(bucket: "{room.bucket}")
                |> range(start: {time_start}, stop: {time_end})
                |> filter(fn: (r) => r["_measurement"] == "{room.measurement}" 
                                    and r["_field"] == "roomID" 
                                    and r["_value"] == "{roomname}")
                |> window(every: 30m)
                |> last()
                |> window(every: inf)
                |> rename(columns: {{_time: "last_occupancy"}})
                """
        last_occupancy_time_df = query_api.query_data_frame(org=ORG, query=query)

        df["last_occupancy"] = last_occupancy_time_df["last_occupancy"]

        # make the boundaries explicit
        df = df.rename(columns={"_time":"end", "_value":"num_detections"})
        df["start"] = df["end"] - window
        return df[["start", "end", "num_detections", "last_occupancy"]]

if __name__ == "__main__":
    start = datetime(2026, 1, 14, tzinfo=timezone.utc)
    end = datetime(2026, 1, 15, tzinfo=timezone.utc)
    get_occupancy("fish", start, end, window=timedelta(minutes=30))
    