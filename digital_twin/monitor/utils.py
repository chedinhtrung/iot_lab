from config import *
from datetime import datetime, timezone, timedelta

from sifec_base import BaseEventFabric

class EmergencyEvent(BaseEventFabric):
    def __init__(self, data:dict):
        super().__init__()
        self.data = data
    
    def call(self): 
        return "emergency_event", self.data


def check_emergency():
    """
        uses the emergency detector model to compute emergency
    """
    pass

if __name__ == "__main__":
    pass