from common import EventRequest, Event, BaseFunction, Function, DeleteFunction, MetricsProcessor, MetricsIndex
from fastapi import FastAPI
from dispatcher import Dispatcher
from scheduler import Scheduler, WeightUpdater
import builtins
import traceback

app = FastAPI()

metrics = MetricsProcessor()

weights = WeightUpdater()

dispatcher = Dispatcher(metrics.init(), weights)
sch = Scheduler(
    dispatcher=dispatcher.return_event_loop(), weights=weights)

dispatcher.wait_loop()
sch.wait_loop()

sch_evt_loop = sch.return_event_loop()


@app.post("/api/event", status_code=200)
def handle_event(evt_req: EventRequest):
    print(f"Got event {evt_req.data}")
    evt = Event(evt_req.name, data=evt_req.data)
    sch_evt_loop.put(evt, True)
    return {"status": 200}


@app.post("/api/function")
def register_fn(fn_data: BaseFunction):
    sch.register_fn(fn_data)
    return


@app.delete("/api/function")
def delete_fn(fn_data: DeleteFunction):
    sch.delete_fn(fn_data.name)
    return


@app.get("/api/status")
def status_fn():
    return sch.status_sch()


@app.get("/api/reset")
def reset_samples():
    metrics.reset_file()


@app.post("/api/reset")
def reset_metrics(data: MetricsIndex):
    weights.set_index(data.index)
    return {"status": 200}
