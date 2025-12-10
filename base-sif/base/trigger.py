import time
import durationpy

from abc import ABC
from datetime import timedelta, datetime, tzinfo
from threading import Thread

from apscheduler.triggers.cron import CronTrigger
from apscheduler.schedulers.background import BackgroundScheduler

from base import BaseEventFabric


def one_shot_cb(cb):
    def handler():
        cb()
        return schedule.CancelJob
    return handler


class Trigger(ABC):
    """
    Child objects of the :class:`Trigger <Trigger>` represent either One-Shot or
    Periodic Triggers for Event Request generation through the :class:`BaseEvent <event.BaseEvent>`
    factory.

    Once any child of this class has been instantiated, it will launch a local
    scheduler, which calls the given callback. The callback must take arguments.

    :param eventCallback: :class:`BaseEvent <event.BaseEvent>` instance to be called
    :param oneShot: indicates if the trigger must be run only once
    :param runImmediate: indicates the trigger should fire immediately
    :param cronSpec: indicates the periodicity of the trigger using Cron syntax
    """

    def __init__(self,
                 eventCallback: BaseEventFabric,
                 oneShot: bool,
                 runImmediate: bool = False,
                 cronSpec: str = "* * * * *"
                 ):
        super(Trigger, self).__init__()

        # Instantiate the BackgroundScheduler
        self.scheduler = BackgroundScheduler()
        self.job_identifier = None

        if runImmediate:
            next_time = datetime.now() + timedelta(seconds=30)
            self.scheduler.add_job(eventCallback,
                                   trigger="date",
                                   run_date=next_time,
                                   timezone="Europe/Berlin"
                                   )

        if oneShot and not runImmediate:
            self.job_identifier = self.scheduler.add_job(self.oneShotCallback(eventCallback),
                                                         CronTrigger.from_crontab(cronSpec, "Europe/Berlin"))

        if not oneShot:
            self.scheduler.add_job(eventCallback,
                                   CronTrigger.from_crontab(cronSpec,
                                                            "Europe/Berlin")
                                   )

        self.scheduler.start()

    def oneShotCallback(self, eventCallback: BaseEventFabric):
        def exec():
            eventCallback()
            self.scheduler.remove_job(self.job_identifier.id)
        return exec


class OneShotTrigger(Trigger):
    """
    Creates a One-Shot Trigger

    :param evt_cb: :class:`BaseEvent <event.BaseEvent>` instance to be called
    :param wait_time: indicates if there must be a delay before scheduling the first executions
    """

    def __init__(self, evt_cb: BaseEventFabric, runImmediate: bool = True, cronSpec: str = "* * * * *"):
        super(OneShotTrigger, self).__init__(
            evt_cb, oneShot=True, runImmediate=runImmediate, cronSpec=cronSpec)


class PeriodicTrigger(Trigger):
    """
    Creates a Periodic Trigger

    :param evt_cb: :class:`BaseEvent <event.BaseEvent>` instance to be called
    :param duration: frequency of event generation using Golang's time representation, e.g., 1h1m1s
    :param wait_time: indicates if there must be a delay before scheduling the first executions
    """

    def __init__(self, evt_cb: BaseEventFabric, runImmediate: bool = False, cronSpec: str = "* * * * *"):
        super(PeriodicTrigger, self).__init__(
            evt_cb, oneShot=False, runImmediate=runImmediate, cronSpec=cronSpec)
