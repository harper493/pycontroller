#
# object class to represent a locomotive
#

from layout_controller import layout_controller
from dispatcher import dispatcher
from utility import *
from logger import log
import constants
from simtime import simtime

class locomotive(object) :

    locomotives = {}

    arg_table = { 'dcc_id' : 0,
                  'length' : 0.0,
                  'magnet_offset' : 0.0,
                  'normal_acceleration' : constants.default_normal_acceleration,
                  'normal_deceleration' : constants.default_normal_deceleration,
                  'max_speed' : constants.default_max_speed,
                  'reverse_ok' : True,
                  'celerity' : 1.0,
                  'opt_lights' : 1,
                  'opt_whistle' : 2,
                  'opt_bell' : 3,
              }

    def __init__(self, name, **args) :
        construct(self, locomotive.arg_table, args)
        self.my_class = "loco"
        self.name = name
        self.desired_speed = 0
        self.actual_speed = 0
        self.last_speed_change = None
        self.reverse = False
        self.options = set()
        locomotive.locomotives[name] = self
        dispatcher.add_tick_client(self.tick)
        
    def set_speed(self, speed, reverse) :
        log(self, "setting speed %.1f rev %s dcc_id %d dcc_speed %d" \
            % (speed, reverse, self.dcc_id, self._make_dcc_speed(speed)))
        s = speed
        if self.max_speed :
            s = min(s, self.max_speed)
        self.desired_speed = s
        if self.reverse_ok or not rev :
            self.reverse = reverse
        self.control()

    def set_option(self, opt) :
        self.options.add(opt)

    def clear_option(self, opt) :
        self.options.discard(opt)

    def control(self) :
        speed = self.actual_speed
        now = simtime.time()
        if self.last_speed_change is None or \
           self.last_speed_change + constants.min_speed_change_interval < now or \
           (self.desired_speed==0 and self.actual_speed > 0) :
            if self.desired_speed > self.actual_speed :
                if self.last_speed_change :
                    interval = now - self.last_speed_change
                    speed += interval * self.normal_acceleration
                    speed = min(speed, self.desired_speed)
            elif self.desired_speed==0 :
                speed = 0
            elif self.desired_speed < self.actual_speed :
                if self.last_speed_change :
                    interval = now - self.last_speed_change
                    speed -= interval * self.normal_deceleration
                    speed = max(speed, self.desired_speed)
            self.name, self.actual_speed, self.desired_speed, speed
            self.last_speed_change = now
            if self.actual_speed != speed :
                self.actual_speed = speed
                layout_controller.set_loco(self.dcc_id, self._make_dcc_speed(speed), \
                                           self.reverse, self.options)

    def tick(self, duration) :
        self.control()

    def get_actual_speed(self) :
        #print '!!!', self.actual_speed, self.celerity
        return self.actual_speed * self.celerity

    def _make_dcc_speed(self, speed) :
        return int(min(float(speed)/self.max_speed * 128, 127))
        
    @staticmethod
    def get(name) :
        try :
            return locomotive.locomotives[name]
        except KeyError :
            return None

    def __str__(self) :
        return self.name

