import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from modelling.data.preprocessing import get_bucketized_occupancy
from modelling.data.preprocessing import *
import os
import pickle

from sklearn.linear_model import Ridge
from minio import Minio
import io
from minio.error import S3Error

MINIO = Minio(
    "192.168.0.103:9090",
    access_key="bSYIFuEHZa3JHTKg6WE9",
    secret_key="u8TnjmYYEcUJNugWSOUZwXEDqu2FU2JToOIAx2Lt",
    secure=False,
)

class StayDurationModel: 
    def __init__(self, window:timedelta, rooms:list=["kitchen", "desk", "fish"], 
                 history:timedelta=timedelta(days=60)):
        self.rooms = rooms
        self.window = window
        self.history = history
        self.models = {}
        for room in self.rooms:
            self.models[room] = Ridge(alpha=0.1)
        
        self.models["Void"] = Ridge(alpha=0.1)
    
    def _train(self, data):
        features, labels, rooms = preprocess_to_features_labels(data)   # pne for each room
        for index, room in enumerate(rooms): 
            feature = features[index][features[index]["occupied"]]
            label = labels[index][features[index]["occupied"]]
            assert len(feature) == len(label)
            if len(feature) == 0: 
                continue
            feature.drop(columns=["occupied"])
            self.models[room].fit(feature, label)
    
    def train(self): 
        end = datetime.now(tz=timezone.utc)
        start = end - self.history
        data, rooms = get_combined_bucketized_occupancy(start=start, end=end, window=self.window, rooms=self.rooms)
        self._train(data)

    def _predict(self, data):
        features, labels, rooms = preprocess_to_features_labels(data)
        
        for index, room in enumerate(rooms): 
            feature = features[index].tail(1)
            if feature["occupied"].any():
                feature.drop(columns=["occupied"])
                model = self.models[room]
                duration = model.predict(feature)
                duration = np.exp(duration) - 1
                actual_duration = np.exp(feature["occupancy_time"].iloc[0]) - 1
                return room, timedelta(minutes=duration[0]), timedelta(minutes=actual_duration)

    def predict(self):
        end = datetime.now(tz=timezone.utc)
        start = end - timedelta(days=1)    # has to do -1 day for buffering
        data, rooms = get_combined_bucketized_occupancy(start=start, end=end, window=self.window, rooms=self.rooms)
        return self._predict(data)
        

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
    MINIO.put_object(
        bucket_name="models",
        object_name=f"history/{name}_{timestamp}.pkl",
        data=buf,
        length=buf.getbuffer().nbytes,
    )

if __name__ == "__main__":
    model = StayDurationModel(window=timedelta(minutes=10))
    model.train()
    model.predict()