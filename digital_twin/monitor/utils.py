from config import *
from datetime import datetime, timezone, timedelta

from sifec_base import BaseEventFabric

class PeriodicFunctionEvent(BaseEventFabric):
    def __init__(self, func):
        super().__init__()
        self.func = func 
    
    def call(self):
        return self.func.__name__, None

class EmergencyEvent(BaseEventFabric):
    def __init__(self, data:dict):
        super().__init__()
        self.data = data 
    
    def call(self):
        return "emergency_event", self.data

if __name__ == "__main__":
    pass