#
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

    def book(self, prev_sect, tr, dir) :
        result = False
        if prev_sect!=self._get_unique_adjacent() :
            for urgent in [ False, True ] :
                if self.can_book(prev_sect, tr, dir, urgent) :
                    for s in self.sections[:self.section_robin] + self.sections[self.section_robin:] :
                        if s.can_book(self, tr, dir, urgent) :
                            self._log_me("book_yard", "siding %s", s)
                            result = True
                            self.set_route(s)
                            self._book(prev_sect, tr, dir)
                            break
                if result :
                    break
            self.section_robin += 1
            if self.section_robin >= len(self.sections) :
                self.section_robin = 0
        else :
            result = self._book(prev_sect, tr, dir)
        if result:
            self._log_me("book yard_fan")
        return result
        
            
        
section.enroll_type('yard_fan', yard_fan_section)
