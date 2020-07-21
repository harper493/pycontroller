#
# object class to represent a train
#

from utility import *
from locomotive import locomotive
from logger import log, trace
from simtime import simtime
from dispatcher import dispatcher
import constants
import random
import traceback

class train(object) :

    trains = {}

    arg_table = { 'loco' : None,
                  'length' : 0,
                  'max_speed' : constants.default_max_speed,
                  'cruise_speed' : constants.default_cruise_speed,
                  'slowing_speed' : None,
                  'stopping_speed' : None,
                  'min_radius' : 0,
                  'max_reverse_speed' : None,
                  'reversible' : False,
                  'reverse_ok' : False,
                  'mean_wait' : constants.default_mean_wait,
                  'max_wait' : constants.default_max_wait
              }

    first = True

    def __init__(self, name, **args) :
        construct(self, train.arg_table, args)
        self.name = name
        if self.reversible :
            self.max_reverse_speed = self.max_speed
        self.section = None
        self.speed = 0
        self.reversed = False   # fwd/rev interchanged, for reversible trains
        self.reverse = False    # currently going "backwards" for selected direction
        if self.reversible :
            self.reverse_ok = True
        self.loco = locomotive.get(self.loco)
        self.active = False
        self.my_class = "train"
        self.head = None
        self.tail = None
        self.hold_until = None
        self.last_speed_change = None
        self.last_terminate = simtime.time()
        self.slowing_speed = self.slowing_speed \
                             or min(self.cruise_speed, constants.default_slowing_speed)
        self.stopping_speed = self.stopping_speed \
                             or min(self.slowing_speed, constants.default_stopping_speed)
        #print '***', self.name, self.max_speed, self.cruise_speed, self.slowing_speed, self.stopping_speed
        train.trains[name] = self
        if train.first :
            train.first = False
            train.init_class()

    @staticmethod
    def init_class() :
        dispatcher.add_ten_second_client(train.status_reporter)

    def is_active(self) :
        return self.active

    def is_available(self) :
        return not self.active and \
            (self.hold_until is None or simtime.time() > self.hold_until)

    def is_reversible(self) :
        return self.reversible

    def activate(self, dir=None, **speed) :
        if dir is not None and dir!=self.head.direction :
            self.set_reversed()
        self.active = True
        self.hold_until = None
        self._log_me("activate")
        self.set_speed(**speed)

    def deactivate(self, do_wait=True) :
        self.active = False
        if do_wait :
            wait = min(random.weibullvariate(self.mean_wait, constants.weibull_shape), self.max_wait)
        else :
            wait = 0
        self.last_terminate = simtime.time()
        self.hold_until = self.last_terminate + wait
        self._log_me("deactivate", "wait %.2f", wait)

    def set_speed(self, speed=None, cruise=False, slowing=False, \
                  stopping=False, on_behalf_of=None) :
        if self.last_speed_change==simtime.time() :
            traceback.print_stack()
        self.last_speed_time = simtime.time()
        requested = speed
        limit = self.max_speed
        if self.active :
            if cruise :
                limit = min(limit, self.cruise_speed)
            elif slowing :
                limit = min(limit, self.slowing_speed)
            elif stopping :
                limit = min(limit, self.stopping_speed)
            if speed is None :
                speed = limit
            else :
                speed = min(speed, limit)
        else :
            speed = 0
        if self.speed != speed :
            self.speed = speed
            self._control()
            self._log_me("set_speed", extra='for %s requested %s limit %s', \
                         args=(on_behalf_of, requested, limit))

    def get_speed(self) :
        return self.speed

    def set_forward(self, rev) :
        if self.reverse_ok or not rev :
            self.reverse = rev
            self._control()

    def set_reversed(self) :
        if self.reverse_ok :
            self.reversed = not self.reversed
            self._log_me("turning around", "reversed %s", self.reversed)
            self._control()

    def set_head(self, next) :
        self.head = next
        self._log_me("set_head")

    def set_tail(self, next) :
        self.tail = next
        self._log_me("set_tail")

    def get_length(self) :
        result = self.length
        try :
            result += self.loco.length
        except : pass
        return result

    def idle_time(self) :
        return simtime.time() - self.last_terminate
        
    def get_actual_speed(self) :
        return self.loco.get_actual_speed()

    def stop(self) :
        if self.speed :
            self._log_me("stopping")
            self.set_speed(0)

    def _control(self) :
        if self.loco :
            self.loco.set_speed(self.speed, (self.reverse ^ self.reversed))

    def report_status(self) :
        self._log_me("status")

    def _log_me(self, why, extra=None, args=tuple()) :
        log(self, "%s: %s %s", why, self.describe(), (extra % args if extra else ''))

    def describe(self, name=False) :
        result = "head %s tail %s speed %s %s last_terminate %s hold %s" % \
                 (self.head, self.tail, self.speed, \
                  "active" if self.active else "inactive", \
                  self.last_terminate, self.hold_until)
        if name :
            result = ' '.join([self.name, result])
        return result

    @staticmethod
    def get(name) :
        try :
            return train.trains[name]
        except KeyError :
            return None

    def __str__(self) :
        return self.name

    @staticmethod
    def visit_all(fn) :
        return [ fn(train.trains[k]) for k in sorted(train.trains.keys()) ]

    @staticmethod
    def status_reporter(x) :
        if constants.log_train_status :
            train.visit_all(train.report_status)
