from abc import ABC
from typing import List
from threading import Thread, Lock
from multiprocessing import Queue

from common import BaseFunction, Function, MetricsProcessor

import os
import pickle
import common
import traceback
import logging

from .updater import WeightUpdater

logger = logging.getLogger("fastapi_cli")


class Scheduler(ABC):
    def __init__(self, dispatcher: "Queue[common.Invocation]", weights: WeightUpdater,
                 base_path: str = "/data", chk_name: str = "scheduler.pkl"):
        self.chk_name = chk_name
        self.base_path = base_path
        self.function_loop: List[common.Function] = []
        self.event_loop: Queue[common.Event] = Queue()
        self.dispatcher: Queue[common.Invocation] = dispatcher
        self.lock = Lock()
        self.fn_names = []
        self.weights = weights
        super(Scheduler, self).__init__()
        self.restore_chk(os.path.join(base_path, chk_name))

    def return_event_loop(self) -> Queue:
        return self.event_loop

    def __reg_fn(self, fn_data: BaseFunction):
        logger.info("Creating a new function...")
        fn = Function(fn_data.name, fn_data.subs, fn_data.mock)
        fn.register_endpoint(fn_data.url, fn_data.method, fn_data.endpoint)
        self.function_loop.append(fn)
        self.fn_names.append(fn_data.name)
        path = os.path.join(self.base_path, self.chk_name)
        self.handle_chk(path)

    def register_fn(self, fn_data: BaseFunction):
        self.lock.acquire(blocking=True)
        if fn_data.name not in self.fn_names:
            self.__reg_fn(fn_data)
        else:
            try:
                idx = self.fn_names.index(fn_data.name)
                fn = self.function_loop[idx]
                fn.register_endpoint(
                    fn_data.url, fn_data.method, fn_data.endpoint)
                self.weights.register(fn_data.url)
            except ValueError:
                logger.info(
                    f"Failure during fetching function name {fn_data.name}...")
            path = os.path.join(self.base_path, self.chk_name)
            self.handle_chk(path)
        self.lock.release()

    def restore_chk(self, path: str):
        if os.path.isfile(path):
            with open(path, "rb") as chk:
                self.function_loop = pickle.load(chk)
            print("The following functions have been restored:")
            for fn in self.function_loop:
                fn.refresh_weights(self.weights)
                self.fn_names.append(fn.name)
                logger.info(fn.print())

    def __del_fn(self, name: str):
        del_idx = -1
        for idx, fn in enumerate(self.function_loop):
            if fn.name == name:
                del_idx = idx

        if del_idx >= 0:
            del self.function_loop[del_idx]
            self.fn_names.remove(name)
            path = os.path.join(self.base_path, self.chk_name)
            self.handle_chk(path)

    def delete_fn(self, name: str):
        self.lock.acquire(True)
        self.__del_fn(name)
        self.lock.release()

    def generate_invocation(self, fn: common.Function):
        path = os.path.join(self.base_path, self.chk_name)
        # self.function_loop.remove(fn)
        self.handle_chk(path)
        inv = fn.generate_invocation(self.weights)
        self.dispatcher.put(inv, True)

    def handle_chk(self, path: str):
        with open(path, "wb") as chk:
            pickle.dump(self.function_loop, chk)

    def status_sch(self):
        status = []
        self.lock.acquire(True)
        for fn in self.function_loop:
            fn_status = {}
            fn_status["subs"] = fn.subs
            fn_status["last_invoke"] = fn.last_invoke
            fn_status["events"] = []
            for rdy in fn.ready:
                evts = {"ready": [], "waiting": []}
                for idx, evt in enumerate(rdy):
                    if evt is None:
                        evts["waiting"].append(fn.subs[idx])
                    else:
                        evts["ready"].append(fn.subs[idx])
                fn_status["events"].append(evts)
            fn_status["name"] = fn.name
            status.append(fn_status)
        self.lock.release()
        return status

    def submit_event(self):
        pass

    def wait_loop(self) -> Thread:
        scheduler_thr = Thread(target=self._wait_loop)
        scheduler_thr.start()
        return scheduler_thr

    def process_fn(self, fn, event):
        ready_inv = fn.update_event(event)
        if ready_inv:
            self.generate_invocation(fn)

    def _wait_loop(self):
        while True:
            event = self.event_loop.get(True)
            self.lock.acquire(blocking=True)
            logger.info(f"Incoming event {event.name}")
            for fn in self.function_loop:
                try:
                    ready_inv = fn.update_event(event)
                    if ready_inv:
                        self.generate_invocation(fn)
                except Exception as errf:
                    logger.info(f"Error during generating invocations {errf}")
                    traceback.print_exc()
            self.lock.release()
