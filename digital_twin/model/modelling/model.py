import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from modelling.data.preprocessing import get_bucketized_occupancy
from modelling.data.preprocessing import *
import os
import pickle

from sklearn.linear_model import LogisticRegression
from minio import Minio
import io
from minio.error import S3Error

MINIO = Minio(
    "192.168.0.103:9090",
    access_key="bSYIFuEHZa3JHTKg6WE9",
    secret_key="u8TnjmYYEcUJNugWSOUZwXEDqu2FU2JToOIAx2Lt",
    secure=False,
)

def sigmoid(x):
    return 1/(1+np.exp(-x))

class BayesianBetaModel:
    """
        Outputs p(occupied) for each time bucket of the day. 
        model params: alpha, beta. One per time bucket per day of the week per room

        dimension: (buckets_per_day, 7, num_rooms)
    """

    def __init__(self, bucket_size:timedelta, rooms:list=["kitchen", "desk", "fish"], history:timedelta=timedelta(days=60)):
        """
            history: how many days in the past to consider. To keep it representative of the behavior, the model train on a rolling 
            window of data from the past e.g 90 days
        """
        buckets_per_day = int(timedelta(days=1)/bucket_size)
        self.bucket_size = bucket_size
        self.num_buckets = buckets_per_day
        self.num_rooms = len(rooms)
        self.alpha = np.zeros((buckets_per_day, 7, self.num_rooms))
        self.beta = np.zeros((buckets_per_day, 7, self.num_rooms))
        self.roomnames = rooms
        self.history = history

        # metadata on the training period
        self.train_period_start = None
        self.train_period_end = None

    def _predict(self,  bucket_idx: np.ndarray,  weekday: np.ndarray, room: np.ndarray) -> np.ndarray:
        """
        returns the best estimate of p = p(occupied) of the room, i.e the mean of the beta distribution
        """
        return self.mean[bucket_idx, weekday, room]
    
    def predict(self, timestamp:datetime, room:str):
        """
        returns the probability of the room being occupied, given time (coarsened to time bucket size)
        """
        room_idx = self.roomnames.index(room)
        day_start = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        bucket_idx = int((timestamp - day_start) / self.bucket_size)
        weekday = timestamp.weekday()
        return self._predict(bucket_idx, weekday, room_idx)

    
    def _update(
        self,
        bucket_idx: np.ndarray,   # shape (N,)
        weekday: np.ndarray,      # shape (N,)
        room: np.ndarray,         # shape (N,)
        observation: np.ndarray,     # shape (N,) in {0,1}
    ):
        """
         generic update where observation is an array of N observations, 
         where each observation has to specifiy: which bucket of the day, 
         what day of the week, and what was the observation (occupied or not)
        """
        #assert bucket_idx.shape[0] == weekday.shape[0] == room.shape[0] == observation.shape[0]
        occ = observation.astype(np.int64)
        np.add.at(self.alpha, (bucket_idx, weekday, room), occ)
        np.add.at(self.beta, (bucket_idx, weekday, room), (1 - occ))

    def update(self, 
                   observation: pd.DataFrame, 
                   roomname:str, 
                   halflife = 6
                   ): 
        """
        observation: a dataframe of raw bucketized observations of a single room.
        columns: start, end, num_detections
        halflife:  In weeks. after halflife weeks, the contribution is halved
        """
        
        #assert len(observation) == self.alpha.shape[0]

        occupancy = observation["num_detections"].to_numpy(dtype=int).clip(0, 1)
        
        # compute the bucket index 
        day_start = observation["start"].dt.floor("D")
        delta = observation["start"] - day_start
        bucket_idx = (delta.dt.total_seconds()//(self.bucket_size.total_seconds())).astype(int).to_numpy()

        room = self.roomnames.index(roomname)
        room = (np.ones(occupancy.shape) * room).astype(int)
        weekday = observation["start"].dt.weekday.to_numpy()

        # compute time since last observation for decay
        # before updating with observations 
        self.alpha *= np.pow(0.5, 1/halflife)
        weeks_since_first_observation = (observation["start"][len(observation)-1] - observation["start"])//timedelta(days=7)
        decay = np.pow(0.5, (weeks_since_first_observation/halflife))
        occupancy *= decay

        self._update(bucket_idx, weekday, room, occupancy)

    def train(self):
        """
            get the data starting from the last time the model was trained, train on that data and save the results to a file
        """
        for room in self.roomnames:
            end = datetime.now(tz=timezone.utc)
            start = end - self.history
            observation = get_bucketized_occupancy(room, start, end, window=self.bucket_size)
            self.update(observation=observation, roomname=room)
        
        self.train_period_end = datetime.now(tz=timezone.utc)
        self.train_period_start = end - self.history

    def _load_prior(self, excelfile, k=np.array([4, 7, 3]), b=np.array([0.6, 1, 0.3]), a=np.array([-1, 0, -1.5])):
        """
        excel file: contains sheets that are named the same as the room name. Must assign each bucket a score 0 to 10
        k: strength of belief for the prior. Essentially "my prior belief is obtained from k supporting (imaginary) experiments"
        a, b: adjusted score = a + b*score for each room, to reflect relative score confidence and overall probability of visiting
        """
        base_path = os.path.dirname(__file__)
        excelfile = base_path + "/" + excelfile
        assert len(k) == self.num_rooms
        prior_scores = np.ndarray(self.alpha.shape)
        for roomindex, room in enumerate(self.roomnames):
            df = pd.read_excel(excelfile, sheet_name=room)
            prior_scores[:, :, roomindex] = df.iloc[:,1:].to_numpy()
        
        # hardcoded score confidence and score weighting for now 
        
        # turn score into probabilities

        prior_logits = a[None, None, :] + b[None, None, :] * (prior_scores - 5)   

        prior_probs = sigmoid(prior_logits)

        # update alpha and beta
        self.alpha = prior_probs * k[None, None, :]
        self.beta  = (1 - prior_probs) * k
    
    def load_prior_from_minio(self):
        pass

    @property
    def mean(self) -> np.ndarray:
        eps = 1e-6
        return self.alpha / (self.alpha + self.beta + eps)


class PredictiveLogRegModel: 
    """
        learns the mapping 
        (time, weekday, current room, <room_x>_t_since_last_visit, <room_x>_stay_duration) -> p(occupied) for each room

    """
    def __init__(self, window:timedelta, rooms:list=["kitchen", "desk", "fish"], 
                 horizon:timedelta=timedelta(hours=1), history:timedelta=timedelta(days=60)):
        """
            window: the size of the bucket to discretize the day
            rooms: the room names 
            horizon: how far into the future to predict
            history: how far back to pull training data
        """
        self.horizon = horizon
        self.rooms = rooms
        self.window = window
        self.history = history

        self.model = LogisticRegression(
            multi_class="multinomial",
            solver="lbfgs",
            max_iter=500,
            class_weight="balanced"
        )
    
    def _train(self, data:pd.DataFrame):
        """
        process the data into refined feature vectors
        and then train on the data.
        """
        feature, label = preprocess_to_features_labels(data, self.rooms, horizon=self.horizon)
        self.model.fit(feature, label)
        return 
    
    def _predict(self, data:pd.DataFrame):
        features = preprocess_to_features(data, self.rooms)
        features_last = features.tail(1)
        return self.model.predict_proba(features_last)
    
    def predict(self):
        """
            get the latest observations and predict occupancy in self.horizon
        """
        end = datetime.now(tz=timezone.utc)
        start = end - timedelta(days=1)    # always base on the observation for the last day for buffering
        data, rooms = get_combined_bucketized_occupancy(start=start, end=end, window=self.window, rooms=self.rooms)
        return self._predict(data), rooms
 
    def train(self):
        """
            query data from last self.history, train, then save the model
        """
        end = datetime.now(tz=timezone.utc)
        start = end - self.history
        data, _ = get_combined_bucketized_occupancy(start=start, end=end, window=self.window, rooms=self.rooms)
        self._train(data)

class PredictiveModelEnsemble:
    def __init__(self, window:timedelta, 
                 horizons:list, rooms:list=["kitchen", "desk", "fish"], history:timedelta=timedelta(days=60)):
        self.models = []
        self.horizons = horizons
        self.window = window
        self.history = history
        self.rooms = rooms
        for horizon in self.horizons: 
            self.models.append(PredictiveLogRegModel(window=self.window,
                                                     horizon=horizon,
                                                     history=history,
                                                     rooms=self.rooms))
    
    def train(self):
        for model in self.models:
            model.train()
    
    def predict(self):
        predictions = []
        horizons = []
        for model in self.models: 
            horizons.append(model.horizon)
            predictions.append(model.predict())
        
        return horizons, predictions
        

def load_model(pickle_file):
    """
        loads a model stored on MinIO in the bucket "models" as pickle file
    """
    try:
        response = MINIO.get_object("models", pickle_file)
    except S3Error as e:
        if e.code == "NoSuchKey":
            return None   # signal: train from scratch
        else:
            raise e

    try:
        data = response.read()
        print(f"loaded pretrained model from {pickle_file}")
        return pickle.loads(data)
    finally:
        response.close()
        response.release_conn()

def save_model(model, name=None):
    """
        save model to minio
    """
    if name is None:
        name = model.__class__.__name__
    buf = io.BytesIO()
    pickle.dump(model, buf)
    buf.seek(0)
    MINIO.put_object(
        bucket_name="models",
        object_name=f"latest/{name}.pkl",
        data=buf,
        length=buf.getbuffer().nbytes,
    )
    timestamp = datetime.now().date().strftime("%Y%m%d")
    buf.seek(0)
    MINIO.put_object(
        bucket_name="models",
        object_name=f"history/{name}_{timestamp}.pkl",
        data=buf,
        length=buf.getbuffer().nbytes,
    )

if __name__ == "__main__":
    model = BayesianBetaModel(bucket_size=timedelta(minutes=30))
    start = datetime(2025, 11, 15, 10, tzinfo=timezone.utc)
    end = datetime(2026, 1, 15, tzinfo=timezone.utc)
    #observation = get_bucketized_occupancy("fish", start, end, window=timedelta(minutes=30))
    #model._load_prior("data/Priors.xlsx")
    #model.predict(datetime(2026, 1, 14, 10,4,30, tzinfo=timezone.utc), "fish")
    #model.train()

    #data, rooms = get_combined_bucketized_occupancy(start=start, end=end, window=timedelta(minutes=30))
    #logistic_model = PredictiveLogRegModel(window=timedelta(minutes=30), rooms=["kitchen", "desk", "fish"], horizon=timedelta(minutes=30))
    #logistic_model.train()
    #logistic_model.predict()
    ensemble = PredictiveModelEnsemble(window=timedelta(minutes=15), horizons=(timedelta(minutes=15), timedelta(minutes=30), timedelta(minutes=60), timedelta(minutes=120)))
    ensemble.train()
    horizons, predictions = ensemble.predict()
    print(horizons)
    print(predictions)