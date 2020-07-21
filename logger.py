# logger.py
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
