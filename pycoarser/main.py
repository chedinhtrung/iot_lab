from definitions import *
from config import *
def main():
    kitchen_stay_aggr = StayAggregator(source_bucket="1_7_12", sensor_type="door", roomname="door", cfg=kitchen_cfg)
    fish_stay_aggr = StayAggregator(source_bucket="1_8_14", sensor_type="PIR", roomname="fish", cfg=fish_cfg)
    desk_stay_aggr = StayAggregator(source_bucket="1_6_10", sensor_type="PIR", roomname="desk", cfg=desk_cfg)
    #desk_stay_aggr.loop()
    #fish_stay_aggr.loop()
    #kitchen_stay_aggr.loop()
    desk_activity_aggregator = ActivityAggregator(source_bucket="stays", roomname="desk", dest_bucket="activities", cfg=desk_cfg)
    fish_activity_aggregator = ActivityAggregator(source_bucket="stays", roomname="fish", dest_bucket="activities", cfg=fish_cfg)
    kitchen_activity_aggregator = ActivityAggregator(source_bucket="stays", roomname="door", dest_bucket="activities", cfg=kitchen_cfg) 
    fish_activity_aggregator.loop()

if __name__ == "__main__":
    main()