#
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

