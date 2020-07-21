controller.py                                                                                       0000755 0001750 0001750 00000000447 13673251342 012307  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   #!/usr/bin/python

#
# controller - main program
#

from parse_args import parse_args
from dispatcher import dispatcher
from load_layout import load_layout
import logger

p = parse_args()
usb_listener.make_listeners(p.exclude)
d = dispatcher(p)
logger.log_init()
load_layout(p.layout)
d.start()
                                                                                                                                                                                                                         control.py                                                                                          0000755 0001750 0001750 00000006521 13673251342 011603  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   #!/usr/bin/python
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
                                                                                                                                                                               dispatcher.py                                                                                       0000755 0001750 0001750 00000006237 13673251342 012255  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   #
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
                                                                                                                                                                                                                                                                                                                                                                 fan_section.py                                                                                      0000755 0001750 0001750 00000014251 13673251342 012412  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   #
# Representation of a turnout fan
#
# A fan is described as a semicolon-separated list of turnouts followed
# by the normal and reverse adjacencies, as follows:
#
# T1:T2/S34; T2:T3/T4; T3:S35/S36; T4:S37/S31
#

from section import section
from turnout import turnout
from logger import log
import re
from utility import *
from symbols import *

arg_table = { 'orientation' : lambda obj, dir : parse_direction(dir),
              'description' : '',
          }

class fan_section(section) :

    def __init__(self, name, **args) :
        construct(self, arg_table, args)
        section.__init__(self, name, **args)
        if self.is_leftwards() :
            self.right.set_multi_adjacency()
        else :
            self.left.set_multi_adjacency()
        self._build()
        self.selected = None
        self.sections = [ section.get(ss) for ss in self.exits.keys() ]
        self.route_set = False
        self.book_through = True
        for s in self.sections :
            s.set_adjacent(self.orientation, self)

    def is_leftwards(self) :
        return self.orientation==DIR_LEFT

    def set_route(self, _exit) :
        if not _exit.name in self.exits :
            raise ValueError("fan '%s' does not have an exit to section '%s'" \
                % (self.name, str(_exit)))
        self.route_set = False
        if self.selected != _exit :
            self.selected = _exit
            if self.is_leftwards() :
                self.right.adjacent = _exit
            else :
                self.left.adjacent = _exit
            self._log_me("set_route", "route %s", self._show_exit(self.exits[_exit.name]))
        return self.is_clear()

    def is_clear(self) :
        if not self.route_set and self.selected :
            self.route_set = and_all([ x[0].throw(x[1]) for x in self.exits[self.selected.name] ])
        return self.route_set

    #
    # _build - take the description and turn it into what we need to operate.
    #
    # We build the exits dict, which contains one entry for each section the fan leads
    # to, each of which is a list of tuples of (turnout, direction) - so to select
    # a section, we just go down the list making all those settings (see set_route).
    #
    # To do this, we keep an auxiliary list for each turnout saying which sections it
    # is relevant to. Then, when a further-out turnout references it, we know
    # which exit entry to add THIS turnout to. It's a bit complicated but it does work,
    # honest.
    #

    def _build(self) :
        self.exits = {}
        self.turnouts = {}
        turnout_exits = {}
        descriptions = [ re.match(r'^\s*(\w+)\s*:\s*(\w+)\s*/\s*(\w*)\s*$', tt) \
                         for tt in self.description.split(';') ]
            # make array of turnout:normal/thrown with optional whitespace
        for d in descriptions :
            if d is None :
                raise ValueError("fan descriptions for %s must be in the form Tx:Ty/Sz,... or similar: '%s'" % \
                    (self.name, self.description))
        progress = True
        good_values = 0
        done = {}
        while progress :
            progress = False
            for m in descriptions :
                if m in done :
                    continue
                tname, nname, rname = m.group(1), m.group(2), m.group(3)
                normal = section.get_if(nname) or turnout.get_if(nname)
                reverse = section.get_if(rname) or turnout.get_if(rname)
                if normal and reverse :
                    progress = True
                    good_values += 1
                    done[m] = None
                    t = turnout(tname, container=self)
                    self.turnouts[t.name] = t
                    turnout_exits[t.name] = []
                    for s in [normal, reverse] :
                        if isinstance(s, turnout) :
                            turnout_exits[t.name] += turnout_exits[s.name]
                            for ss in turnout_exits[s.name] :
                                self.exits[ss].append((t, s is reverse))
                        else :
                            turnout_exits[t.name].append(s.name)
                            self.exits[s.name] = [(t, s is reverse)]
        if good_values != len(descriptions) :
            raise ValueError("some sections for %s do not exist yet: '%s'" \
                % (self.name, self.description))
        log(self, "exits: %s", self._show_exits())

    def _show_exit(self, exits) :
        return ','.join([ "%s%s" % (tt[0], "R" if tt[1] else "N") \
                          for tt in exits ])

    def _show_exits(self) :
        return '; '.join([ "%s:%s" % (xn, self._show_exit(xv)) \
                                   for xn,xv in self.exits.items() ])
        
    def _get_next_section(self, sect) :
        result = None
        if self.orientation == DIR_LEFT :
            result = self.selected if sect==self.left.adjacent else self.left.adjacent
        else :
            result = self.selected if sect==self.right.adjacent else self.right.adjacent
        log(self, "_get_next_section: sect %s selected %s result %s", sect, self.selected, result)
        return result

    def make_booking_v(self) :
        if self.next_section in self.exits :
            self.set_route(self.next_section)

    def enliven_connections(self) :
        for x in self.sections :
            x.enliven_connections()

    def leave_v(self) :
        self.selected = None

    def __get_next_section(self, sect) :
        if self.is_leftwards() :
            if sect==self.left.adjacent :
                return self.selected
            else :
                return self.left.adjacent
        else :
            if sect==self.right.adjacent :
                return self.selected
            else :
                return self.right.adjacent

    def _get_unique_adjacent(self) :
        if self.orientation==DIR_LEFT :
            return self.left.adjacent
        else :
            return self.right.adjacent

    def _set_direction(self, val) :
        self.orientation = parse_direction(val)

    def _log_extra(self) :
        return "selected " + str(self.selected)

    def _dump_extra(self) :
        return "exits=" + self._show_exits()

section.enroll_type('fan', fan_section)
    
                                                                                                                                                                                                                                                                                                                                                       jmri_controller.py                                                                                  0000755 0001750 0001750 00000001034 13673251342 013321  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   #
# jmri_controller - specialization of controller to work via JMRI
#

from layout_controller import layout_controller
import socket

class jmri_controller(layout_controller) :

    def __init__(self, address, port) :
        self.address, self.port = address, port
        self.socket = None
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        layout_controller.__init__(self)

    def _set_loco(dcc_id, speed, reverse, options) :
        pass

    def set_turnout(dcc_id, thrown) :
        pass
        

    
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    jmri-throttle-test.py                                                                               0000664 0001750 0001750 00000001105 13674007101 013665  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   import requests
import sys

HOST = '192.168.1.140'
PORT = 12080

def  make_url(url):
    url = f'ws://{HOST}:{PORT}/json/{url}'
    print(url)
    return url

def do_http(verb, url, *args):
    jargs = { args[i]:args[i+1] for i in range(0, len(args), 2)}
    print(str(jargs))
    r = requests.request(verb, make_url(url), json=jargs)
    print('Post:', r.status_code, r.text)

def get(url):
    r = requests.get(make_url(url))
    print(r.status_code, r.text)

verb = sys.argv[1]
if verb=='get':
    get(sys.argv[2])
else:
    do_http(sys.argv[1], sys.argv[2], *sys.argv[3:])




                                                                                                                                                                                                                                                                                                                                                                                                                                                           layout_controller.py                                                                                0000755 0001750 0001750 00000001076 13673251342 013703  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   #
# layout_controller - static class for communicating with DCC controller
#

class layout_controller(object) :

    the_controller = None

    def __init__(self) :
        layout_controller.the_controller = self
        self.my_class = 'layout_controller'

    @staticmethod
    def set_loco(dcc_id, speed, reverse, options) :
        layout_controller.the_controller._set_loco(dcc_id, speed, reverse, options)

    @staticmethod
    def set_turnout(dcc_id, thrown, callback=None) :
        layout_controller.the_controller._set_turnout(dcc_id, thrown, callback=callback)

                                                                                                                                                                                                                                                                                                                                                                                                                                                                  load_layout.py                                                                                      0000755 0001750 0001750 00000004411 13673251342 012433  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   #
# load_layout - read the layout description file and create the corresponding objects
#

import re
from section import section
from locomotive import locomotive
from train import train

types = { 'sections' : section.factory, \
          'locos' : locomotive, \
          'trains' : train, \
          'positions' : (lambda n,**a : _load_position(n, **a)) }

def load_layout(f) :
    item_class = None
    lineno = 0
    line = ''
    for l in f:
        line += l.strip()
        if len(line)==0 :
            continue
        if line[-1]=='\\' :
            line = line[:-1]
            continue
        lineno += 1
        error = None
        m = re.match(r'^\s*\[(.*)\]\s*|\s*(#).|\s*(.*?)\s*:\s*(.*)\s*$', line)
        if m :
            if m.group(1) :
                item_class = m.group(1).strip()
                if item_class not in types :
                    error = "unrecognised item class '%s'" % (item_class,)
                    item_class = None
            elif not m.group(2) : # not a comment
                attr_str = [ s.strip() for s in m.group(4).split(',') ]
                attrs = {}
                for a in attr_str :
                    aa = a.split('=')
                    if len(aa)==1 :
                        attrs[aa[0].strip()] = "True"
                    elif len(aa)==2 :
                        attrs[aa[0].strip()] = aa[1].strip()
                    else :
                        error = "incorrect syntax for attribute/value pair %s" % (a,)
                if not error :
                    try :
                        (types[item_class])(m.group(3), **attrs)
                    except ValueError as err :
                        error = err
        else :
            error = "syntax error"
        if error :
            print("error in line %d: %s\n    %s" % (lineno, error, line))
        line = ''
    section.visit_all(section.enliven_connections)

