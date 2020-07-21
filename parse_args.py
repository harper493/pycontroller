import sys
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

