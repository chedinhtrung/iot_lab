from sifec_base import LocalGateway, base_logger, PeriodicTrigger, ExampleEventFabric


app = LocalGateway(mock=False)

def emergency_notify(data:dict):
    print(f"emergency event received!")
    print(data)
    # TODO: get the event detail: location, time, confidence
    # send the email
    return

app.deploy(cb=emergency_notify, name="emergency_notify", evts="EmergencyEvent", method="POST")

