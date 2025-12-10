from sifec_base import LocalGateway, base_logger, PeriodicTrigger, ExampleEventFabric


app = LocalGateway(mock=True)


async def dummy():
    base_logger.info("I passed the assignment")

# Deploy a route within this server to be reachable from the SIF scheduler
# it appends the name of the cb to `/api/`. For more, please read the
# documentation for `deploy`
app.deploy(cb=dummy, name="dummy_monitor", evts="ClassTestEvent", path="dummy_monitor")