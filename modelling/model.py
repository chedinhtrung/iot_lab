
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from data.preprocessing import get_occupancy


class BayesianBetaModel:
    """
        Outputs p(occupied) for each time bucket of the day. 
        model params: alpha, beta. One per time bucket per day of the week per room

        dimension: (buckets_per_day, 7, num_rooms)
    """

    def __init__(self, bucket_size:timedelta, num_rooms:int):
        buckets_per_day = int(timedelta(days=1)/bucket_size)

        self.alpha = np.zeros((buckets_per_day, 7, num_rooms))
        self.beta = np.zeros((buckets_per_day, 7, num_rooms))
        self.roomnames = ["kitchen", "desk", "fish"]

    def _predict(self,  bucket_idx: np.ndarray,  weekday: np.ndarray, room: np.ndarray) -> np.ndarray:
        """
        returns the best estimate of p = p(occupied) of the room, i.e the mean of the beta distribution
        """
        return self.mean[bucket_idx, weekday, room]
    
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
        self.alpha[bucket_idx, weekday, room] += occ
        self.beta[bucket_idx, weekday, room] += (1 - occ)

    def update(self, 
                   observation: pd.DataFrame, 
                   roomname:str
                   ): 
        """
        observation: a dataframe of raw bucketized observations of a single room. Can extend many days but has to be whole days
        starting at midnight, no half days
        columns: start, end, num_detections
        """
        
        #assert len(observation) == self.alpha.shape[0]

        occupancy = observation["num_detections"].to_numpy(dtype=int).clip(0, 1)
        bucket_idx = np.array(range(len(observation)))
        room = self.roomnames.index(roomname)
        room = (np.ones(occupancy.shape) * room).astype(int)
        weekday = observation["start"].dt.weekday.to_numpy()

        self._update(bucket_idx, weekday, room, occupancy)

    def train(self, loader):
        """
        loader: a data loader that outputs a batch of recent observations
        """
        pass
        


    def load_prior(self, excelfile, k=np.array([10, 20, 8]), confidence=np.array([0.6, 1, 0.3]), scoreshift=np.array([2, 20, 1])):
        """
        excel file: contains sheets that are named the same as the room name. Must assign each bucket a score 0 to 10
        k: strength of belief for the prior
        """
        prior_scores = np.ndarray(self.alpha.shape)
        for roomindex, room in enumerate(self.roomnames):
            df = pd.read_excel(excelfile, sheet_name=room)
            prior_scores[:, :, roomindex] = df.iloc[:,1:].to_numpy()
        
        # hardcoded score confidence and score weighting for now 
        
        # turn score into probabilities
        prior_scores -= 5    # subtract the middle ground)
        prior_logits = scoreshift[None, None, :] + confidence[None, None, :] * (prior_scores - 5)
        prior_probs = sigmoid(prior_logits)

        # update alpha and beta
        self.alpha = prior_probs * k[None, None, :]
        self.beta  = (1 - prior_probs) * k

    @property
    def mean(self) -> np.ndarray:
        return self.alpha / (self.alpha + self.beta + self.eps)


def sigmoid(x):
    return 1/(1+np.exp(-x))


if __name__ == "__main__":
    model = BayesianBetaModel(bucket_size=timedelta(minutes=30), num_rooms=3)
    start = datetime(2026, 1, 14, tzinfo=timezone.utc)
    end = datetime(2026, 1, 15, tzinfo=timezone.utc)
    observation = get_occupancy("fish", start, end, window=timedelta(minutes=30))
    model.load_prior("./modelling/data/Priors.xlsx")
    model.day_update(observation=observation, roomname="fish")