def _load_position(name, **attrs) :
    t = train.get(name)
    a0 = list(attrs.keys())[0]
    m = re.match(r'^(\w+)/(\d*)([LR])$', a0)
    if m :
        sect = section.get(m.group(1))
        offset = float(m.group(2)) if m.group(2) else -1
        left = m.group(3)=='L'
        sect.position_train(t, left, offset)
    else :
        raise ValueError("'%s' is not a valid train position" % (a0,))
                                                                                                                                                                                                                                                       locomotive.py                                                                                       0000755 0001750 0001750 00000006670 13673251342 012310  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   #
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

                                                                        logger.py                                                                                           0000755 0001750 0001750 00000004130 13705462243 011374  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   # logger.py
#
# simple file logger

from time import localtime, strftime
from simtime import simtime
from utility import *
from datetime import datetime

logfile = None

LOG_PATH = './log/'
LOG_FILENAME = 'pycontroller'
LOG_EXT = '.log'

class logger(object) :

    the_logger = None
    traces = set()

    def __init__(self, filename=None, console=False, trace=None) :
        if filename is None :
            filename = f'{LOG_PATH}{LOG_FILENAME}_{datetime.now().strftime("%Y%m%dT%H%M%S")}{LOG_EXT}'
        try :
            self.logfile = open(filename, 'w')
        except IOError :
            print("failed to open log file")
        self.console = console
        self.logfile.write("%s opening log '%s'\n" % (logger._get_time(), filename))
        for t in trace or [] :
            self._add_trace(t)
        logger.the_logger = self

    def _log(self, obj, message, *args) :
        if self.logfile :
            text = message % args
            try :
                extra = obj._log_extra()
            except AttributeError :
                extra = ''
            msg = "%8s %20s.%-15s %s %s" % \
                  (simtime.time(), obj.my_class, obj.name, text, extra)
            self.logfile.write(msg+'\n')
            self.logfile.flush()
            if self.console :
                print(msg)

    def _trace(self, tr, obj, message, *args) :
        for t in logger.traces :
            if tr.startswith(t) :
                self._log(obj, message, *args)
                break

    def _add_trace(self, t) :
        if t :
            logger.traces.add(t)

    @staticmethod
    def log(obj, message, *args) :
        logger.the_logger._log(obj, message, *args)

    @staticmethod
    def trace(tr, obj, message, *args) :
        logger.the_logger._trace(tr, obj, message, *args)

    @staticmethod
    def _get_time() :
         return get_time_of_day()

    @staticmethod
    def add_trace(t) :
        logger.the_logger._add_trace(t)

def log(obj, message, *args) :
    logger.the_logger._log(obj, message, *args)

def trace(tr, obj, message, *args) :
    logger.the_logger._trace(tr, obj, message, *args)
                                                                                                                                                                                                                                                                                                                                                                                                                                        loop_section.py                                                                                     0000755 0001750 0001750 00000004511 13673251343 012616  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   #
# Representation of a reverse loop with no sidings
#

from section import *
from turnout import turnout
from sensor import sensor
from logger import log
from utility import *
from symbols import *

arg_table = { 'prefer_thrown' : False,
              'prefer_normal' : False,
              'turnout' : REQUIRED,
              'half_way' : '0.5',
              }

class loop_section(section) :

    def __init__(self, name, **args) :
        construct(self, arg_table, args)
        section.__init__(self, name, **args)
        if not isinstance(self.turnout, turnout) :
            self.turnout = turnout(self.turnout, container=self, \
                                   normal_section=self, thrown_section=self)
        try :
            self.half_way = float(self.half_way) * self.length
            self.half_way_sensor = None
        except ValueError :
            self.half_way = None
            self.half_way_sensor = sensor.get(self.half_way)
            self.half_way_sensor.listen(self.half_way_listen)
        self.reached_half_way = 'no'
        self.hold = True
        self.book_through = False

    def enter(self, from_, offset=0) :
        if not self.is_occupied() :
            self.reached_half_way = 'no'
            self.hold = True
            self.enter_base(from_, offset)

    def half_way_listen(self) :
        self.reached_half_way = 'yes'

    def _can_cruise(self) :
        return self.reached_half_way=='no'

    def enliven_connections_v(self) :
        self.enliven_connections_base()

    def review_position(self) :
        if self.half_way :
            if self.position > self.half_way >= self.prev_position :
                self.reached_half_way = 'yes'
        if self.reached_half_way == 'yes' :
            self.leave_previous()
            self.reached_half_way = 'done'
            self.hold = False
            prev_state = self.state
            self.state = SECTION_OCCUPIED
            self.direction = reverse_direction(self.direction)
            self._log_me("half way", "old_state %s", self.show_state(prev_state))
        self.review_position_base()
        
    def prepare(self, sect) :
        self.prepare_base(sect)
        if prefer_thrown :
            self.turnout.throw(True)
        elif prefer_normal :
            self.turnout.throw(False)

section.enroll_type('loop', loop_section)
    

                
                                                                                                                                                                                       manager.py                                                                                          0000644 0001750 0001750 00000003745 13705613744 011543  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   #
# Base class for manager objects, i.e. ones that supervise traffic
# across multiple sections
#

from logger import log
from utility import *
import constants
from symbols import *
from section import section

class manager(object) :

    arg_table = { 'sections' : REQUIRED,
                  }

    def __init__(self, name, **args) :
        self.name = name
        self.my_class = 'manager'
        construct(self, manager.arg_table, args, check=True)
        self.my_sections = [ section.get(n) for n in self.sections.split(';') ]

    def can_book(self, to_sect, from_sect, tr, dir, urgent) :
        """
        Delegated can_book function. Return (True, result) if all required
        action has been taken, 'result' is whether the booking can be
        taken. Return (False, xxx) to re-delegate back to the section
        object.
        """
        return (False, False)

    def book(self, to_sect, from_sect, tr, dir) :
        """
        Delegated book function. Return (True, result) if all required action has
        been taken, (False, xxx) to allow the section to take care of its own booking.
        'result' says whether thebooking was successful.
        """
        return (False, False)

    def dispatch(self, sect) :
        """
        Delegated dispatch function. Return True if all required action
        has been taken, False to allow the section to take care of it.
        """
        return False

    def get_occupancy(self, sect) :
        """
        Delegated get_occupancy function. By default, returns the
        section's value. Used for shuffle_section and other to
        return the total number of trains in the managed collection.
        """
        return sect._get_occupancy()

    def make_booking(self, sect) :
        """
        Called when a booking is being made for managed section sect.
        """
        return

    def _log_me(self, why, extra=None, *args) :
        x = (extra % args) if extra else ''
        log(self, "%s: %s", \
            why, x)
                           nce_controller.py                                                                                   0000755 0001750 0001750 00000015110 13673251343 013126  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   #controller for NCE systemdummy controller when running simulated
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
                


                                                                                                                                                                                                                                                                                                                                                                                                                                                        nce_test.py                                                                                         0000755 0001750 0001750 00000001072 13673251343 011724  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   from nce_controller import nce_controller
from logger import logger
from stop_server import stop_server

l = logger(console=True)
l._add_trace('controller')

n = nce_controller('')

n._set_turnout(3, 1)
n._set_turnout(1, 0)
n._set_turnout(511, 0)
n._set_loco(1, 0, False)
n._set_loco(1, 127, False)
n._set_loco(1, 127, True)
n._set_loco(15, 63, False)
n._set_loco(15, 63, False, [0])
n._set_loco(15, 63, False, [0,1])
n._set_loco(15, 63, False, [1])
n._set_loco(15, 63, False, [1,2,8])
n._set_loco(15, 63, False, [2,8,12])
n._set_loco(15, 63, False)

stop_server.stop()
                                                                                                                                                                                                                                                                                                                                                                                                                                                                      parse_args.py                                                                                       0000755 0001750 0001750 00000003240 13673251343 012245  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   import sys
import os
import re
import argparse
import constants

class parse_args(object) :

    def __init__(self) :
        p = argparse.ArgumentParser()
        p.add_argument('args', nargs='*')
        p.add_argument('-n', '--nce', \
                       help='usb device for communicating with NCE controller')
        p.add_argument('-s', '--simulate', action='store_true', default=False, \
                       help='simulate without layout')
        p.add_argument('-g', '--log_to_console', action='store_true', default=False, \
                       help='send log output also to console')
        p.add_argument('-t', '--time', type=float, default=constants.default_time_dilution,
                       help='time dilution factor for simulation')
        p.add_argument('-x', '--trace', type=str, default='', \
                       help='list of trace points to log')
        p.add_argument('-l', '--layout', type=argparse.FileType('r'), default='layout.txt', \
                       help='file to load layout and trains')
        p.add_argument('-c', '--constants', type=argparse.FileType('r'), \
                       help='file to load constant overrides')
        p.add_argument('-p', '--log_periodic', action='store_true', default=False, \
                       help='log section and train status every 10 seconds')
        a = p.parse_args()
        self.additional_args = a.args
        self.nce = a.nce
        self.simulate = a.simulate
        self.time_dilution = a.time
        self.constants_file = a.constants
        self.layout = a.layout
        self.log_to_console = a.log_to_console
        self.trace = a.trace
        self.log_periodic = a.log_periodic

                                                                                                                                                                                                                                                                                                                                                                pubsub.py                                                                                           0000755 0001750 0001750 00000001352 13673251343 011421  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   #
