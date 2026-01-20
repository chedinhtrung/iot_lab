
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from data.preprocessing import * 

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

def get_occupancy_data(start:str, end:str, resolution=30):
    """
        start, end: start and end of the query period. Must be ISO timestamp string
        resolution: how much to coarsen, in minutes. Defaults to 30
    """
    print(f"Bot requested to get data from {start} to {end}")
    start = datetime.fromisoformat(start)
    end = datetime.fromisoformat(end)

    try:
        raw_df, rooms = get_combined_bucketized_occupancy(start, end, window=timedelta(minutes=resolution))
        
        better_df = make_df_json_safe(raw_df)
        
        return {
        "data":better_df.to_dict(orient="list"),
        "context": f"""
        You have queried the database for a complete record of occupancy state from {start} to {end}. 
        You got a result that contains timestamps in buckets of regular time intervals. Each bucket captures the state 
        of occupancy of rooms during that time interval.
        Especially useful are the columns: occupancy_time - gives "time spent up to that timestamp of the at the time occupied room"
        <roomname>_occupied - whether the room is occupied at that time
        <roomname>_t_since_last_visit: time since I have visited that room for the last time, 0 if i am there.
        The room Void is active only when no actual rooms are active
        """
        }
    except Exception as e: 
        return {
            "result": "Function Call Failed", 
            "reason": str(e)
        }

TOOL_NAMES_MAPPING = {}
TOOL_FUNCTS = [get_occupancy_data]

for funct in TOOL_FUNCTS:
    TOOL_NAMES_MAPPING[funct.__name__] = funct


if __name__ == "__main__":
    get_occupancy_data(start="2026-01-19T00:00:00", end="2026-01-20T00:00:00")