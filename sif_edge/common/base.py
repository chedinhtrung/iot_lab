import pytz
import urllib3
import logging

from abc import ABC
from enum import Enum
from typing import Dict, Optional, Any, List, Union
from datetime import datetime
from pydantic import BaseModel

import json

from .status import EventStatus
from multiprocessing import Queue

logger = logging.getLogger("fastapi_cli")

logging.getLogger("requests").setLevel(logging.DEBUG)


class Endpoint(Enum):
    MICROSERVICE = 1
    KNATIVE = 2


class MetricsIndex(BaseModel):
    index: int


class EventRequest(BaseModel):
    name: str
    data: Optional[Dict[Any, Any]] | Optional[Any] = None


class DeleteFunction(BaseModel):
    name: str


class BaseFunction(BaseModel):
    name: str
    subs: List[str]
    url: str
    method: Optional[str] = "GET"
    endpoint: Optional[Endpoint] = Endpoint.MICROSERVICE
    mock: Optional[bool] = False


class Event(ABC):
    def __init__(self, name: str, data: List[Dict[Any, Any]] | Dict[Any, Any] | Any = None):
        super(Event, self).__init__()
        self.name: str = name
        self.data: List[Dict[Any, Any]] | Dict[Any, Any] = data
        self.status: EventStatus = EventStatus.CREATED
        self.timestamp: int = int(datetime.now().timestamp()*1000)


class Invocation(ABC):
    """
    Abstract class emerging from a function upon fulfilling all event(s)
    requirements.
    """

    def __init__(self, url: str, method: str, endpt_type, mock: bool, metrics_data,  ** kwargs):
        super(Invocation, self).__init__()
        self.kwargs = kwargs
        self.url = url
        self.method = method
        self.mock = mock
        self.endpt_type = endpt_type
        self.metrics_data = metrics_data

    def invoke(self, metrics: Queue, weights):
        try:
            if not self.mock:
                # TODO: Add retries method and provide feedback with function name
                if self.method == "GET":
                    self.kwargs = {}
                timeout = urllib3.Timeout(connect=10.0, read=None)
                http = urllib3.PoolManager(timeout=timeout, retries=5)
                self.metrics_data["request_start"] = int(
                    datetime.now().timestamp()*1000)
                # if self.endpt_type != Endpoint.MICROSERVICE:
                #     _url = urllib3.util.parse_url(self.url)
                #     url = f"http://kourier.kourier-system.svc.cluster.local{
                #         _url.path}"
                #     res = http.request(self.method, url, headers={
                #                        "Host": _url.host}, **self.kwargs)
                # else:

                res = http.request(self.method, self.url, **self.kwargs)

                self.metrics_data["request_end"] = int(
                    datetime.now().timestamp()*1000)
                weights.lock.acquire(True)
                weights.queue.put(1, True)
                weights.lock.release()
                weights.submit(
                    self.url,
                    self.metrics_data["request_end"]
                    - self.metrics_data["request_start"]
                )

                data = res.data.decode('utf-8')

                data = json.loads(data)

                self.metrics_data.update(data)

                if res.status >= 300:
                    logger.warn(
                        f"failure to invoke {res.url} because: {res.reason}")
                # logger.info("invocation has been dispatched")
                res.release_conn()
                res.close()
        except Exception as err:
            logger.error(f"Failure during invocation because {err}")
        self.metrics_data["event_end"] = int(
            datetime.now().timestamp()*1000)
        metrics.put(self.metrics_data, block=True)
        return


class RemoteInvocation(Invocation):
    def __init__(self):
        super(RemoteInvocation, self).__init__()


