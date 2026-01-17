from sifec_base import LocalGateway, base_logger, PeriodicTrigger, ExampleEventFabric 
from pydantic import BaseModel

app = LocalGateway(mock=False)

def train_bayesian_model(data:dict):
    print(f"Training Bayesian model with {data}")
    

cb = train_bayesian_model

app.deploy(cb=train_bayesian_model, evts=cb.__name__, name=cb.__name__, method="POST")