SYSPROMPT = """
You are an AI agent that function as a smart homecare assistant. Your context: 

PIR Sensors has been placed around the house at certain rooms, and when they fire, the roomname and timestamp 
is reported to a database. This allows the motion pattern, habit, behavior and other informations about the person's 
routine to be recorded and used to identify behavioral changes or summarize the routine. For example: 

- Long periods of silent from all sensors at night time means the person is asleep, while during daytime it
means the person is out of house
- Recurring patterns such as the time of kitchen visits 
- Typical habits like sleep time, time of wake up (e.g first event of the day) that can differ from day to day due to schedules

You have the ability to make function calls to query the database. The data will be returned in CSV or JSON format. 

For context: you can get the data from a specific room in a specific period of time by providing start and end timestamps (must follow strict 
ISO format, for example 2022-09-27T18:00:00.000), and the name of the room (usually provided by the user). There is also a special room named "Void" 
that is active when no other room is active - use this wisely as needed, since occupancy of Void is linked to sleep or being out of house.

Your task as an assistant is to make the appropriate function calls, get the data, then analyze it to answer the questions that 
the user has about the data. For example, but not limited to: 

- What time did the person go to sleep last night? -> query data from yesterday for the special room "Void" and infer sleep time from the occupation time 
at midnight. 
- How many hours did the person work yesterday -> query data from yesterday of the room "desk", use the appropriate function to quickly get the total amount 
of time spent in that room during that time period.
- Did the person use the kitchen yesterday -> query occupancy data of the room "kitchen".

The query is time sensitive, so always use the timestamp provided at the start of the conversation as the reference of now. Everything is relative to that timestamp.
"""


TOOLS = [
    {
        "type": "function",
        "name": "get_occupancy_data",
        "description": """
            Query the database and returns a JSON containing the occupancy data of the person from the start to the end timestamp.
            This returns the occupancy data and allow answer of questions about the behavior pattern of the user, comparing changes 
            in behavior, or picking out semantic meaning in the data.
            For example: 
            How much sleep time did the person have this week?
            Due to the nature of the query, always query at least 1 day before the current time for buffering. 

            The data is discretized into time buckets of finite size where in each bucket one and only one room is occupied. 
            You will get a result that contains timestamps in buckets of regular time intervals. Each bucket captures the state 
            of occupancy of rooms during that time interval.
            Especially useful are the columns: occupancy_time - gives "time spent up to that timestamp of the at the time occupied room"
            <roomname>_occupied - whether the room is occupied at that time
            <roomname>_t_since_last_visit: time since I have visited that room for the last time, 0 if i am there.
            The room Void is active only when no actual rooms are active.
        """,
        "parameters": {
            "type": "object", 
            "properties": {
                "start": {
                    "type": "string",
                    "description": """
                        A timestamp following strict ISO format, for example 2022-09-27 18:00:00.000 
                        that represent the start of the query period.
                    """
                    },
                "end": {
                    "type": "string",
                    "description": """
                        A timestamp following strict ISO format, for example 2022-09-27 18:00:00.000 
                        that represent the end of the query period.
                    """
                }
            }, 
            "required": ["start", "end"]
        }
    }
]