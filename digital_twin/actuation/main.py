from sifec_base import LocalGateway, base_logger, PeriodicTrigger, ExampleEventFabric


app = LocalGateway(mock=True)


async def dummy():
    base_logger.info("I passed the assignment")

def emergency_notify():
    print(f"emergency event received")
    # TODO: get the event detail: location, time, confidence
    # send the email
    return

# Deploy a route within this server to be reachable from the SIF scheduler
# it appends the name of the cb to `/api/`. For more, please read the
# documentation for `deploy`
app.deploy(cb=dummy, name="dummy_actuation", evts="ClassTestEvent", path="dummy_actuation")
app.deploy(cb=emergency_notify, name="EmergencyNotify", evts="EmergencyEvent", path="EmergencyNotify")