# simple publish-subscribe class
#

class pubsub(object) :

    def __init__(self) :
        self.listeners = []
        self.listener_index = 1

    def listen(self, fn, *args) :
        index = self.listener_index
        self.listener_index += 1
        self.listeners.append((index, fn, args))
        return index

    def unlisten(self, index) :
        for i in range(len(self.listeners)) :
            if self.listeners[i[0]]==index :
                self.listeners = self.listeners[:i-1] + self.listeners[i+1:]
                return True
        return False

    def signal(self, event=None) :
        for l in self.listeners :
            if event :
                l[1](event, *l[2])
            else :
                l[1](*l[2])
                                                                                                                                                                                                                                                                                      pycontroller.py                                                                                     0000755 0001750 0001750 00000002565 13673251343 012664  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   #!/usr/bin/python

from dispatcher import dispatcher
from usb_listener import usb_listener
from parse_args import parse_args
from sim_controller import sim_controller
from nce_controller import nce_controller
from load_layout import load_layout
from simple_section import simple_section
from yard_fan_section import yard_fan_section
from shuffle_manager import shuffle_manager
from loop_section import loop_section
from logger import log, logger
from section import section
from stop_server import stop_server
import constants
#import positions
import os
import sys
import signal
import time

JMRI_PORT = 12345

def signal_term_handler(signal, frame):
    print('got SIGTERM')
    stop_server.stop()
    time.sleep(1)

args = parse_args()
logger(console=args.log_to_console, trace=args.trace.split(','))
disp = dispatcher(args)
constants.load_string(args.additional_args)
if args.constants_file :
    constants.load_file(args.constants_file)
if args.log_periodic :
    constants.log_section_status = constants.log_train_status = True
if args.simulate :
    sim_controller()
else :
    nce = nce_controller(args.nce)
    usb_listener.make_listeners(args.nce)
    while not nce.is_connected() or not usb_listener.all_connected() :
        pass
load_layout(args.layout)
print(section.dump_all())
#positions.load()

signal.signal(signal.SIGTERM, signal_term_handler)

disp.start()

stop_server.stop()
                                                                                                                                           section_end.py                                                                                      0000755 0001750 0001750 00000004552 13673251343 012420  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   #
# section_end - one end of a section (left or right)
#

from logger import log
from sensor import sensor
from utility import *
from symbols import *
import constants

arg_table = { 'adjacent' : None,
              'sensor' : None,
              'sensor_offset' : 0,
}

class section_end(object) :

    def __init__(self, owner, direction, explicit_args=None, **args) :
        self.my_class = 'section_end'
        self.owner, self.direction = owner, direction
        self.delegate = None
        args = explicit_args or args
        self.dir_string = 'left' if self.direction==DIR_LEFT else 'right'
        construct(self, arg_table, args, prefix=self.dir_string+'_')
        self.sensor_offset = self.sensor_offset or constants.default_sensor_offset \
                             if self.sensor else 0
        self.multi_adjacency = False
        if self.sensor :
            self.sensor = sensor.make_sensor_for(self.sensor, self)

    def enliven_connections(self) :
        if isinstance(self.adjacent, str) :
            self.adjacent = self.owner.enliven_m(self.adjacent)
            if self.adjacent :
                self.adjacent.enliven_connections()
        if self.adjacent and not self.delegate :
            opposite_end = self.adjacent.get_opposite_end(self)
            if opposite_end and not opposite_end.multi_adjacency :
                if opposite_end.adjacent is None :
                    opposite_end.adjacent = self.owner
                else :
                    if opposite_end.adjacent != self.owner :
                        raise ValueError("incorrect adjacency, section %s connected to %s which is connected to %s" % \
                            (str(self.owner), str(opposite_end.owner), str(opposite_end.adjacent)))

    def is_left(self) :
        return self.direction==DIR_LEFT

    def is_right(self) :
        return self.direction==DIR_RIGHT

    def set_multi_adjacency(self) :
        self.multi_adjacency = True
        
    def delegate_to(self, delegate) :
        self.delegate = delegate
        delegate.adjacent = self.adjacent

    def __str__(self) :
        return self.owner.name + '.' + self.dir_string

    def show_adjacent(self) :
        if self.adjacent :
            if isinstance(self.adjacent, str) :
                return self.adjacent
            else :
                return self.adjacent.name
        else :
            return "<None>"
                                                                                                                                                      section.py                                                                                          0000755 0001750 0001750 00000045546 13705621360 011576  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   from logger import log
from utility import *
from section_end import section_end
from dispatcher import dispatcher
from train import train
from simtime import simtime
from symbols import *
import random
import constants
import re
import traceback

STATUS_INTERVAL = 10

# section states

