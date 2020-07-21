__all__ = [ 'construct', 'add_default_arg', 'check_unused_args', 'REQUIRED', 'parse_direction', 'container_equal', 'select', 'reverse_direction', "weighted_choice", "find_devices", 'get_time_of_day', 'and_all', 'or_all', 'make_dcc_id' ]

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
