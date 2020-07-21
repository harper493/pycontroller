from dispatcher import dispatcher
from pubsub import pubsub
from sensor import sensor
from logger import log
from time import localtime, strftime
import threading

SENSOR_LOGFILE = 'log_sensor.txt'

class sensor_listener(object) :

    listeners = {}
    lock = threading.Lock()
    logfile = open(SENSOR_LOGFILE, 'w')

    def __init__(self) :
        self.last_message = 0
        self.lost_messages = 0
        self.bad_messages = 0
        self.good_messages = 0
        self.my_pubsub = pubsub()
        self.last_trigger = None
        self.my_class = "sensor_listener"
        self.prev_values = None
        sensor_listener.listeners[self.name] = self
        dispatcher.add_tick_client(self.tick)

    def digest(self, line) :
        with sensor_listener.lock :
            sensor_listener.logfile.write('%s %s\n' % \
                (strftime("%Y-%m-%d %H:%M:%S\n", localtime()), line.strip('\n\r ')))
            sensor_listener.logfile.flush()
        if line and line[0]=='S' :
            good = False
            fields = line[1:].split()
            try :
                base = int(fields[0])
                seq = int(fields[1])
                values = fields[2]
            except Exception as exc :
                pass
            else :
                if values != self.prev_values :
                     log(self, "changed new %s old %s", values, self.prev_values)
                     self.prev_values = values
                if seq >= self.last_message+1 :
                    if self.last_message+1 < seq :
                        self.lost_messages += seq - self.last_message
                        log(self, '%d lost messages', seq - self.last_message)
                    good = True
                    for i in range(len(values)) :
                        if values[i]=='1' :
                            s = str(base+i)
                            sensor.trigger_named(s)
                self.last_message = seq
            if good :
                self.good_messages += 1
            else :
                self.bad_messages += 1
                log(self, 'incorrect message: %s', line)

    def tick(self) :
        pass

    @staticmethod
    def visit_all(fn) :
        list(map(fn, sensor_listener.listeners))

       
