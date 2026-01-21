from threading import Thread
from multiprocessing import Queue


class MetricsProcessor(object):
    def __init__(self):
        super(MetricsProcessor, self).__init__()

        self.queue = None

        self.init()

        self.thr = Thread(target=self.run)
        self.thr.start()

    def init(self):
        if self.queue is None:
            self.queue = Queue()
            with open("/data/samples.csv", "w") as file:
                file.write(
                    "event_start,event_end,invocation_waiting,invocation_ready,request_start,request_end,pred_start,pred_end\n")

        return self.queue

    def reset_file(self):
        with open("/data/samples.csv", "w") as file:
            file.write(
                "event_start,event_end,invocation_waiting,invocation_ready,request_start,request_end,pred_start,pred_end\n")

    def write_entry(self, recv):
        ln = f"""{recv['event_start']},{recv['event_end']},{recv['invocation_waiting']},{
            recv['invocation_ready']},{recv['request_start']},{recv['request_end']},{recv['pred_start']},{recv['pred_end']}\n"""
        with open("/data/samples.csv", "a") as file:
            file.write(ln)

    def run(self):
        while (True):
            try:
                recv = self.queue.get(block=True)
                self.write_entry(recv)
            except Exception:
                print("Failure during processing entries...")
