#
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
