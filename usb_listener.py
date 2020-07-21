import socket
import time
import sys
import os
from datetime import datetime
from sensor_listener import sensor_listener
from serial_port import serial_port
from logger import log, trace
from utility import *

DEFAULT_BAUDRATE = 115200
DEFAULT_TIMEOUT = 3
CONNECT_MESSAGE_THRESHOLD = 3

class usb_listener(sensor_listener) :

    listeners = set()

    def __init__(self, device, baudrate=DEFAULT_BAUDRATE, timeout=DEFAULT_TIMEOUT) :
        self.name = device
        sensor_listener.__init__(self)
        self.device = device
        self.baudrate = baudrate
        self.timeout = timeout
        self.my_class = 'usb_listener'
        self.port = serial_port(device, sensor_listener.digest, args=(self,), \
                                baudrate=baudrate, timeout=timeout)

    def start(self) :
        pass

    def stop(self) :
        self.port.stop()

    def tick(self, t) :
        if self.last_message and self.last_message + self.timeout < t :
            #self.disp.emergency_stop()
            log(self, "no message received for %f seconds from %s", self.timeout, self.device)

    def is_connected(self) :
        return self.port.is_connected() and self.good_messages > CONNECT_MESSAGE_THRESHOLD

    @staticmethod
    def make_listeners(exclude=[]) :
        for d in find_devices("cu.usbmodem", exclude) :
            listener = usb_listener(d)
            usb_listener.listeners.add(listener)
            listener.start()

    @staticmethod
    def all_connected() :
        result = True
        for l in usb_listener.listeners :
            result &= l.is_connected()
        return result

