#controller for NCE systemdummy controller when running simulated
#

from layout_controller import layout_controller
from logger import log, trace
from serial_port import serial_port
from utility import *
import constants
import functools
import threading
import operator
import time
from functools import reduce

ACC_REPEAT_COUNT = 3

CMD_LOCO = 0xa2
CMD_TRKQ3 = 0xa3
CMD_ACC3 = 0x93
CMD_PING = 0x80
OP_FWD128 = 0x04
OP_REV128 = 0x03
OP_ESTOP_FWD = 0x06
OP_ESTOP_REV = 0x05
OP_FWD_REV = 0x01
OP_FN0X4 = 0x07
OP_FN5X8 = 0x08
OP_FN9X12 = 0x09

DEFAULT_CTRL_BAUDRATE = 9600
CTRL_TIMEOUT = 0.1

#
# Table of function groups, their bit values and the corresponding opcodes.
#
    
function_groups = (
    ( { 0:0x10, 1:0x01, 2:0x02, 3:0x04, 4:0x08 }, OP_FN0X4 ),
    ( { 5:0x01, 6:0x02, 7:0x04, 8:0x08 }, OP_FN5X8 ),
    ( { 9:0x01, 10:0x02, 11:0x04, 12:0x08 }, OP_FN9X12 ),
)
class nce_controller(layout_controller) :

    loco_options = {}

    def __init__(self, device=None, baudrate=DEFAULT_CTRL_BAUDRATE, \
                 timeout=CTRL_TIMEOUT) :
        self.name = 'nce'
        layout_controller.__init__(self)
        d = None
        if device :
            self.device = device
        else :
            d = find_devices("cu.usbserial")
            if d :
                self.device = d[0]
            else :
                self.device = ''
        self.baudrate, self.timeout = baudrate, timeout
        self.port = serial_port(self.device, nce_controller.listener, args=(self,), \
                                baudrate=baudrate, timeout=timeout, whole_lines=False)
        self.last_msg = None
        self.last_xmit_time = None
        self.pending = []
        self.lock = threading.Lock()
        self.timeouts = 0
        self.receive_errors = 0

    def is_connected(self) :
        return self.port.is_connected()
                
    def _set_loco(self, dcc_id, speed, reverse, options=[]) :
        try :
            prev_opts = nce_controller.loco_options[dcc_id]
        except KeyError :
            prev_opts = set()
        new_opts = set(options)
        if new_opts != prev_opts :
            self._send_options(dcc_id, prev_opts, new_opts)
            nce_controller.loco_options[dcc_id] = new_opts
        if speed < 0 :
            op = OP_ESTOP_FWD
            speed = 1
        else :
            if speed > 0 :
                speed += 1
            op = OP_FWD128
        if reverse :
            op -= OP_FWD_REV
        msg = self._make_loco_msg(dcc_id, op, min(int(speed), 127))
        self.send_msg(msg)
        log(self, "setting loco %d speed %s%s options %s msg %s",
            dcc_id, '-' if reverse else '', speed, \
            ','.join([str(o) for o in options]) if options else '<None>', \
            self.show_msg(msg))

    def _set_turnout(self, dcc_id, thrown, callback=None) :
        msg = bytearray([CMD_ACC3, 0x02]) + self._make_acc_packet(dcc_id, thrown)
        self.send_msg(msg, callback)
        log(self, "setting turnout %d%s msg %s",
              dcc_id, "R" if thrown else "N", self.show_msg(msg))

    def _make_acc_packet(self, address, state) :
        msg_adr = ((address - 1) >> 2) + 1
        hiaddr = ((~msg_adr)>>6) & 0x07
        channel = ((address-1) & 0x03) << 1
        result = bytearray([0x80 | (msg_adr & 0x3f), \
                            0x88 | (hiaddr<<4) | channel | (0 if state else 1)])
        return self._make_check_bits(result)

    def _make_loco_msg(self, dcc_id, op, data) :
        return bytearray([CMD_LOCO, 0x00, int(dcc_id), int(op), (int(data) & 0xff)])

    def _send_options(self, dcc_id, prev, new) :
        diff = prev.symmetric_difference(new)
        for fg in function_groups :
            k = set(fg[0].keys())
            if not k.isdisjoint(diff) :
                data = reduce(operator.or_, [ m for b,m in list(fg[0].items()) if b in new ])
                msg = self._make_loco_msg(dcc_id, fg[1], data)
                self.send_msg(msg)
                trace('controller', self, "setting loco %d functions %s msg %s",
                      dcc_id, ','.join([ "%d" % (f,) for f in k.intersection(new) ]) or 'none',
                      self.show_msg(msg))

    def _make_check_bits(self, msg) :
        msg.append(reduce(operator.xor, msg))
        return msg

    def ping(self) :
        msg = bytearray([ CMD_PING ])
        self.send_msg(msg)

    def show_msg(self, msg) :
        return ' '.join([ '%02x' % (m,) for m in msg])

    def listener(self, line) :
        do_next_msg = False
        if line :
            trace('controller', self, "%s received '%s'", get_time_of_day(), line)
        line = line.strip()
        now = time.time()
        deadline = self.last_xmit_time + constants.nce_response_wait_time if self.last_xmit_time else 0.0
        if line=='!' :
            if self.last_msg :
                do_next_msg = True
            else :
                self.receive_errors += 1
                log(self, 'unexpected ack')
        elif line and self.last_msg is None :
            self.receive_errors += 1
            log(self, "%s unexpected error response '%s'", get_time_of_day(), line)
        elif (line=='' or line is None) \
             and self.last_xmit_time \
             and deadline < now \
             and self.last_msg : # timeout
            trace('serial', self, '%s timeout waiting for response xmit %s now %s (%.6f) deadline %s (%.6f)', get_time_of_day(), \
                  self.last_xmit_time, now, now-self.last_xmit_time, deadline, deadline-self.last_xmit_time)
            self.timeouts += 1
            do_next_msg = True
        elif line :
            self.receive_errors += 1
            log (self, "%s error response '%s' for message '%s'", get_time_of_day(), \
                 line, self.show_msg(self.last_msg))
            do_next_msg = True
        if do_next_msg :
            with self.lock :
                self.last_msg = None
                if self.pending :
                    next = self.pending[0]
                    self._transmit(next[0])
                    if next[1] :
                        next[1]()
                    self.pending = self.pending[1:]

    def send_msg(self, msg, callback=None) :
        if self.device :
            with self.lock :
                if self.last_msg :
                    self.pending.append((msg, callback))
                else :
                    self._transmit(msg)
                    if callback :
                        callback()

    def _transmit(self, msg) :
        n = self.port.write(msg)
        log(self, "%s transmitting '%s' %d bytes", get_time_of_day(), self.show_msg(msg), n)
        self.last_msg = msg
        self.last_xmit_time = time.time()
                


