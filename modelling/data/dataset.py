
from datetime import datetime, timedelta
from preprocessing import *
from preprocessing import *

class OccupancyDataset:
    def __init__(self, start:datetime, end:datetime, time_horizons:list, roomnames:list, window:timedelta):
        self.dataframe, self.roomnames = get_combined_bucketized_occupancy(start, end, window, roomnames)
        # split into train vs test set