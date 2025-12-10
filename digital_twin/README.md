# Digital twin details 

- `monitor`, `actuation`, `model` are three separate services running independently at different ports on the Pi.



### Monitor component
Emits `TrainOccupancyModelEvent`
- Is triggered once every day
- Does not need to contain any data

Emits `CheckEmergencyEvent` 
- is triggered once every 5 minutes
- contains a data field `mode` which can be `simple` or `complex`


Subscribes to `CheckEmergencyEvent` with callback `DetectEmergency`
- if `mode=simple`: polls minio to get mean and variance of time of stay. Compares the latest stay to this. Calculates probability of such a stay occuring. If it is too unlikely (anomaly), emit `EmergencyEvent`.

Emits `EmergencyEvent` 
- When?
- Which room?
- Confidence = 1 - probability of event

### Modelling component
- Subscribes to `TrainOccupancyModelEvent` with callback `CreateOccupancyModel()`
- For now the simple averaging model is used: 
    - Calculates the mean time of stay and variance in each room of
    - Save these two numbers as json into Minio

### Actuation component
- Subscribes to `EmergencyEvent` 
