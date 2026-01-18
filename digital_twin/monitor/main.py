from sifec_base import LocalGateway, base_logger, PeriodicTrigger, OneShotTrigger
from utils import * 
from modelling.model import *

app = LocalGateway(mock=False)

duration_model = load_model(f"latest/{StayDurationModel.__name__}.pkl")
if duration_model is None: 
    print("Warning: Can't find pretrained. Initializing new Bayesian model")
    duration_model = StayDurationModel(timedelta(minutes=15))
    duration_model.train()
    save_model(duration_model)

def detect_emergency(data:dict|None):
    print(f"check emergency event received. Checking...")
    active_room, expected_stay_duration, actual_stay_duration = duration_model.predict()
    
    if active_room == "kitchen" and actual_stay_duration/expected_stay_duration > 3:
        event = EmergencyEvent(data={"location": "kitchen", "stay_duration":actual_stay_duration.total_seconds()/60})
        trg = OneShotTrigger(event, True)
        print("Emitting emergency event!")
        return
    
def train_duration_model(data:dict|None):
    print(f"Training duration model...")
    duration_model.train()
    save_model(duration_model)

# subscribe to CheckEmergencyEvent, callback detect_emergency
app.deploy(cb=detect_emergency, name=detect_emergency.__name__, evts=detect_emergency.__name__, method="POST")