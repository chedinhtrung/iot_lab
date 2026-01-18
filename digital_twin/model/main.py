from sifec_base import LocalGateway, base_logger, PeriodicTrigger, BaseEventFabric 
from pydantic import BaseModel
from modelling.model import * 

# the models 
bayesian_model = load_model(f"latest/{BayesianBetaModel.__name__}.pkl")
if bayesian_model is None:
    print("Warning: Can't find pretrained. Initializing new Bayesian model")
    bayesian_model = BayesianBetaModel(timedelta(minutes=30))
    bayesian_model.load_prior_from_minio()
    bayesian_model.train()
    save_model(bayesian_model)

logistic_model = load_model(f"latest/{PredictiveLogRegModel.__name__}.pkl")
if logistic_model is None: 
    print("Warning: Can't find pretrained. Initializing new Logistic Regression model")
    logistic_model = PredictiveLogRegModel(window=timedelta(minutes=15))
    save_model(logistic_model)

# Functions and registering them with the scheduler
# The scheduler's endpoint has to be set with SCH_SERVICE_NAME env var

app = LocalGateway(mock=False)

def train_bayesian_model(data:dict|None):
    print(f"Training Bayesian model with {data}")
    bayesian_model.train()
    save_model(bayesian_model)
    return {"success": True}

def train_logistic_regression(data:dict|None):
    print(f"Training logistic regression with {data}")
    logistic_model.train()
    save_model(logistic_model)
    return {"success": True}

def create_prediction_report():
    pass

training_fct = [train_bayesian_model, train_logistic_regression]

for cb in training_fct:
    app.deploy(cb=cb, evts=cb.__name__, name=cb.__name__, method="POST")


### training events 

class TrainLogisticRegressionEvent(BaseEventFabric):
    def __init__(self):
        super().__init__()
    
    def call(self, *args, **kwargs):
        return train_logistic_regression.__name__, None
    
class TrainLogisticRegressionEvent(BaseEventFabric):
    def __init__(self):
        super().__init__()
    
    def call(self, *args, **kwargs):
        return train_bayesian_model.__name__, None
    
# triggers 
    
