#
# serial_port class - deliver completed lines to listener function
#

import serial
import time
import threading
from logger import log
from stop_server import stop_server

DEFAULT_BAUDRATE = 9600

class serial_port(object) :

    def __init__(self, device=None, listener=None, args=tuple(), \
                 baudrate=DEFAULT_BAUDRATE, timeout=0, whole_lines=True) :
        self.listener, self.args, self.baudrate, self.timeout = \
            listener, args, baudrate, timeout
        self.port = None
        self.device = '/dev/' + device if device else None
        self.last_message_time = None
        self.whole_lines = whole_lines
        self.my_class = 'serial_port'
        self.name = self.device
        self.stopping = False
        self.connected = False
        stop_server.listen(self.stop)
        if self.device :
            self.thread = threading.Thread(name=('serial_port:'+(device or '')), \
                                           target=serial_port.receiver, args=(self,))
            self.thread.start()
        else :
            self.thread = None

    def is_connected(self) :
        return self.connected

    def connect(self) :
        if self.device :
            self.connected = False
            log(self, 'trying to connect to %s', self.device)
            while True :
                try :
                    self.port = serial.Serial(port=self.device,
                                              baudrate=self.baudrate,
                                              timeout=1)
                    self.connected = True
                    log(self, 'connected to %s', self.device)
                    break
                except (IOError, OSError) :
                    time.sleep(1)
        else :
            self.port = None

    def receiver(self) :
        self.connect()
        line = ''
        while not self.stopping :
            ch = None
            try :
                if self.port :
                    ch = self.port.read()
                else :
                    time.sleep(1)
            except IOError :
                log(self, 'lost connection to %s, trying to reconnect', self.device)
                self.connect()
                continue
            if ch or not self.whole_lines :
                if not self.whole_lines :
                    (self.listener)(*(self.args + (ch or '',)))
                elif ch=='\n' :
                    self.last_message_time = time.time()
                    (self.listener)(*(self.args + (line,)))
                    line = ''
                elif ch!='\r' :
                    line += ch

    def stop(self) :
        self.stopping = True
        if self.thread :
            self.thread.join()

    def write(self, msg) :
        if self.port :
            return self.port.write(msg)
        else :
            return 0
                    