class section(object) :

    """
    Base class for all kinds of track section

    Supports the follwing operations:
    -- book - book a section for a given train and previous section
    -- prepare - set up the route for the imminent arrival of the train
    -- enter - the train has arrived in the section
    -- leave - the train has definitely left the section
    """

    arg_table = { 'container' : None,
                  'max_speed' : constants.default_max_speed,
                  'radius' : None,
                  'length' : 0,
                  'exclude' : [],
                  'template' : None,
                  'hold' : False,
                  'terminus' : False,
                  'blocked' : False,
                  'book_through' : False,
                  'through_prob' : constants.section_through_prob,
              }

    sections = {}
    types = {}
    first = True

    def __init__(self, name, **args) :
        self.my_class = 'section'
        self.name = name
        self.left = section_end(self, DIR_LEFT, explicit_args=args)
        self.right = section_end(self, DIR_RIGHT, explicit_args=args)
        construct(self, section.arg_table, args, check=True)
        if self.template :
            construct(self, section.arg_table, self.template.__dict__)
        self.my_train = None
        self.my_state = SECTION_EMPTY
        self.next_section = None
        self.prev_section = None
        self.manager = None
        self.state = SECTION_BLOCKED if self.blocked else SECTION_EMPTY
        self.direction = DIR_NONE
        self.position = 0
        self.prev_position = 0
        self.try_next_sec = None
        self.terminating = False
        if self.terminus or self.hold :
            self.book_through = False
        self.stop_position = None
        self.set_sensor_listen(self.left)
        self.set_sensor_listen(self.right)
        section.sections[name] = self
        dispatcher.add_tick_client(self.tick)
        if section.first :
            section.first = False
            section.init_class()

    @staticmethod
    def enroll_type(name, factory) :
        section.types[name] = factory

    @staticmethod
    def init_class() :
        dispatcher.add_ten_second_client(section.status_reporter)

    @staticmethod
    def factory(name, **args) :
        try :
            my_type = args['type']
            del args['type']
        except KeyError :
            my_type = 'simple'
        try :
            fn = section.types[my_type]
        except KeyError :
            raise ValueError("unknown section type '%s'" % (my_type,))
        (fn)(name, **args)

    def is_booked(self) :
        return self.state in (SECTION_BOOKED, SECTION_CLEAR)

    def is_empty(self) :
        return self.state==SECTION_EMPTY

    def is_clear(self) :
        return self.state==SECTION_CLEAR

    def is_clear_for(self, t) :
        return self.state==SECTION_CLEAR \
            or (self.state>=SECTION_OCCUPIED and self.my_train==t)

    def is_leftbound(self) :
        return self.direction==DIR_LEFT

    def is_rightbound(self) :
        return self.direction==DIR_RIGHT

    def is_unoccupied(self) :
        return self.state < SECTION_OCCUPIED 

    def is_occupied(self) :
        return not self.is_unoccupied()

    def is_stopping(self) :
        return self.state==SECTION_STOPPING

    def is_continuing(self) :
        return self.state==SECTION_CONTINUING

    def is_same_direction(self, other) :
        return self.direction==other.direction

    def is_stopped(self) :
        return self.state==SECTION_STOPPED

    def get_occupancy(self) :
        if self.manager :
            return self.manager.get_occupancy(self)
        else :
            return 1 if self.is_occupied() else 0

    def get_left(self) :
        return self.left

    def get_right(self) :
        return self.right

    def is_head(self) :
        return self.is_occupied() and \
            (self.next_section is None or not self.next_section.is_occupied())

    def set_manager(self, mgr) :
        self.manager = mgr

    def get_my_train(self, dir) :
        return self.my_train

    def has_available_train(self, dir) :
        return self.is_occupied() \
                and self.my_train.is_available() \
                and (self.is_leftbound()==(dir==DIR_LEFT) \
                         or self.my_train.is_reversible())

    def set_terminating(self) :
        if not self.terminating :
            self.terminating = True
            self._log_me("terminating")

    def get_departure_end(self) :
        return self.left if self.is_leftbound() else self.right

    def get_arrival_end(self) :
        return self.right if self.is_leftbound() else self.left

    def book(self, sect, tr, dir) :
        done = result = False
        if self.manager :
            done, result = self.manager.book(self, sect, tr, dir)
        if done :
            if result :
                self.try_next_sect = self._get_next_section(sect)
            return result
        else :
            return self._book(sect, tr, dir)

    def _book(self, sect, tr, dir) :
        return self.book_base(sect, tr, dir)

    def book_base(self, sect, tr, dir) :
        result = False
        self.try_next_sec = self._get_next_section(sect)
        if self.can_book_through(sect, tr, dir) :
            self.make_booking(sect, tr, dir)
            result = True
        return result

    def can_book(self, sect, tr, dir, urgent=False) :
        done = result = False
        if self.manager :
            done, result = self.manager.can_book(self, sect, tr, dir, urgent)
        if done :
            return result
        else :
            return self._can_book(sect, tr, dir, urgent)

    def _can_book(self, sect, tr, dir, urgent) :
        return self.is_empty() and self.is_bookable(tr)

    def can_book_through(self, sect, tr, dir, urgent=False) :
        cb = self.can_book(sect, tr, dir, urgent)
        cbt = False
        assert(self.try_next_sec != self)
        if not self.hold and self.try_next_sec :
            self._log_me("can_book_through", "try_next %s", self.try_next_sec)
            cbt = self.try_next_sec.can_book_through(self, tr, dir)
        result = cb and (cbt or not self.book_through)
        return result

    def extend_booking(self) :
        if not self.is_empty() \
           and not self.hold \
           and not self.next_section \
           and self.my_train and self.my_train.is_active() :
            return self.force_extend_booking()
        else :
            return False

    def force_extend_booking(self) :
        result = False
        if self.try_next_sec is None :
            if self.direction==DIR_LEFT:
                self.try_next_sec = self.left.adjacent
            else :
                assert(self.direction==DIR_RIGHT)
                self.try_next_sec = self.right.adjacent
        if self.try_next_sec and self.try_next_sec.is_empty() :
            assert(isinstance(self.my_train, train))
            result = self.try_next_sec.book(self, self.my_train, self.direction)
            if result :
                self.next_section = self.try_next_sec
                self.try_next_sec = None
                self._log_me("extended")
        return result

    def _get_next_section(self, sect) :
        return self.right.adjacent if sect==self.left.adjacent else self.left.adjacent

    def _get_connected_end(self, sect) :
        for e in [ self.left, self.right ] :
            if sect==e.adjacent :
                return e
        return None

    def is_bookable(self, tr) :
        return tr.name not in self.exclude and \
            (self.radius is None or tr.min_radius <= self.radius)

    def make_booking(self, sect, tr, dir) :
        assert(isinstance(tr, train))
        self.my_train = tr
        self.prev_section = sect
        self.state = SECTION_BOOKED
        self.direction = dir
        self.make_booking_v()
        self._test_clear()
        self._log_me("book")

    def _test_clear(self) :
        if self.is_booked() :
            self.state = SECTION_CLEAR

    def make_booking_v(self) :
        pass

    def prepare(self, sect) :
        self.prepare_base()

    def prepare_base(self) :
        self._log_me("prepare")

    def enter(self, from_, offset=0, sensor=False) :
        if not self.is_occupied() :
            self.enter_base(from_, offset, sensor=sensor)

    def enter_base(self, from_, offset=0, sensor=False) :
        entry = self.left if self.is_rightbound() else self.right
        exit_ = self.right if self.is_rightbound() else self.left
        if sensor or (entry and entry.sensor is None) or dispatcher.is_simulated() :
            if self.is_unoccupied() :
                self.state = SECTION_OCCUPIED
                self.position = offset
                self.stop_position = self.length - exit_.sensor_offset
                prev_head = self.my_train.head
                while True :
                    next = prev_head.next_section
                    prev_head.depart()
                    if next==self :
                        break
                    prev_head = next
                    next.enter(self)
                self.my_train.set_head(self)
                self.prev_section.unhead()
                self.review_progress()
                self._log_me("enter")

    def unhead(self) :
        self.state = SECTION_LEAVING

    def review_progress(self) :
        if self.state==SECTION_STOPPING or self.state==SECTION_OCCUPIED :
            if self.terminating :
                self.state = self.TERMINATING
            elif self.next_section \
               and self.next_section.is_clear_for(self.my_train) \
               and not self.terminating :
                self.state = SECTION_CONTINUING
            else :
                self.state = SECTION_STOPPING

    def set_offset(self, offset) :
        self.position = offset

    def leave(self) :
        self.leave_base()

    def leave_base(self) :
        if self.prev_section :
            self.prev_section.leave()
        self.my_train.set_tail(self.next_section)
        self.state = SECTION_EMPTY
        self.direction = DIR_NONE
        self.my_train = None
        self.prev_section = None
        self.next_section = None
        self.leave_v()
        self._log_me("leave")

    def leave_v(self) :
        pass

    def leave_previous(self) :
        if self.prev_section :
            self.prev_section.leave()
            self.prev_section = None
            self.pre_booked_section = None

    def dispatch(self) :
        if self.manager and self.manager.dispatch(self) :
            return True
        if self.is_booked() \
           and not self.next_section \
           and random.random() < self.through_prob :
            self.force_extend_booking()

    def entry_sensor(self, end) :
        if self.prev_section :
            if self.prev_section==end.adjacent :
                self.enter(self, end.sensor_offset, sensor=True)

    def departure_sensor(self, end) :
        if self.my_train and self.my_train.is_active() :
            self.depart()

    def depart(self) :
        if self.state != SECTION_LEAVING :
            end = self.get_departure_end()
            self._log_me("departure sensor", "end %s", end)
            if self.length > self.my_train.get_length() * constants.train_length_fudge :
                self.leave_previous()
            if self.state==SECTION_STOPPING :
                if self.terminus :
                    self.state = SECTION_TERMINATED
                    self.terminate_train()
                else :
                    self.state = SECTION_STOPPED
            elif self.state==SECTION_TERMINATING :
                self.state = SECTION_TERMINATED
            else :
                self.state = SECTION_LEAVING
                self.next_section.enter(self, -end.sensor_offset)

    def set_train_speed(self, speed=None, cruise=False, slowing=False, stopping=False) :
        if self.state==SECTION_STOPPING or self.state==SECTION_TERMINATING :
            if self.position > self.stop_position - constants.stopping_margin :
                self.my_train.set_speed(stopping=True)
            else :
                self.my_train.set_speed(slowing=True)
        elif self.state==SECTION_CONTINUING :
            self.my_train.set_speed(cruise=True)
        elif self.my_state==SECTION_STARTING :
            self.my_train.set_speed(slowing=True)
        elif self.my_state==SECTION_STOPPED or self.my_state==SECTION_TERMINATED :
            self.my_train.set_speed(0)

    def terminate_train(self, do_wait=True) :
        self.terminate_train_base(do_wait)

    def terminate_train_base(self, do_wait) :
        self.state = SECTION_TERMINATED
        self.my_train.deactivate(do_wait=do_wait)

    def tick(self, duration) :
        self.tick_base(duration)

    def tick_base(self, duration) :
        self.extend_booking()
        self.update_position(duration)
        self.review_progress()
        self.set_train_speed()
        self.dispatch()

    def set_position(self, pos) :
        self.position = pos

    def update_position(self, duration) :
        self.prev_position = self.position
        if self.my_train and self.is_occupied() :
            speed = self.my_train.get_actual_speed()
            if speed > 0 :
                self.position += speed * duration * constants.scale_factor * \
                                 constants.mph2fps * constants.speed_fudge
                if self.position > self.length and self.next_section :
                    self.next_section.enter(self)
            self.review_position()

    def review_position(self) :
        self.review_position_base()

    def review_position_base(self) :
        if self.my_train :
            entry_dist = exit_dist = None
            if self.is_rightbound() :
                entry = self.left
                exit_ = self.right
            else :
                entry = self.right
                exit_ = self.left
            entry_dist = entry.sensor_offset
            exit_dist = self.length - exit_.sensor_offset
            if entry.sensor :
                if self.position >= entry_dist > self.prev_position  :
                    dispatcher.fake_sensor(entry.sensor)
            if exit_.sensor :
                if self.position >= exit_dist > self.prev_position :
                    dispatcher.fake_sensor(exit_.sensor)
            elif self.position >= self.length > self.prev_position :
                self.departure_sensor(exit_)

    def activate(self) :
        pass

    def _can_cruise(self) :
        return False

    def enliven_connections(self) :
        self.enliven_connections_v()

    def enliven_connections_v(self) :
        self.enliven_connections_base()

    def enliven_connections_base(self) :
        self.left.enliven_connections()
        self.right.enliven_connections()

    def get_opposite_end(self, adjacent_end) :
        if adjacent_end.is_left() :
            result = self.right
        else :
            result = self.left
        return result

    def set_adjacent(self, dir, sect) :
        if dir==DIR_LEFT :
            self.left.adjacent = sect
        else :
            self.right.adjacent = sect

    def set_sensor_listen(self, end) :
        if end.sensor:
            end.sensor.listen(self.sensor_listen, end)

    def sensor_listen(self, end) :
        self._log_me("sensor", "sensor %s pos %.1f", end.sensor.name, self.length-end.sensor_offset)
        if not dispatcher.is_simulated() :
            self.set_position(end.sensor_offset)
        if end==self.get_arrival_end() :
            self.entry_sensor(end)
        else :
            self.departure_sensor(end)

    def set_container(self, cont) :
        self.container = cont

    def get_top_container(self) :
        return self.container.get_top_container() if self.container else self

    @staticmethod
    def enliven(section_name) :
        return section.get(section_name) if isinstance(section_name, str) else section_name

    def enliven_m(self, section_name) :
        return section.enliven(section_name)

    @staticmethod
    def get(name) :
        try :
            return section.sections[name]
        except KeyError :
            raise KeyError("section '%s' does not exist" % (name,))

    @staticmethod
    def get_if(name) :
        try :
            return section.sections[name]
        except KeyError :
            return None

    @staticmethod
    def visit_all(fn) :
        return [ fn(section.sections[k]) for k in sorted(section.sections.keys()) ]

    @staticmethod
    def dump_all() :
        return '\n'.join(section.visit_all(section.dump))

    def _make_dcc_id(self) :
        if self.dcc_id is None :
            self.dcc_id = make_dcc_id(self.name)

    def __str__(self) :
        return self.name

    def show_state(self, value=None) :
        if value is None :
            value = self.state
        return select(value,
                      SECTION_EMPTY, "EMPTY",
                      SECTION_BLOCKED, "BLOCKED",
                      SECTION_BOOKED, "BOOKED",
                      SECTION_CLEAR, "CLEAR",
                      SECTION_OCCUPIED, "OCC",
                      SECTION_STOPPING, "STOPPING",
                      SECTION_CONTINUING, "CONT",
                      SECTION_STARTING, "START",
                      SECTION_STOPPED, "STOPPED",
                      SECTION_LEAVING, "LEAVE",
                      SECTION_TERMINATING, "TERM",
                      SECTION_TERMINATED, "TERMED",
                      "???")

    def show_dir(self, value=None) :
        if value is None :
            value = self.direction
        return select(value,
                      DIR_NONE, "NONE",
                      DIR_LEFT, "LEFT",
                      DIR_RIGHT, "RIGHT",
                      "???")

    def _log_me(self, why, extra=None, *args) :
        x = ''
        if extra :
            x = extra % args
        log(self, "%s: next %s try %s prev %s dir %s state %s train '%s' %s%s pos %.1f %s", \
            why, self.next_section, self.try_next_sec, self.prev_section, self.show_dir(), \
            self.show_state(), self.my_train, \
            "H" if self.my_train and self.my_train.head==self else "", \
            "T" if self.my_train and self.my_train.tail==self else "", \
            self.position, x)

    def _log_extra(self) :
        return ''

    def dump(self) :
        return "%s left=%s right=%s cont=%s %s" % \
            (self.name,
             self.left.show_adjacent(),
             self.right.show_adjacent(),
             self.container.name if self.container else "<None>",
             self._dump_extra())

    def _dump_extra(self) :
        return ''

    def report_status(self) :
        self._log_me("status")

    @staticmethod
    def status_reporter(x) :
        if constants.log_section_status :
            section.visit_all(section.report_status)

                                                                                                                                                          sensor_listener.py                                                                                  0000755 0001750 0001750 00000004325 13673251343 013342  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   from dispatcher import dispatcher
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

       
                                                                                                                                                                                                                                                                                                           sensor.py                                                                                           0000755 0001750 0001750 00000003472 13673251343 011437  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   from dispatcher import dispatcher
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

                                                                                                                                                                                                      serial_port.py                                                                                      0000755 0001750 0001750 00000005466 13705143371 012453  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   #
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
                    
                                                                                                                                                                                                          shuffle_manager.py                                                                                  0000644 0001750 0001750 00000007165 13705613722 013253  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   #
