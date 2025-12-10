from sifec_base import BaseEventFabric

class TrainModelEvent(BaseEventFabric):
    def __init__(self):
        super().__init__()
    
    def call(self, *args, **kwargs):
        return
