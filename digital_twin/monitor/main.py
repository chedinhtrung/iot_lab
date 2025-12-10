from sifec_base import LocalGateway, base_logger, PeriodicTrigger, OneShotTrigger
from utils import * 

app = LocalGateway(mock=False)

def detect_emergency():
    print(f"check emergency event received. Checking...")
    
    for roomname in ["door", "desk", "fish"]:
        model = get_latest_model(roomname)
        latest_stay = get_latest_stay(roomname)
        if len(latest_stay) == 0:
            continue
        emergency, confidence = is_emergency(latest_stay["duration"][0], model)
        if emergency: 
            event = EmergencyEvent(data={"confidence": confidence, "location": roomname})
            trg = OneShotTrigger(event, True)
            print("Emitting emergency event!")
    return

async def dummy():
    base_logger.info("I passed the assignment")

# Deploy a route within this server to be reachable from the SIF scheduler
# it appends the name of the cb to `/api/`. For more, please read the
# documentation for `deploy`
app.deploy(cb=dummy, name="dummy_monitor", evts="ClassTestEvent", path="dummy_monitor")

# subscribe to CheckEmergencyEvent, callback detect_emergency
app.deploy(cb=detect_emergency, name="DetectEmergency", evts="CheckEmergencyEvent", path="DetectEmergency")


# periodically emit TrainOccupancyModelEvent
trn_evt = TrainOccupancyModelEvent()
trg = PeriodicTrigger(trn_evt, True, "0 * * * *") # run every minute for demo

# periodically emit CheckEmergencyEvent
chk_evt = CheckEmergencyEvent()
trg2 = PeriodicTrigger(chk_evt, True, "0 * * * *") # run every minute for demo