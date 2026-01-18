from sifec_base import LocalGateway, base_logger, PeriodicTrigger, OneShotTrigger
from utils import * 

app = LocalGateway(mock=False)

def detect_emergency():
    print(f"check emergency event received. Checking...")
    emergency, confidence = True, True
    if emergency: 
        event = EmergencyEvent(data={"confidence": confidence})
        trg = OneShotTrigger(event, True)
        print("Emitting emergency event!")
    return


# subscribe to CheckEmergencyEvent, callback detect_emergency
app.deploy(cb=detect_emergency, name=detect_emergency.__name__, evts=detect_emergency.__name__, method="POST")