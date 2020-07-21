#!/usr/bin/python

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