class Function(ABC):
    """
    Class identifying a function to be called upon an event.

    This class serves as the abstraction of remote requests upon
    the required events being generated. Once the events have
    arrived, the scheduler will generate an invocation from
    the function data, which includes the target's URL and
    correspondg event(s) data.
    """

    def __init__(self, name: str, subs: List[str], mock: bool = False):
        super(Function, self).__init__()

        self.name: str = name
        self.endpoints: Dict[str, Dict[str, Union[str, Endpoint]]] = dict()
        self.last_endpoint = -1
        self.events: Dict[str, List[Event]] = {}
        self.subs: List[str] = subs
        self.ready: List[List[str]] = []
        self.last_pos = None
        self.mock = mock
        self.last_invoke = None

        self.last_start = 0
        self.last_end = 0

        self.reset_fn()

    def reset_metrics(self, metrics: Queue):
        self.metrics = metrics

    def set_start(self):
        if self.last_start != 0:
            return
        self.last_start = int(datetime.now().timestamp()*1000)

    def set_end(self):
        if self.last_end != 0:
            return
        self.last_end = int(datetime.now().timestamp()*1000)

    def __repr__(self):
        return pformat(vars(self), indent=4)

    def print(self):
        return f"[{self.name}] -> {self.endpoints} ? {','.join(self.subs)}"

    def register_endpoint(self, url, method, endpt: Endpoint):

        pt = self.endpoints.get(url, None)
        if pt is None:
            self.endpoints[url] = {"method": method,
                                   "endpoint": endpt,
                                   "weight": 1,
                                   "count": 0}
        else:
            logger.info(
                f"Upating endpoint to {url} on {self.name}")
            self.endpoints[url].update({"endpoint": endpt, "method": method})

        return

    def refresh_weights(self, weights):
        for k, v in self.endpoints.items():
            weights.register(k)
            v.update({"weight": 1, "count": 0})

    def update_event(self, evt: Event) -> bool:
        if evt.name not in self.subs:
            return False
        self.set_start()
        if len(self.ready) == 0:
            self.events[evt.name] = [evt]
            idx = self.subs.index(evt.name)
            vals = [None for _ in range(len(self.subs))]
            vals[idx] = evt.name
            self.ready.append(vals)
            if None not in self.ready[-1]:
                self.last_pos = 0
                self.set_end()
                return True
            return False

        for idx, evt_tr in enumerate(self.ready):
            if evt.name in evt_tr:
                if None not in evt_tr:
                    self.last_pos = idx
                evts = [None for _ in range(len(self.subs))]
                evts[self.subs.index(evt.name)] = evt.name
                self.ready.insert(len(self.ready), evts)
                if self.events[evt.name]:
                    self.events[evt.name].insert(len(self.ready), evt)
                else:
                    self.events[evt.name] = [
                        None for _ in range(len(self.ready)+1)]
                    self.events[evt.name][len(self.ready)] = evt

                if None not in self.ready[-1]:
                    self.last_pos = len(self.ready) - 1
                    self.set_end()
                    return True
                return (self.last_pos is not None) or False
            else:
                jdx = self.subs.index(evt.name)
                if self.events[evt.name] is None:
                    self.events[evt.name] = [
                        None for _ in range(len(self.ready))]
                if idx > (len(self.events[evt.name]) - 1):
                    self.events[evt.name].insert(idx, evt)
                else:
                    self.events[evt.name][idx] = evt
                evt_tr[jdx] = evt.name
                if None not in evt_tr:
                    self.last_pos = idx
                    self.set_end()
                    return True
                return False
        return False

    def reset_fn(self):
        self.last_start = 0
        self.last_end = 0
        if self.last_pos is None:
            for topic in self.subs:
                self.events[topic] = None
            return

        if len(self.ready) > self.last_pos:

            lst = self.ready.pop(self.last_pos)

            for topic in self.subs:
                if len(self.events[topic]) > self.last_pos:
                    self.events[topic].pop(self.last_pos)

            # logger.info(
            #     f"removing {lst} from the ready queue for function {self.name}")
            self.last_pos = None

    def generate_invocation(self, weights) -> Invocation:
        env_start = 999999999999999
        kwargs = dict()
        for k, v in self.events.items():
            vals = dict()
            if v[self.last_pos].data:
                vals["data"] = v[self.last_pos].data
            vals["timestamp"] = v[self.last_pos].timestamp
            kwargs[k] = vals
            if v[self.last_pos].timestamp < env_start:
                env_start = v[self.last_pos].timestamp

        # self.last_endpoint = (self.last_endpoint + 1) % len(self.endpoints)
        # endpt = self.endpoints[self.last_endpoint]
        lst = []
        for k, _ in self.endpoints.items():
            lst.append(k)
        w = weights.search(lst)
        for (url, val) in w:
            if self.endpoints.get(url).get("weight") > val:
                self.endpoints[url]["weight"] = val
            elif self.endpoints.get(url).get("weight") < val:
                self.endpoints[url]["weight"] = val
                self.endpoints[url]["count"] = 0

        target_pt = None
        while target_pt is None:
            for (url, val) in w:
                tmp = self.endpoints.get(url)
                if tmp["weight"] > tmp["count"]:
                    target_pt = (url, tmp)
                    tmp["count"] += 1
                    break

            if target_pt is None:
                for k, _ in self.endpoints.items():
                    self.endpoints[k]["count"] = 0

        metrics = {
            "event_start": env_start,
            "invocation_waiting": self.last_start,
            "invocation_ready": self.last_end
        }

        inv = Invocation(target_pt[0], target_pt[1]["method"],
                         target_pt[1]["endpoint"], self.mock,
                         metrics, json=kwargs)
        self.reset_fn()
        self.last_invoke = int(datetime.now(
            pytz.timezone("Europe/Berlin")).timestamp()*1000)
        # logger.info(f"Invoking {target_pt[0]}...")
        return inv
