#
# dispatcher - runs everything
#

from logger import log
from utility import *
from pubsub import pubsub
import constants
import random
import time
from simtime import simtime
from stop_server import stop_server

class dispatcher(object) :

    the_dispatcher = None

    def __init__(self, args=None) :
        self.args = args
        if args :
            self.simulate = args.simulate
            self.time_dilution = args.time_dilution if self.simulate else 1
        else :
            self.simulate = False
            self.time_dilution = 1
        self.real_interval = constants.dispatch_interval / self.time_dilution \
                             if self.time_dilution>0 else 0
        self.my_class = "dispatcher"
        self.name = "single"
        self.tick_subs = pubsub()
        self.one_second_subs = pubsub()
        self.ten_second_subs = pubsub()
        self.stopping = False
        stop_server.listen(self._stop)
        dispatcher.the_dispatcher = self

    def start(self) :
        prev_simtime = 0
        ten_second_count = 0
        while not self.stopping :
            t = time.time()
            while self.real_interval > 0 :
                now = time.time()
                delay = self.real_interval - (now - t)
                if delay > 0 :
                    time.sleep(delay)
                if now - t >= self.real_interval :
                    break
            interval = constants.dispatch_interval if self.simulate else now - t
            simtime.advance(interval)
            st = simtime.time().get()
            self.tick_subs.signal(interval)
            if prev_simtime and int(prev_simtime) < int(st) :
                self.one_second_subs.signal(st)
                ten_second_count -= 1
                if ten_second_count <= 0 :
                    self.ten_second_subs.signal(st)
                    ten_second_count = 10
            prev_simtime = st

    def _add_tick_client(self, fn, *args) :
        self.tick_subs.listen(fn, *args)
            
    def _add_one_second_client(self, fn, *args) :
        self.one_second_subs.listen(fn, *args)
            
    def _add_ten_second_client(self, fn, *args) :
        self.ten_second_subs.listen(fn, *args)
            
    def run_once(self) :
        self.tick_subs.signal()

    def _fake_sensor(self, sensor) :
        log(self, 'fake sensor %s', sensor)
        if self.simulate :
            sensor.trigger()

    @staticmethod
    def fake_sensor(sensor) :
        dispatcher.the_dispatcher._fake_sensor(sensor)
        
    @staticmethod
    def emergency_stop() :
        log(dispatcher.the_dispatcher, "emergency stop requested")
        dispatcher.the_controller.emergency_stop()

    @staticmethod
    def add_tick_client(fn, *args) :
        dispatcher.the_dispatcher._add_tick_client(fn , *args)

    @staticmethod
    def add_one_second_client(fn, *args) :
        dispatcher.the_dispatcher._add_one_second_client(fn , *args)

    @staticmethod
    def add_ten_second_client(fn, *args) :
        dispatcher.the_dispatcher._add_ten_second_client(fn , *args)

    @staticmethod
    def is_simulated() :
        return dispatcher.the_dispatcher.simulate

    def _stop(self) :
        self.stopping = True