# Manager for "shuffle section"
#

from manager import manager
from section import section
from symbols import *
from utility import *
from logger import log
import constants
import re

arg_table = { }

class shuffle_manager(manager) :

    def __init__(self, name, **args) :
        construct(self, arg_table, args)
        manager.__init__(self, name, **args)
        self.my_class = 'shuffle_manager'
        self.direction = DIR_NONE
        self._build()
        for s in self.my_sections :
            s.set_manager(self)

    def can_book(self, to_sect, from_sect, tr, dir, urgent) :
        result = False
        entry = self._get_entry_for(from_sect)
        if not entry.is_empty() :
            return (True, False)
        sections = self._get_sections_from(from_sect)
        for s in sections :
            if s.is_occupied() :
                if from_sect.is_leftbound()==s.is_leftbound() :
                    result = True
                break
        else :                  # all sections are empty
            result = True
        return (True, result)

    def make_booking(self, sect) :
        self.direction = sect.direction
        self._set_hold()

    def position_train(self, sect) :
        if self.direction==DIR_NONE :
            self.direction = sect.direction
        elif self.direction!=sect.direction :
            raise ValueError("inconsistent directions for '%s' and '%'s" % (self, sect))
        self._set_hold()

    def dispatch(self, sect) :
        sections = self._get_ordered_sections()
        for s in reversed([s for s in sections][1:]) :
            if s.is_occupied() :
                s.force_extend_booking()

    def _build(self) :
        self.my_sections = [ section.get(s.strip()) for s in self.sections.split(';') ]
        prev = None
        for s in self.my_sections :
            s.container = self
            s.book_through = False
            if prev :
                prev.set_adjacent(DIR_RIGHT, s)
                s.set_adjacent(DIR_LEFT, prev)
            prev = s
        self.my_sections[0].set_adjacent(DIR_LEFT, self._left_adjacent())
        self.my_sections[-1].set_adjacent(DIR_RIGHT, self._right_adjacent())

    def _set_hold(self) :
        for s in self.my_sections :
            s.hold = False
        self._get_exit_for_dir().hold = True
                
    def get_occupancy(self, sect) :
        return sum([ s._get_occupancy() for s in self.my_sections if s.is_head()])

    def _get_entry_for(self, from_sect) :
        if from_sect is self._left_adjacent() :
            return self.my_sections[0]
        else :
            return self.my_sections[-1]

    def _get_exit_for(self, from_sect) :
        if from_sect is self._left_adjacent() :
            return self.my_sections[-1]
        else :
            return self.my_sections[0]

    def _get_exit_for_dir(self) :
        if self.direction==DIR_LEFT :
            return self.my_sections[0]
        elif self.direction==DIR_RIGHT :
            return self.my_sections[-1]
        else :
            return None

    def _get_sections_from(self, from_sect) :
        if from_sect is self._left_adjacent() :
            return self.my_sections
        else :
            return reversed(self.my_sections)

    def _get_ordered_sections(self) :
        if self.direction==DIR_LEFT :
            return self.my_sections
        else :
            return reversed(self.my_sections)

    def _left_adjacent(self) :
        return self.my_sections[0].left.adjacent

    def _right_adjacent(self) :
        return self.my_sections[-1].right.adjacent
        
    def __str__(self) :
        return self.name

section.enroll_type('shuffle', shuffle_manager)
                                                                                                                                                                                                                                                                                                                                                                                                           shuffle_section.py                                                                                  0000755 0001750 0001750 00000013703 13705614116 013301  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   #
# Representation of a section that can hold more than one train lined
# up behind one another
#
# The basic operation is that trains are shuffled up towards one end
# end as they arrive and as others leave.
#
# There's a wrinkle that an either-way train (e.g. railcar) can
# be kept at its arrival end and dispatched in either direction.
#
# At construction it must be given a comma-separated list of the contained
# sections going from left to right

from logger import log
from sensor import sensor
from section import section
from utility import *
from symbols import *
import operator

arg_table = { 'sections' : REQUIRED }

class shuffle_section(section) :

    def __init__(self, name, **args) :
        construct(self, arg_table, args)
        section.__init__(self, name, **args)
        self.my_class = "shuffle_section"
        self._build()
        self.min_section_length = min([ s.length for s in self.section_list ])

    def _build(self) :
        try :
            self.section_list = [ section.get(s.strip()) for s in self.sections.split(';') ]
        except IndexError as exc :
            raise ValueError("section from '%s' not found for shuffle section '%s'" % exc.args[0])
        for s in self.section_list :
            s.set_manager(self)
            s.book_through = False
    def is_empty(self) :
        return and_all([ s.is_empty() for s in self.section_list ])

    def occupancy(self) :
        return sum([s.occupancy() for s in self.section_list])

    def is_unoccupied(self) :
        return self.is_empty()

    def _get_entry_sect(self, sect) :
        entry_end = self._get_connected_end(sect)
        entry_sectno = 0 if entry_end.is_left() else -1
        return self.section_list[entry_sectno]

    def _is_end_section(self, sect) :
        return sect is self.section_list[0] or sect is self.section_list[-1]

    def can_book(self, sect, tr, dir, urgent=False) :
        if not self.is_bookable(tr) :
            return False
        entry_sect = self._get_entry_sect(sect)
        if tr.length > self.min_section_length : # overlength train
            return urgent and section.can_book(self, sect, tr, dir, urgent) 
        elif entry_sect.is_unoccupied() \
                and (self.is_unoccupied() or self.is_same_direction(sect)) :
            return entry_sect.can_book(sect, tr, dir, urgent)
        else :                  # can we shuffle up a reversible train that is waiting?
            train_in_place = entry_sect.get_my_train(sect)
            next_sect = entry_sect.get_departure_end().adjacent
            if train_in_place \
                    and urgent \
                    and train_in_place.is_reversible() \
                    and entry_sect.is_same_direction(sect) \
                    and not next_sect.is_occupied() :
                if next_sect.book(entry_sect, train_in_place, dir) :
                    self._log_me(self, "moving reversible", "from %s train %s", entry_sect, train_in_place)
                    train_in_place.activate(stopping=True)

    def book(self, sect, tr, dir) :
        result = False
        entry_sect = self._get_entry_sect(sect)
        if entry_sect.is_unoccupied() :
            if self.is_unoccupied() :
                self.state = SECTION_BOOKED
                self.direction = sect.direction
            result = entry_sect.book(sect, tr, dir)
            if result and not tr.is_reversible() : # book as far through the sections as possible
                s = entry_sect
                while s.force_extend_booking() :
                    s = s.next_section
                    if self._is_end_section(s) :
                        break
        self._log_me("book", "entry %s train %s", entry_sect, tr)
        return result

    def force_extend_booking(self, dir) :
        s = self._get_first_occupied(dir)
        return s.force_extend_booking(dir)
                            
    def enter(self, from_, offset=0, sensor=False) :
        entry_sect = self._get_entry_sect(from_)
        entry_sect.enter(from_, offset, sensor)

    def tick(self, duration) :
        if self.direction==DIR_NONE :
            return
        sections = self._get_section_list(self.direction)
        for s in sections :
            next = s.right.adjacent
            if s.is_occupied() :
                if s.is_stopped() :
                    print '&&&', self, s, s.my_train, self.show_dir()
                    s.terminate_train(do_wait=False)
            elif next.is_occupied() \
                    and not (self._is_end_section(next) and next.my_train.is_reversible()) :
                if next.force_extend_booking() :
                    self._log_me("shuffling", "from %s train %s", next, next.my_train)
                    next.my_train.activate(stopping=True)
        if self.is_empty() :
            self.state = SECTION_EMPTY

    def get_my_train(self, dir) :
        result = None
        sections = self._get_section_list(dir)
        for s in sections :
            if s.my_train :
                result = s.my_train
                break
        return result

    def set_adjacent(self, dir, sect) :
        section.set_adjacent(self, dir, sect)
        if dir==DIR_LEFT :
            self.section_list[0].set_adjacent(dir, sect)
        else :
            self.section_list[-1].set_adjacent(dir, sect)

    def _get_first_occupied(self, dir) :
        result = None
        sections = self._get_section_list(dir)
        for s in sections :
            if s.is_occupied() :
                result = s
                break
        return result

    def _get_section_list(self, dir) :
        if dir==DIR_LEFT :
            return self.section_list
        else :
            return reversed(self.section_list)
        
    def has_available_train(self, dir) :
        result = False
        s = self._get_first_occupied(dir)
        if s :
            result = s.has_available_train(dir) \
                or (s.is_leftbound()==(dir==DIR_LEFT) and s.get_my_train(end).is_active())
        return result

