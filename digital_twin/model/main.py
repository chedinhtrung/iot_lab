from sifec_base import LocalGateway, base_logger, PeriodicTrigger, BaseEventFabric 
from pydantic import BaseModel
from modelling.model import * 
from fastapi import BackgroundTasks

# the models 
bayesian_model = load_model(f"latest/{BayesianBetaModel.__name__}.pkl")
if bayesian_model is None:
    print("Warning: Can't find pretrained. Initializing new Bayesian model")
    bayesian_model = BayesianBetaModel(timedelta(minutes=30))
    bayesian_model.load_prior_from_minio()
    bayesian_model.train()
    save_model(bayesian_model)

predictive_model = load_model(f"latest/{PredictiveModelEnsemble.__name__}.pkl")
if predictive_model is None:
    print("Warning: Can't find pretrained. Initializing new Bayesian model")
    predictive_model = PredictiveModelEnsemble(window=timedelta(minutes=15),
                                           horizons=[timedelta(minutes=30), timedelta(minutes=60), timedelta(minutes=120), timedelta(minutes=180)])
    predictive_model.train()
    save_model(predictive_model)

# Functions and registering them with the scheduler
# The scheduler's endpoint has to be set with SCH_SERVICE_NAME env var

app = LocalGateway(mock=False)

def train_then_save(model):
    model.train()
    save_model(model)

def train_bayesian_model(background_tasks:BackgroundTasks):
    print(f"Training Bayesian model")
    background_tasks.add_task(train_then_save, bayesian_model)
    return {"success": True}

def train_predictive_model(background_tasks:BackgroundTasks):
    print(f"Training predictive model")
    background_tasks.add_task(train_then_save, predictive_model)
    return {"success": True}

def create_prediction_report(data:dict|None):
    """
        use predictive + bayesian to generate predictions
        returns predictions
    """
    horizons, predictions = predictive_model.predict()
    week_summary = bayesian_model.get_summary()
    return


training_fct = [train_bayesian_model, train_predictive_model]

for cb in training_fct:
    app.deploy(cb=cb, evts=cb.__name__, name=cb.__name__, method="POST")


### training events 

class PeriodicEvent(BaseEventFabric):
    def __init__(self, func):
        super().__init__()
        self.func = func
    
    def call(self):
        return self.func.__name__, None

# triggers 

train_bayesian_trigger = PeriodicTrigger(PeriodicEvent(train_bayesian_model),
                                         cronSpec="0 0 * * 1")

train_predictive_trigger = PeriodicTrigger(PeriodicEvent(train_predictive_model),
                                         cronSpec="0 0 * * 1")