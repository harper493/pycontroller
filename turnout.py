#
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