section.enroll_type('shuffle', shuffle_section)
                                                             sim_controller.py                                                                                   0000755 0001750 0001750 00000001270 13673251343 013153  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   #
# sim_controller - dummy controller when running simulated
#

from layout_controller import layout_controller
from logger import log, trace

class sim_controller(layout_controller) :

    def __init__(self) :
        self.name = 'sim'
        layout_controller.__init__(self)

    def _set_loco(self, dcc_id, speed, reverse, options) :
        trace('controller', self, "setting loco %d speed %s%s options %s",
            dcc_id, '-' if reverse else '', speed, str(options) if options else '<None>')

    def _set_turnout(self, dcc_id, thrown, callback=None) :
        log(self, "setting turnout %d %s",
            dcc_id, "R" if thrown else "N")
        if callback :
            callback()
                                                                                                                                                                                                                                                                                                                                        simple_section.py                                                                                   0000755 0001750 0001750 00000001525 13673251343 013140  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   from section import *
from symbols import *
from dispatcher import dispatcher

arg_table = {
}

class simple_section(section) :

    """
    Simple point-to-point section
    """

    def __init__(self, name, **args) :
        construct(self, arg_table, args)
        section.__init__(self, name, **args)

    def position_train(self, t, left, offset) :
        self.my_train = t
        self.direction = DIR_LEFT if left else DIR_RIGHT
        self.state = SECTION_STOPPED
        if offset >= 0 :
            self.position = self.prev_position = offset
        else :
            end = self.left if left else self.right
            self.position = self.prev_position = \
                            self.length - end.sensor_offset + t.loco.magnet_offset
        t.set_head(self)
        t.set_tail(self)

section.enroll_type('simple', simple_section)
                                                                                                                                                                           simtime.py                                                                                          0000755 0001750 0001750 00000003070 13673251343 011567  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   #
# simtime - central repository for simulated time
#

class simtime(object) :

    now = 0

    def __init__(self, t=None) :
        if isinstance(t, simtime) :
            self.t = t.t
        else :
            self.t = t or simtime.now

    def __str__(self) :
        return '%.02f' % (self.t,)

    def __sub__(self, other) :
        if isinstance(other, simtime) :
            return self.t - other .t
        else :
            return simtime(self.t - other)

    def __add__(self, other) :
        if isinstance(other, simtime) :
            return simtime(self.t + other.t)
        else :
            return simtime(self.t + other)

    def __iadd__(self, other) :
        self.t += other
        return self

    def __eq__(self, other) :
        return self.t==(other.t if isinstance(other, simtime) else other)

    def __ne__(self, other) :
        return self.t!=(other.t if isinstance(other, simtime) else other)

    def __lt__(self, other) :
        return self.t<(other.t if isinstance(other, simtime) else other)

    def __le__(self, other) :
        return self.t<=(other.t if isinstance(other, simtime) else other)

    def __gt__(self, other) :
        return self.t>(other.t if isinstance(other, simtime) else other)

    def __ge__(self, other) :
        return self.t>=(other.t if isinstance(other, simtime) else other)

    def get(self) :
        return self.t

    @staticmethod
    def set_time(t) :
        simtime.now = t

    @staticmethod
    def advance(t) :
        simtime.now += t

    @staticmethod
    def time() :
        return simtime(simtime.now)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                        stop_server.py                                                                                      0000755 0001750 0001750 00000000447 13673251343 012500  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   #
# Hack to make it easy to stop threads
#

from pubsub import pubsub

class stop_server(object) :

    my_pubsub = pubsub()

    @staticmethod
    def listen(fn, *args) :
        stop_server.my_pubsub.listen(fn, *args)

    @staticmethod
    def stop() :
        stop_server.my_pubsub.signal()
                                                                                                                                                                                                                         symbols.py                                                                                          0000755 0001750 0001750 00000000542 13673251343 011611  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   
#
# Directions
# 
DIR_NONE = 0
DIR_RIGHT = 1
DIR_LEFT = 2
#
# Section states
#
SECTION_EMPTY = 0
SECTION_BLOCKED = 1
SECTION_BOOKED = 2
SECTION_CLEAR = 3
SECTION_OCCUPIED = 4
SECTION_STOPPING = 5
SECTION_CONTINUING = 6
SECTION_STARTING = 7
SECTION_STOPPED = 8
SECTION_LEAVING = 9
SECTION_TERMINATING = 10
SECTION_TERMINATED = 11
SECTION_BASE_LAST = 12

                                                                                                                                                              train.py                                                                                            0000755 0001750 0001750 00000014161 13673251343 011240  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   #
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
                                                                                                                                                                                                                                                                                                                                                                                                               turnout.py                                                                                          0000644 0001750 0001750 00000012411 13673251343 011634  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   #
# representation of a simple turnout
#

from section import section
from layout_controller import layout_controller
from utility import *
from logger import log
import functools

#
# This class manages the operation of turnouts. This requires a fairly
# complicated state machine. The caller interface is through the function
# throw, whichrequests a direction and returns True iff the turnout is
# known to be set to that direction. The NCE controller can't handle
# turnout requests at too high a rate, it just sulks and stops obeying
# them. So they have to be rate-paced.
#
# Behind the scenes, the following states are involved:
#
# -- TURNOUT_X (X=NORMAL or REVERSE) : the turnout is believed to be in the corresponding
#                                      state
# -- TURNOUT_TO_X : a command to set the turnout has been queued but
#                   has not yet been executed
# -- TURNOUT_AT_X : a command to set the turnout has been executed and was
#                   the most recent command
# -- TURNOUT_ALREADY_X : the turnout is believed to be in the right state
#                        but a command has been queued to be sure
#

TURNOUT_UNKNOWN         = 0
TURNOUT_NORMAL          = 2
TURNOUT_NORMAL_LSB      = 0x01
TURNOUT_REVERSE         = 3
TURNOUT_TO_NORMAL       = 4
TURNOUT_TO_REVERSE      = 5
TURNOUT_AT_NORMAL       = 6
TURNOUT_AT_REVERSE      = 7
TURNOUT_ALREADY_NORMAL  = 8
TURNOUT_ALREADY_REVERSE = 9
TURNOUT_SET_AT          = TURNOUT_AT_NORMAL - TURNOUT_NORMAL
TUNROUT_NORMAL_REVERSE  = TURNOUT_REVERSE - TURNOUT_NORMAL


