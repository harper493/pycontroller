#!/usr/bin/python
#
# simple functional tester for nce point control
#

from nce_controller import nce_controller
from usb_listener import usb_listener
from logger import logger
from dispatcher import dispatcher
from stop_server import stop_server
from sensor import sensor

import re
import sys
import time

def do_turnout(cmd, rev=None) :
    m = re.match(r'^(\d+)\s*([nrNR]?)$', cmd)
    if m :
        dcc_id = int(m.group(1))
        if 0 < dcc_id <= 255 :
            if rev is None :
                rev = m.group(2) in ('r', 'R')
            n._set_turnout(dcc_id, rev)
        else :
            raise ValueError

class loco_info(object) :
    pass

def get_loco(n) :
    try :
        return loco_infos[n]
    except KeyError :
        l = loco_info()
        l.speed = 0
        l.reverse = False
        l.opts = set()
        loco_infos[n] = l
        return l

def set_loco(nn) :
    l = get_loco(nn)
    n._set_loco(nn, l.speed, l.reverse, l.opts)

l = logger(console=True)
l._add_trace('controller')
l._add_trace('serial')

try :
    dev = sys.argv[1]
except IndexError :
    dev = None
d = dispatcher()
n = nce_controller(dev)
usb_listener.make_listeners()
for i in range(12) :
    sensor(str(i+1))
curloco = 0
loco_infos = {}

while True :
    cmd = input('command: ').strip()
    if cmd=='' :
        break
    try :
        cmd0 = cmd[0]
        rest = cmd[1:].strip()
        if cmd0=='p' :
            n.ping()
        elif cmd0=='l' :
            curloco = int(rest)
            get_loco(curloco)
        elif cmd0=='+' or cmd0=='-' :
            if len(cmd) > 1 :
                delta = int(rest)
            else :
                delta = 1
            if cmd0=='-' :
                delta = -delta
            delta *= 8
            get_loco(curloco).speed = max(0, min(127, get_loco(curloco).speed + delta))
            set_loco(curloco)
        elif cmd0=='f' :
            get_loco(curloco).reverse = False
            set_loco(curloco)
        elif cmd0=='r' :
            get_loco(curloco).reverse = True
            set_loco(curloco)
        elif cmd0=='e' :
            get_loco(curloco).speed = 0
            set_loco(curloco)
        elif cmd0=='s' :
            get_loco(curloco).speed = int(rest) if rest else 0
            set_loco(curloco)
        elif cmd0=='o' :
            undo = False
            if rest[0]=='-' or rest[0]=='+' :
                undo = rest[0]=='-'
                rest = rest[1:].strip()
            opt = int(rest)
            if undo :
                get_loco(curloco).opts.discard(opt)
            else :
                get_loco(curloco).opts.add(opt)
            set_loco(curloco)
        elif cmd0=='c' :
            t = [ '2n', '1n', '2r', '2n', '1r', '1n' ]
            for nn in list(range(3, 9)) + list(range(10, 14)) :
                t += [ '%d%s' % (nn, d) for d in ['n', 'r', 'n'] ]
            for tt in t:
                do_turnout(tt)
                time.sleep(1)
        elif cmd0=='t' :
            do_turnout(rest)
        elif cmd0=='x' :
            for i in range(10) :
                do_turnout(rest, rev=True)
                time.sleep(1)
                do_turnout(rest, rev=False)
                time.sleep(1)
        else :
            raise ValueError
    except ValueError as exc :
        print(exc)
        print('commands must be in the form <turnout><dir> e.g. 13r')

print('stopping')
stop_server.stop()
