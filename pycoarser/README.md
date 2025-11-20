
### Definitions
- A "stay" is a sequence of PIR events that satisfy the following conditions: 
    - No two consecutive events in the sequence are longer than `MAX_IDLE_TIME` minutes apart 
    - The sequence is longer than `MIN_STAY_DURATION` minutes from beginning to end.   

    A stay has a `begin` and an `end` timestamp that are defined by the first and last event in the sequence, respectively.
    Additionally the activity is *tagged* with the room it occurs in.

- An "activity" is a sequence of stays in the same room such that no consecutive stays are separated by more than `MAX_AWAY_TIME` minutes apart.
    
    An activity has a `begin` and `end` timestamp that are marked by the `begin` of the first stay and the `end`of the last stay. Additionally the activity is *tagged* with the room it occurs in.

### Aggregation rule to avoid collisions 

- The aggregator is a program that queries InfluxDB events, aggregate events continuously and asynchronously into a list of "stays" and "activities" as defined above, and add it to a "stay" bucket and an "activity" bucket on InfluxDB. 

- Each room has its own two threads that perform aggregate 

- The frequency that the aggregator wakes up and run is defined by `AGGR_FREQ`in minutes

- The aggregation is done by iterating through the events, checking the time difference between two consecutive events and spawning a new stay/activity when the `MAX_IDLE_TIME` or `MAX_AWAY_TIME` is exceeded.

- The aggregator begins aggregating starting from the time `GENESIS_TIME` on cold start (no activities/stays have been created). Otherwise it starts the aggregation from the `end` time of the last activity/stays in the bucket.

- To prevent touching activities/stays that is still happening and have not ended yet, the aggregator will intentionally discard the last stay that it detects. This is neccessary because events are not sent immediately due to the event table!