class turnout(object) :

    """
    Simple point-to-point section
    """

    turnouts = {}

    arg_table = { 'dcc_id' : None,
                  'container' : None,
                 }

    def __init__(self, name, **args) :
        construct(self, turnout.arg_table, args)
        self.name = name
        self.state = TURNOUT_UNKNOWN
        self.my_class = 'turnout'
        self.last_command_id = 0
        if self.dcc_id is None :
            self.dcc_id = make_dcc_id(self.name)
        self.throw(False)
        turnout.turnouts[name] = self

    def is_unknown(self, state=None) :
        if state is None :
            state = self.state
        return state==TURNOUT_UNKNOWN

    def is_normal(self, state=None) :
        if state is None :
            state = self.state
        return state==TURNOUT_NORMAL

    def is_reverse(self, state=None) :
        if state is None :
            state = self.state
        return state==TURNOUT_REVERSE

    def will_be(self, reverse, state=None) :
        if state is None :
            state = self.state
        return not self.is_unknown(state) and \
            (state & TURNOUT_NORMAL_LSB)==(TURNOUT_NORMAL_LSB if reverse else 0)

    def is_set(self, state=None) :
        if state is None :
            state = self.state
        return TURNOUT_NORMAL<=state<=TURNOUT_REVERSE

    def is_already(self, state=None) :
        if state is None :
            state = self.state
        return TURNOUT_ALREADY_NORMAL<=state<=TURNOUT_ALREADY_REVERSE        

    def is_moving(self, state=None) :
        if state is None :
            state = self.state
        return TURNOUT_TO_NORMAL<=state<=TURNOUT_TO_REVERSE

    def is_complete(self, state=None) :
        if state is None :
            state = self.state
        return TURNOUT_AT_NORMAL<=state<=TURNOUT_AT_REVERSE

    def throw(self, reverse) :
        result = False
        old_state = self.state
        if self.will_be(reverse) :
            if self.is_set() :
                self._do_throw(reverse, TURNOUT_ALREADY_NORMAL)
                result = True
            elif self.is_already() :
                result = True
            elif self.is_complete() :
                self.state -= TURNOUT_SET_AT
                result = True
        else :
            if reverse :
                self.state = TURNOUT_TO_REVERSE
            else :
                self.state = TURNOUT_TO_NORMAL
            self._do_throw(reverse, TURNOUT_AT_NORMAL)
        log(self, 'throw prev state %s new state %s result %s', self.show_state(old_state), \
            self.show_state(), result)
        return result

    def _do_throw(self, reverse, final_state) :
        self.last_command_id += 1
        if reverse :
            final_state |= TURNOUT_NORMAL_LSB
        callback = functools.partial(turnout._callback, \
                                     self, self.last_command_id, final_state)
        layout_controller.set_turnout(self.dcc_id, reverse, callback=callback)
        
    def _callback(self, id, state) :
        if self.last_command_id==id :
            self.state = state

    def show_state(self, state=None) :
        if state is None :
            state = self.state
        if state==TURNOUT_UNKNOWN :
            result = '?'
        else :
            result = '->' if self.is_moving(state) else \
                     ':' if self.is_complete(state) else \
                     '@' if self.is_already(state) else \
                     ''
            result += "N" if self.will_be(False, state) else "R"
        return result

    def __str__(self) :
        return self.name

    @staticmethod
    def get(name) :
        return turnout.turnouts[name]

    @staticmethod
    def get_if(name) :
        try :
            return turnout.get(name)
        except KeyError :
            return None
                                                                                                                                                                                                                                                       usb_listener.py                                                                                     0000755 0001750 0001750 00000003120 13673251343 012612  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   import socket
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

                                                                                                                                                                                                                                                                                                                                                                                                                                                utility.py                                                                                          0000755 0001750 0001750 00000010341 13673677623 011637  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   __all__ = [ 'construct', 'add_default_arg', 'check_unused_args', 'REQUIRED', 'parse_direction', 'container_equal', 'select', 'reverse_direction', "weighted_choice", "find_devices", 'get_time_of_day', 'and_all', 'or_all', 'make_dcc_id' ]

import math
import string
import time
import re
import os
import random
import functools
import operator
from time import localtime, strftime
from datetime import datetime
from symbols import *

# 
# construct - generic help for delegated constructors
#
# arg table is either a list of argument names, or a dict of args names and
# the associated handler function or None, or the default value
#
# args which are handled are removed from the dict.
#

REQUIRED = object()

def construct(obj, arg_table, kwargs, check=False, prefix='') :
    if not isinstance(arg_table, dict)  :
        arg_table = { a : None for a in arg_table }
    #print '%%%', kwargs, arg_table
    for k,a in arg_table.items() :
        pk = prefix + k
        #print '$$$', k, a, pk,
        if pk in kwargs :
            if callable(a) :
                v = (a)(obj, kwargs[pk])
            elif a is None or a is REQUIRED :
                v = kwargs[pk]
            else :
                v = type(a)(kwargs[pk])
            del kwargs[pk]
        else :
            if a is REQUIRED :
                raise ValueError("required argument '%s' not present" % (pk,))
            elif callable(a) :
                v = (a)(obj, None)
            else :
                v = a
        setattr(obj, k, v)
        #print v, kwargs
    if check : check_unused_args(kwargs)

def add_default_arg(args, name, value) :
    if name not in args :
        args[name] = value

def check_unused_args(kwargs) :
    if kwargs :
        raise NameError("unexpected args: " + ", ".join(list(kwargs.keys())))
#
# Turn a direction ('left' or 'right') into 'l' or 'r'
#

def parse_direction(dir) :
    if 'left'.startswith(dir.lower()) :
        return DIR_LEFT
    elif 'right'.startswith(dir.lower()) :
        return DIR_RIGHT
    else :
        raise ValueError("direction must be 'left', 'l', 'right' or 'r', not '%s'" % (dir,))

# container_equal
#

def container_equal(c1, c2) :
    result = False
    if len(c1)==len(c2) :
        for c in c1 :
            if c not in c2 :
                break
        result = True
    return result

#
# select - LISP style switch function
#

def select(value, *cases) :
    while len(cases) :
        if len(cases)==1 :
            return cases[0]
        elif (isinstance(cases[0], list) or isinstance(cases[0], tuple)) and value in cases[0] :
            return cases[1]
        elif value==cases[0] :
            return cases[1]
        else :
            cases = cases[2:]
    return None

#
# reverse - return the opposite of a direction
#

def reverse_direction(dir) :
    return select(dir, \
                      DIR_LEFT, DIR_RIGHT, \
                      DIR_RIGHT, DIR_LEFT, \
                      DIR_NONE, DIR_NONE)

#
# weighted choice - choose one element of a collection based on a weight.
# weight_fn must return a >=0 value for each element of the collection
#

def weighted_choice(coll, weight_fn) :
    weights = [ weight_fn(c) for c in coll ]
    r = random.random() * sum(weights)
    for c,w in zip(coll, weights) :
        r -= w
        if r <= 0 :
            return c
    # should never get here
    return coll[-1]

#
# find_devices - find all devices of the given type
#

def find_devices(pfx, exclude=None) :
    dev = os.listdir("/dev")
    return [ d for d in (dev or [])  \
             if d.startswith(pfx) and not d in (exclude or []) ]

#
# get_time_of_day - get a string represnting the time of day
#

def get_time_of_day(microsecs=True) :
    return datetime.now().strftime("%H:%M:%S" + ('.%f' if microsecs else ''))

#
# and_all, or_all, sum_all - return the and/or/sum of all items in an iterabe
#

def and_all(list_) :
    return functools.reduce(operator.__and__, list_, True)

def or_all(list_) :
    return functools.reduce(operator.__or__, list_, False)

def sum_all(list_) :
    return functools.reduce(operator.__plus__, list_, 0)

#
# make_dcc_id - deduce the dcc_id from an object's name
#

def make_dcc_id(name) :
    result = None
    m = re.match(r'^\D*(\d+)$', name)
    if m :
        result = int(m.group(1))
    return result
                                                                                                                                                                                                                                                                                               yard_fan_section.py                                                                                 0000644 0001750 0001750 00000004632 13705616320 013425  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   #
# A turnout fan which is also one end of a yard
#

from section import section
from logger import log
from fan_section import fan_section
from utility import *
from symbols import *
import random
import constants
from simtime import simtime

arg_table = { }

class yard_fan_section(fan_section) :

    def __init__(self, name, **args) :
        construct(self, arg_table, args)
        self.section_robin = 0
        fan_section.__init__(self, name, **args)

    def dispatch(self) :
        dir = self.orientation
        if self.is_empty() \
           and self._get_unique_adjacent().is_empty() \
           and random.random() < constants.yard_departure_prob :
            choices = [ s for s in self.sections if s.has_available_train(dir) ]
            if choices :
                source = weighted_choice(choices, lambda s : s.get_my_train(dir).idle_time())
                if source :
                    t = source.get_my_train(dir)
                    if source.force_extend_booking() :
                        self.set_route(source)
        elif self.is_booked() and not self.next_section :
            self.force_extend_booking()
        elif self.is_clear() and self.my_train and not self.my_train.is_active() :
            self.activate()
            self.selected.activate()
            self.my_train.activate(dir, cruise=True)
        section.dispatch(self)

    def book(self, sect, tr, dir) :
        if simtime.time() > 30:
            i = 1
        result = False
        if sect==self._get_unique_adjacent() :
            for urgent in [ False, True ] :
                if self.can_book(sect, tr, dir, urgent) :
                    for s in self.sections[:self.section_robin] + self.sections[self.section_robin:] :
                        if s.can_book(self, tr, dir, urgent) :
                            self._log_me("book_yard", "siding %s", s)
                            result = True
                            self.set_route(s)
                            self._book(sect, tr, dir)
                            break
                if result :
                    break
            self.section_robin += 1
            if self.section_robin >= len(self.sections) :
                self.section_robin = 0
        else :
            result = self._book(sect, tr, dir)
        self._log_me("book yard_fan", "siding %s", result)
        return result
        
            
        
section.enroll_type('yard_fan', yard_fan_section)
                                                                                                      yard_section.py                                                                                     0000755 0001750 0001750 00000012622 13705467072 012612  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   #
# Representation of a yard (ladder of sidings). The description consists of the fan at each
# end, which implicitly gives the sidings that make up the yard
#

from section import *
from fan_section import fan_section
from simple_section import simple_section
from loop_section import loop_section
from utility import *
import constants
import random
from logger import log

arg_table = { 'left_fan' : None,
              'right_fan' : None,
              'through_prob' : constants.yard_through_prob,
          }

