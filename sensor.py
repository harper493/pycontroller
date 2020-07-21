from dispatcher import dispatcher
from logger import log
from pubsub import pubsub
from simtime import simtime
from constants import *

class sensor(object) :

    sensors = {}

    def __init__(self, name, **args) :
        self.name = name
        try :
            int(name)
        except ValueError :
            raise ValueError("sensor names must be numeric, not '%s'" % (name,))
        self.last_triggered = None
        self.my_pubsub = pubsub()
        self.my_class = "sensor"
        self.active = False
        self.owner = None
        self.last_triggered = 0
        sensor.sensors[name] = self
        dispatcher.add_tick_client(self.tick)

    def trigger(self) :
        self.last_triggered = simtime.time()
        if not self.active :
            log(self, "triggered")
            self.active = True
            self.my_pubsub.signal()
        
    def listen(self, fn, *args) :
        self.my_pubsub.listen(fn, *args)

    def tick(self, duration) :
        if self.active and self.last_triggered + sensor_active_time < simtime.time() :
            log(self, "reset")
            self.active = False

    def is_active(self) :
        return self.active

    @staticmethod
    def get_sensor(name) :
        return sensor.sensors[name]

    @staticmethod
    def make_sensor_for(name, owner) :
        try :
            s = sensor.sensors[name]
        except KeyError :
            s = sensor(name)
            sensor.sensors[name] = s
        if s.owner :
            raise ValueError("sensor %s already owned by %s, not available for %s" \
                % (name, s.owner, owner))
        s.owner = owner
        return s

    @staticmethod
    def trigger_named(name) :
        try :
            sensor.sensors[name].trigger()
        except KeyError :
            pass

    def __str__(self) :
        return self.name

