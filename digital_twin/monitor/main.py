from sifec_base import LocalGateway, base_logger, PeriodicTrigger, OneShotTrigger
from utils import * 
from modelling.model import *
from fastapi import BackgroundTasks

app = LocalGateway(mock=False)

duration_model = load_model(f"latest/{StayDurationModel.__name__}.pkl")

if duration_model is None: 
    print("Warning: Can't find pretrained. Initializing new Duration model")
    duration_model = StayDurationModel(timedelta(minutes=15))
    duration_model.train()
    save_model(duration_model)

def train_then_save(model):
    model.train()
    save_model(model)

def detect_emergency(data:dict|None):
    print(f"check emergency event received. Checking...")
    active_room, expected_stay_duration, actual_stay_duration = duration_model.predict()
    
    ### Kitchen emergency
    if active_room == "kitchen" and actual_stay_duration/expected_stay_duration > 3:
        event = EmergencyEvent(data={"type": "stay",
                                     "timestamp":datetime.now(tz=timezone.utc).isoformat(),
                                     "location": active_room, 
                                     "stay_duration":actual_stay_duration.total_seconds()/60, 
                                     "priority": 0})
        trg = OneShotTrigger(event, True)
        print("Emitting emergency event Kitchen")
        todo = Todo("Kitchen RESCUE", priority=0)
        todo.push_to_influx()
    
    ### Reminder to stand up
    if active_room == "desk" and actual_stay_duration > timedelta(hours=2):
        event = EmergencyEvent(data={"type": "stay",
                                     "timestamp":datetime.now(tz=timezone.utc).isoformat(),
                                     "location": active_room, 
                                     "stay_duration":actual_stay_duration.total_seconds()/60, 
                                     "priority": 1})
        
        trg = OneShotTrigger(event, True)
        print("Emitting emergency event Desk!")
        todo = Todo("Desk stay too long, stand up!", priority=10)
        todo.push_to_influx()

def detect_high_co2(data:dict|None):
    """
        simple query the co2
    """
    print("Checking CO2 level...")
    
    todo = Todo("High CO2! Open windows!", priority=6)
    todo.push_to_influx()
    
def train_duration_model(background_tasks:BackgroundTasks):
    print(f"Training duration model...")
    background_tasks.add_task(train_then_save, duration_model)


def generate_prediction(data:dict|None):
    pass


functs = [detect_emergency, train_duration_model, detect_high_co2]

for function in functs:
    app.deploy(cb=function, name=function.__name__, evts=function.__name__, method="POST")

# periodic triggers for detection
# every 15 min 
detect_emergency_trigger = PeriodicTrigger(PeriodicFunctionEvent(detect_emergency), 
                                           cronSpec="*/15 * * * *")

detect_co2_trigger = PeriodicTrigger(PeriodicFunctionEvent(detect_high_co2), 
                                           cronSpec="*/15 * * * *")

# every week on monday
train_model_trigger = PeriodicTrigger(PeriodicFunctionEvent(train_duration_model), 
                                           cronSpec="0 0 * * 1")
