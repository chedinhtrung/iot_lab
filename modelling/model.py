
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from data.preprocessing import get_bucketized_occupancy
from data.preprocessing import *

from sklearn.linear_model import LogisticRegression

def sigmoid(x):
    return 1/(1+np.exp(-x))

class BayesianBetaModel:
    """
        Outputs p(occupied) for each time bucket of the day. 
        model params: alpha, beta. One per time bucket per day of the week per room

        dimension: (buckets_per_day, 7, num_rooms)
    """

    def __init__(self, bucket_size:timedelta, rooms:list=["kitchen", "desk", "fish"]):
        buckets_per_day = int(timedelta(days=1)/bucket_size)
        self.bucket_size = bucket_size
        self.num_rooms = len(rooms)
        self.alpha = np.zeros((buckets_per_day, 7, self.num_rooms))
        self.beta = np.zeros((buckets_per_day, 7, self.num_rooms))
        self.roomnames = rooms

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
        observation: np.ndarray      # shape (N,) in {0,1}
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
                   roomname:str
                   ): 
        """
        observation: a dataframe of raw bucketized observations of a single room.
        columns: start, end, num_detections
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

        self._update(bucket_idx, weekday, room, occupancy)

    def train(self, loader):
        """
        loader: a data loader that outputs a batch of recent observations
        """
        pass
        


    def load_prior(self, excelfile, k=np.array([4, 7, 3]), b=np.array([0.6, 1, 0.3]), a=np.array([-1, 0, -1.5])):
        """
        excel file: contains sheets that are named the same as the room name. Must assign each bucket a score 0 to 10
        k: strength of belief for the prior. Essentially "my prior belief is obtained from k supporting (imaginary) experiments"
        a, b: adjusted score = a + b*score for each room, to reflect relative score confidence and overall probability of visiting
        """

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

    @property
    def mean(self) -> np.ndarray:
        eps = 1e-6
        return self.alpha / (self.alpha + self.beta + eps)
    
    def export(self):
        """
        export the model's parameters into some form.
        """
        pass



class LogisticRegressionModel: 
    """
        learns the mapping 
        (time, weekday, current room, <room_x>_t_since_last_visit, <room_x>_stay_duration) -> 

    """
    def __init__(self, window:timedelta, rooms:list, horizon:timedelta):
        self.horizon = horizon
        self.rooms = rooms
        self.window = window

        self.model = LogisticRegression(
            multi_class="multinomial",
            solver="lbfgs",
            max_iter=500,
            class_weight="balanced"
        )
    
    def train(self, data:pd.DataFrame):
        """
        process the data into refined feature vectors
        and then train on the data.
        """
        feature, label = preprocess_to_features_labels(data, self.rooms, horizon=self.horizon)
        self.model.fit(feature, label)
        return 
    
    def predict(self, data:pd.DataFrame):
        features = preprocess_to_features(data, self.rooms)
        return self.model.predict_proba(features)

if __name__ == "__main__":
    model = BayesianBetaModel(bucket_size=timedelta(minutes=30))
    start = datetime(2026, 1, 14, 10, tzinfo=timezone.utc)
    end = datetime(2026, 1, 15, tzinfo=timezone.utc)
    observation = get_bucketized_occupancy("fish", start, end, window=timedelta(minutes=30))
    model.load_prior("./modelling/data/Priors.xlsx")
    model.predict(datetime(2026, 1, 14, 10,4,30, tzinfo=timezone.utc), "fish")
    model.update(observation=observation, roomname="fish")

    data, rooms = get_combined_bucketized_occupancy(start=start, end=end, window=timedelta(minutes=30))
    logistic_model = LogisticRegressionModel(timedelta(minutes=30), rooms=["kitchen", "fish", "desk", "Void"], horizon=timedelta(minutes=30))
    logistic_model.train(data)
    logistic_model.predict(data.iloc[[0]])