#
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
