#
# Representation of a reverse loop with no sidings
#

from section import *
from turnout import turnout
from sensor import sensor
from logger import log
from utility import *
from symbols import *

arg_table = { 'prefer_thrown' : False,
              'prefer_normal' : False,
              'turnout' : REQUIRED,
              'half_way' : '0.5',
              }

class loop_section(section) :

    def __init__(self, name, **args) :
        construct(self, arg_table, args)
        section.__init__(self, name, **args)
        if not isinstance(self.turnout, turnout) :
            self.turnout = turnout(self.turnout, container=self, \
                                   normal_section=self, thrown_section=self)
        try :
            self.half_way = float(self.half_way) * self.length
            self.half_way_sensor = None
        except ValueError :
            self.half_way = None
            self.half_way_sensor = sensor.get(self.half_way)
            self.half_way_sensor.listen(self.half_way_listen)
        self.reached_half_way = 'no'
        self.hold = True
        self.book_through = False

    def enter(self, from_, offset=0) :
        if not self.is_occupied() :
            self.reached_half_way = 'no'
            self.hold = True
            self.enter_base(from_, offset)

    def half_way_listen(self) :
        self.reached_half_way = 'yes'

    def _can_cruise(self) :
        return self.reached_half_way=='no'

    def enliven_connections_v(self) :
        self.enliven_connections_base()

    def review_position(self) :
        if self.half_way :
            if self.position > self.half_way >= self.prev_position :
                self.reached_half_way = 'yes'
        if self.reached_half_way == 'yes' :
            self.leave_previous()
            self.reached_half_way = 'done'
            self.hold = False
            prev_state = self.state
            self.state = SECTION_OCCUPIED
            self.direction = reverse_direction(self.direction)
            self._log_me("half way", "old_state %s", self.show_state(prev_state))
        self.review_position_base()
        
    def prepare(self, sect) :
        self.prepare_base(sect)
        if prefer_thrown :
            self.turnout.throw(True)
        elif prefer_normal :
            self.turnout.throw(False)

section.enroll_type('loop', loop_section)
    

                