class yard_section(section) :

    def __init__(self, name, **args) :
        construct(self, arg_table, args)
        section.__init__(self, name, **args)
        self.my_class = 'yard_section'
        self.left_fan_description, self.right_fan_description = self.left_fan, self.right_fan
        self.left_fan = fan_section(name+'_L', description=self.left_fan_description, \
                                    orientation='left', \
                                    book_through=True, \
                                    container=self)
        self.right_fan = fan_section(name+'_R', description=self.right_fan_description, \
                                     orientation='right', \
                                     book_through=True, \
                                     container=self)
        self.sections = [ section.get(s) for s in list(self.left_fan.exits.keys()) ]
        self.section_robin = 0
        if not container_equal(list(self.left_fan.exits.keys()), list(self.right_fan.exits.keys())) :
            raise ValueError("sections accessed through a yard's left and right fans must be the same")
        for s in self.sections :
            s.set_adjacent(self.left_fan, True)
            s.set_adjacent(self.right_fan, False)
            s.set_container(self)
            s.hold = True
        self.through_booking_rejected = False

    def _book(self, sect, tr, dir) :
        book = None
        entry_fan = self.left_fan if sect==self.left.adjacent else self.right_fan
        for urgent in [ False, True ] :
            if entry_fan.can_book(sect, tr, dir, urgent) :
                for s in self.sections[:self.section_robin] + self.sections[self.section_robin:] :
                    if s.can_book(sect, tr, dir, urgent) :
                        if book is None or book.get_occupancy() < s.get_occupancy() :
                            book = s
                if book :
                    self._log_me("book_yard", "siding %s", book)
                    entry_fan.set_route(book)
                    entry_fan._book(sect, tr)
                break
        self.section_robin += 1
        if self.section_robin >= len(self.sections) :
            self.section_robin = 0
        return (book is not None)

    def prepare(self, sect) :
        fan = self._get_entry_fan()
        fan.prepare(sect)
        fan.selected.prepare(sect)

    def enter(self, from_) :
        self._get_entry_fan().enter(from_)
        fan.enter(from_)
        fan.selected.enter(fan.selected)

    def leave(self) :
        fan = self._get_exit_fan()
        fan.leave()
        self.through_booking_rejected = False

    def dispatch(self) :
        self._try_through(self.left_fan, self.right_fan)
        self._try_through(self.right_fan, self.left_fan)
        self._try_departure(self.left_fan, section.get_left)
        self._try_departure(self.right_fan, section.get_right)

    def terminate_train(self, siding) :
        siding.terminate_train()
        self.through_booking_rejected = False

    def enliven_connections_v(self) :
        self.left.delegate_to(self.left_fan.left)
        self.right.delegate_to(self.right_fan.right)
        self.enliven_connections_base()
        for f in [self.left_fan, self.right_fan] :
            f.enliven_connections()

    def _try_departure(self, fan, get_end) :
        if fan.is_empty() and random.random() < constants.yard_departure_prob :
            choices = [ s for s in self.sections if s.has_available_train(get_end(s)) ]
            if choices :
                source = weighted_choice(choices, lambda s : s.get_my_train(get_end(s)).idle_time())
                if source :
                    t = source.get_my_train(get_end(source))
                    if source.force_extend_booking(get_end(self).is_left()) :
                        fan.set_route(source)
                        self.my_train = t
                        self._log_me("starting train")
        elif fan.is_clear() :
            self.activate()
            fan.selected.activate()
            fan.selected.my_train.activate(leftbound=self.is_leftbound(), cruise=True)

    def _try_through(self, entry_fan, exit_fan) :
        if not entry_fan.is_empty() and entry_fan.next_section :
            s = entry_fan.selected
            if exit_fan.is_empty() \
               and not self.through_booking_rejected \
               and random.random() < constants.yard_through_prob :
                entry_fan.force_extend_booking()
                exit_fan.set_route(s)
                s.force_extend_booking()
                self._log_me("through train", "siding %s", s)
            else :
                self.through_booking_rejected = True
                s.set_terminating()
                
    def _get_entry_fan(self) :
        return self.right_fan() if self.is_leftbound() else self.left_fan()

    def _get_exit_fan(self) :
        return self.left_fan if self.is_leftbound() else self.right_fan
        
section.enroll_type('yard', yard_section)

                                                                                                              garden.txt                                                                                          0000644 0001750 0001750 00000001652 13705146354 011551  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   [sections]

S1 : length=10, left_sensor=4, right_sensor=1, terminus=1
S2 : length=10, left_sensor=8, right_sensor=5, terminus=1
S3 : length=12, left_sensor=12, right_sensor=9, terminus=1
F1 : type=yard_fan, description=T11:S1/S2;T10:T11/S3, length=15, \
     left_adjacent=L1, orientation=left
F2 : type=yard_fan, description=T12:S1/S2;T13:T12/S3, length=15, \
     right_adjacent=L2, orientation=right
L1 : type=loop, turnout=T3, length = 120
L2 : type=loop, turnout=T4, length = 30

[locos]

Helmut : dcc_id=7, length=1, magnet_offset=0.2
Hartmut : dcc_id=4, length=1, magnet_offset=0.2, max_speed=25
Marcel : dcc_id=1, length=1, magnet_offset=0.2, max_speed=25
Thomas : dcc_id=6, length=1, magnet_offset=0.2, max_speed=25

[trains]

Helmut : loco=Helmut, length=3
Hartmut : loco=Hartmut, length=3
Marcel : loco=Marcel, length=2, stopping_speed=15
Thomas : loco=Thomas, length=3

[positions]

Hartmut : S3/R
Thomas : S2/R
Helmut : S1/R
                                                                                      layout.txt                                                                                          0000755 0001750 0001750 00000001404 13705146354 011624  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   [sections]

S1 : length=20, left_sensor=1, right_sensor=2
S2 : length=20, left_sensor=3, right_sensor=4
S3 : length=20, left_sensor=5, right_sensor=6
S4 : length=20, left_sensor=7, right_sensor=8
Y1 : type=yard, left_fan=T1:S1/S2;T2:S3/S4;T3:T1/T2, right_fan=T4:S1/S2;T5:S3/S4;T6:T4/T5, \
     length=30, left_adjacent=L1, right_adjacent=L2
L1 : type=loop, turnout=T3, length = 60
L2 : type=loop, turnout=T4, length = 300

[locos]

Helmut : dcc_id=7, length=1, magnet_offset=0.2
Hartmut : dcc_id=4, length=1, magnet_offset=0.2
Marcel : dcc_id=1, length=1, magnet_offset=0.2
Thomas : dcc_id=6, length=1, magnet_offset=0.2

[trains]

Helmut : loco=Helmut, length=3
Hartmut : loco=Hartmut, length=3
Marcel : loco=Marcel, length=2
Thomas : loco=Thomas, length=3

[positions]

                                                                                                                                                                                                                                                            log_sensor.txt                                                                                      0000664 0001750 0001750 00000000000 13705621360 012442  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   ss.txt                                                                                              0000644 0001750 0001750 00000002530 13705146354 010732  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   [sections]

S1 : length=5, left_sensor=4, right_sensor=3, right_adjacent=S2
S2 : length=5, left_sensor=2, right_sensor=1, left_adjacent=S1
S3 : length=5, left_sensor=8, right_sensor=7, right_adjacent=S4
S4 : length=5, left_sensor=6, right_sensor=5, left_adjacent=S3
S5 : length=5, left_sensor=10, right_sensor=9, right_adjacent=S6
S6 : length=5, left_sensor=12, right_sensor=11, left_adjacent=S5
SS1 : type=shuffle, sections=S1;S2
SS2 : type=shuffle, sections=S3;S4
SS3 : type=shuffle, sections=S5;S6
F1 : type=yard_fan, description=T11:S1/S3;T10:T11/S5, length=15, \
     left_adjacent=L1, orientation=left
F2 : type=yard_fan, description=T12:S2/S4;T13:T12/S6, length=15, \
     right_adjacent=L2, orientation=right
L1 : type=loop, turnout=T3, length = 120
L2 : type=loop, turnout=T4, length = 30

[locos]

Helmut : dcc_id=7, length=1, magnet_offset=0.2
Hartmut : dcc_id=4, length=1, magnet_offset=0.2, max_speed=25
Marcel : dcc_id=1, length=1, magnet_offset=0.2, max_speed=25
Thomas : dcc_id=6, length=1, magnet_offset=0.2, max_speed=25
Shiny : dcc_id=9, length=1, magnet_offset=0.2, max_speed=25

[trains]

Helmut : loco=Helmut, length=3
Hartmut : loco=Hartmut, length=3
Marcel : loco=Marcel, length=2, stopping_speed=15
Thomas : loco=Thomas, length=3
Shiny : loco=Shiny, length=0

[positions]

Hartmut : S1/R
Thomas : S2/R
Helmut : S3/R
Marcel : S4/R
Shiny : S5/L
                                                                                                                                                                        s.txt                                                                                               0000644 0001750 0001750 00000001753 13705146354 010555  0                                                                                                    ustar   john                            john                                                                                                                                                                                                                   [sections]

S1 : length=10, left_sensor=4, right_sensor=1
S3 : length=10, left_sensor=8, right_sensor=5
S5 : length=10, left_sensor=10, right_sensor=11
F1 : type=yard_fan, description=T11:S1/S3;T10:T11/S5, length=15, \
     left_adjacent=L1, orientation=left
F2 : type=yard_fan, description=T12:S1/S3;T13:T12/S5, length=15, \
     right_adjacent=L2, orientation=right
L1 : type=loop, turnout=T3, length = 120
L2 : type=loop, turnout=T4, length = 30

[locos]

Helmut : dcc_id=7, length=1, magnet_offset=0.2
Hartmut : dcc_id=4, length=1, magnet_offset=0.2, max_speed=25
Marcel : dcc_id=1, length=1, magnet_offset=0.2, max_speed=25
Thomas : dcc_id=6, length=1, magnet_offset=0.2, max_speed=25
Shiny : dcc_id=9, length=1, magnet_offset=0.2, max_speed=25

[trains]

Helmut : loco=Helmut, length=3
Hartmut : loco=Hartmut, length=3
Marcel : loco=Marcel, length=2, stopping_speed=15
Thomas : loco=Thomas, length=3
Shiny : loco=Shiny, length=0, reversible

[positions]

Hartmut : S1/R
Helmut : S3/R
Shiny : S5/L
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     