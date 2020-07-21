#!/usr/bin/python

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
