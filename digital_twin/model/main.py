from sifec_base import LocalGateway, base_logger, PeriodicTrigger, ExampleEventFabric
from model import get_latest_stay_stats

app = LocalGateway(mock=False)


async def dummy():
    base_logger.info("I passed the assignment")

# Deploy a route within this server to be reachable from the SIF scheduler
# it appends the name of the cb to `/api/`. For more, please read the
# documentation for `deploy`

def create_occupancy_model():
    print(f"train occupancy model event received")
    desk_stay_stats = get_latest_stay_stats("desk") 
    kitchen_stay_stats = get_latest_stay_stats("door")
    fish_stay_stats = get_latest_stay_stats("fish")

    # TODO: save to minio
    if desk_stay_stats["valid"]:
        print(f"Modelled desk stay: {desk_stay_stats}")
        
    if kitchen_stay_stats["valid"]:
        print(f"Modelled kitchen stay: {kitchen_stay_stats}")
        
    if fish_stay_stats["valid"]:
        print(f"Modelled fish stay: {fish_stay_stats}")
        
    
app.deploy(cb=dummy, name="dummy_modelling", evts="ClassTestEvent", path="dummy_modelling")
app.deploy(cb=create_occupancy_model, name="CreateOccupancyModel", evts="TrainOccupancyModelEvent", path="CreateOccupancyModel")