
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from data.preprocessing import * 
from io import BytesIO
from minio import Minio
from config import *
import streamlit as st

MINIO = Minio(
        secure=False,
        endpoint=MINIO_URL,
        access_key=MINIO_ACCESSKEY,
        secret_key=MINIO_SECRETKEY
)

## This defines a bunch of functions for the bot to use 
## Mostly to query the data and return in a bot-friendly format

def make_df_json_safe(df:pd.DataFrame):
    df = df.copy()

    # Datetime → ISO string
    for col in df.select_dtypes(include=["datetime64[ns]", "datetime64[ns, UTC]"]).columns:
        df[col] = df[col].dt.strftime("%Y-%m-%d %H:%M:%S")

    # Timedelta → human-readable string
    for col in df.select_dtypes(include=["timedelta64[ns]"]).columns:
        df[col] = df[col].astype(str)

    return df

def get_occupancy_data(room: str, start:str, end:str, resolution=30):
    """
        start, end: start and end of the query period. Must be ISO timestamp string
        resolution: how much to coarsen, in minutes. Defaults to 30
    """
    print(f"Bot requested to get data from room {room}, from {start} to {end} with {resolution}")
    start = datetime.fromisoformat(start)
    end = datetime.fromisoformat(end)

    if end - start > timedelta(days=10):
        return {
                "result": "Function Call Failed",
                "reason": "Exceeded max time from start to end."
            }

    try:
        resolution = 60/(int(60/resolution)) if resolution <= 60 else int(resolution/60)
        raw_df, rooms = get_individualized_occupancy(room, start, end, window=timedelta(minutes=resolution))
        if raw_df is None: 
            print("Could not find the wanted room")
            return {
                "result": "Function Call Failed",
                "reason": f"No such room {room} in the database. Maybe the user typed the wrong room."
            }
        if len(raw_df) > 1500: 
            return {
                "result": "Function Call Failed",
                "reason": "Too much data. Please try a coarser resolution."
            }
        better_df = make_df_json_safe(raw_df)
        
        return {
        "data":better_df.to_dict(orient="list"),
        "context": f"""
        You have queried the database for a complete record of occupancy state from {start} to {end}. 
        You got a result that contains timestamps in buckets of regular time intervals. Each bucket captures the state 
        of occupancy of rooms during that time interval.
        """
        }
    except Exception as e: 
        return {
            "result": "Function Call Failed", 
            "reason": str(e)
        }

def get_coarsened_occupancy_data(room:str, start:str, end:str, resolution=10):
    print(f"Bot requested to get coarsened data from room {room}, from {start} to {end} with {resolution}")
    resolution = 60/(int(60/resolution)) if resolution <= 60 else int(resolution/60)
    
    try:
        start = datetime.fromisoformat(start)
        end = datetime.fromisoformat(end)
        df = get_coarsened_occupancy(room, start, end, timedelta(minutes=resolution))

        if df is None: 
            print("Could not find the wanted room")
            return {
                "result": "Function Call Failed",
                "reason": f"No such room {room} in the database. Maybe the user typed the wrong room."
            }
        df = make_df_json_safe(df)

        return {
            "data":df.to_dict(orient="list"),
            "context": f"""
            You have queried the database for a compact coarsened representation of occupancy state from {start} to {end} of room {room}
            The result contains a list of big intervals of time when the room was occupied when it started being occupied, 
            when it stopped being occupied, and the total amount of time passed in each block. All time intervals outside the blocks returned represent periods of time when the room is not occupied.
            """
        }

    except Exception as e: 
        return {
            "result": "Function Call Failed", 
            "reason": str(e)
        }

def save_response(content:str):
    """
        save bot report to minio
    """
    print("Saving report...")
    buf = BytesIO(content.encode("utf-8"))
    buf.seek(0)
    MINIO.put_object(
        bucket_name="models",
        object_name=f"summaries/latest/report.md",
        data=buf,
        length=buf.getbuffer().nbytes,
    )
    timestamp = datetime.now().date().strftime("%Y%m%d %H:%M:%S")
    buf.seek(0)
    MINIO.put_object(
        bucket_name="models",
        object_name=f"summaries/history/report_{timestamp}.pkl",
        data=buf,
        length=buf.getbuffer().nbytes,
    )

def load_response():
    response = MINIO.get_object("models", "summaries/latest/report.md")
    text = response.read().decode("utf-8")
    response.close()
    response.release_conn()
    return text

TOOL_NAMES_MAPPING = {}
TOOL_FUNCTS = [get_occupancy_data, get_coarsened_occupancy_data, save_response]

for funct in TOOL_FUNCTS:
    TOOL_NAMES_MAPPING[funct.__name__] = funct


if __name__ == "__main__":
    get_coarsened_occupancy_data(start="2025-12-24T17:59:14.117682", end="2026-01-21T17:59:14.117682", resolution=10, room="desk")