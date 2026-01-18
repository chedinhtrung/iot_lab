from sifec_base import LocalGateway, base_logger, PeriodicTrigger, OneShotTrigger
from utils import * 

app = LocalGateway(mock=False)

def detect_emergency():
    print(f"check emergency event received. Checking...")
    emergency, confidence = check_emergency()
    if emergency: 
        event = EmergencyEvent(data={"confidence": confidence, "location": roomname})
        trg = OneShotTrigger(event, True)
        print("Emitting emergency event!")
    return


# subscribe to CheckEmergencyEvent, callback detect_emergency
app.deploy(cb=detect_emergency, name="DetectEmergency", evts="CheckEmergencyEvent", path="DetectEmergency")


# periodically emit TrainOccupancyModelEvent
trn_evt = TrainOccupancyModelEvent()
trg = PeriodicTrigger(trn_evt, True, "0 * * * *") # run every minute for demo

# periodically emit CheckEmergencyEvent
chk_evt = CheckEmergencyEvent()
trg2 = PeriodicTrigger(chk_evt, True, "0 * * * *") # run every minute for demo