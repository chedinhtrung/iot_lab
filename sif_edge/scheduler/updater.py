import time
import logging

from abc import ABC
from threading import Thread
from multiprocessing import Queue, Lock
import urllib3

from kubernetes import config, client

logger = logging.getLogger("fastapi_cli")


class WeightUpdater(ABC):
    def __init__(self):
        super(WeightUpdater, self).__init__()
        self.__lock = Lock()
        self.__update_lock = Lock()
        self.__queue = Queue()
        self.thr = Thread(target=self.__run)
        self.thr.start()
        self.__endpoints = dict()
        self.__endpoint_queue = Queue()
        self.thr_queue = Thread(target=self.__collect_runtime)
        self.thr_queue.start()
        self.thr_weights = Thread(target=self.update_weights)
        self.thr_weights.start()
        self.reqps = 0
        self.index = -1

        config.load_incluster_config()
        self.client = client.AppsV1Api()

        with open("/data/data.csv", "w") as file:
            file.write("index,endpoint,weight,avg,reqps,replicas\n")

    def set_index(self, index):
        self.index = index

    def generate_name(self, url):
        host = urllib3.util.parse_url(url)
        path = host.hostname.split(".")[0]
        return path

    def fetch_replicas(self, name):
        for ns in ["default", "digitaltwin"]:
            replicaset = self.client.list_namespaced_replica_set(ns)
            for rs in replicaset.items:
                if rs.metadata.name.startswith(name):
                    replicas = rs.status.replicas
                    return int(replicas)

    def flush(self, reqps: int):
        self.reqps = reqps
        with open("/data/data.csv", "a") as file:
            for k, v in self.__endpoints.items():
                path = self.generate_name(k)
                replicas = self.fetch_replicas(path)
                line = f"""{self.index},{path},{v['weight']},{
                    v['metrics']},{reqps},{replicas}\n"""
                file.write(line)
                logger.info(line)

    def register(self, endpoint: str):
        if self.__endpoints.get(endpoint, None) is None:
            for ns in ["default", "digitaltwin"]:
                replicaset = self.client.list_namespaced_replica_set(ns)
                name = self.generate_name(endpoint)
                for rs in replicaset.items:
                    if rs.metadata.name.startswith(name):
                        re = int(rs.metadata.annotations.get(
                            "autoscaling.knative.dev/max-scale", "1"))
                        self.__endpoints[endpoint] = {
                            "weight": 1, "metrics": 0.0, "ready": False,
                            "count": 0, "max_replica": re}

    @property
    def queue(self):
        return self.__queue

    @property
    def lock(self):
        return self.__lock

    def search(self, urls):
        if isinstance(urls, str):
            urls = [urls]
        weights = []
        for url in urls:
            pt = self.__endpoints.get(url, None)
            if pt is not None:
                weights.append((url, pt["weight"]))

        weights.sort(key=lambda x: x[1], reverse=True)
        return weights

    def __collect_runtime(self):
        while True:
            obj = self.__endpoint_queue.get(True)
            with self.__update_lock:
                if self.__endpoints.get(obj["endpoint"], None) is None:
                    self.register(obj["endpoint"])

                pt = self.__endpoints[obj["endpoint"]]
                pt["count"] += 1
                pt["metrics"] = pt["metrics"] + \
                    (obj["runtime"] - pt["metrics"])/pt["count"]
                if pt["count"] % 4 == 0:
                    pt["ready"] = True
                self.__endpoints[obj["endpoint"]].update(pt)

    def update_weights(self):
        time.sleep(10)
        open = []
        while True:
            time.sleep(2)
            items = []
            try:
                with self.__update_lock:
                    if len(open) < 2:
                        for k, v in self.__endpoints.items():
                            if v.get("ready") and k not in open:
                                open.append(k)
                        continue

                    for k, v in self.__endpoints.items():
                        if v.get("ready", False):
                            items.append(
                                (k,
                                 v.get("metrics")/v.get("max_replica")
                                 )
                            )
                    items.sort(key=lambda x: x[1])
                    new_weights = []
                    if len(items) > 1:
                        for idx, item in enumerate(items):
                            i = idx+1 if idx < len(items)-1 else 0
                            nxt = items[i]
                            nw = int(nxt[1]/item[1]+1)*self.reqps/2
                            new_weights.append((item[0], nw))

                    for (pt, w) in new_weights:
                        if self.__endpoints.get(pt, None) is not None:
                            self.__endpoints[pt]["weight"] = w
            except Exception as err:
                logger.error(f"Failure during weight update {err}")
                continue

    def __run(self):
        logger.info("Loop to check for performance...")
        while True:
            time.sleep(1)
            self.__lock.acquire(True)
            reqps = self.__queue.qsize()
            self.flush(reqps)
            self.queue.empty()
            self.__lock.release()

    def submit(self, endpoint, runtime):
        self.__endpoint_queue.put(
            {
                "endpoint": endpoint,
                "runtime": runtime
            },
            True
        )
