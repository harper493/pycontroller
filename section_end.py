#
# section_end - one end of a section (left or right)
#

from logger import log
from sensor import sensor
from utility import *
from symbols import *
import constants

arg_table = { 'adjacent' : None,
              'sensor' : None,
              'sensor_offset' : 0,
}

class section_end(object) :

    def __init__(self, owner, direction, explicit_args=None, **args) :
        self.my_class = 'section_end'
        self.owner, self.direction = owner, direction
        self.delegate = None
        args = explicit_args or args
        self.dir_string = 'left' if self.direction==DIR_LEFT else 'right'
        construct(self, arg_table, args, prefix=self.dir_string+'_')
        self.sensor_offset = self.sensor_offset or constants.default_sensor_offset \
                             if self.sensor else 0
        self.multi_adjacency = False
        if self.sensor :
            self.sensor = sensor.make_sensor_for(self.sensor, self)

    def enliven_connections(self) :
        if isinstance(self.adjacent, str) :
            self.adjacent = self.owner.enliven_m(self.adjacent)
            if self.adjacent :
                self.adjacent.enliven_connections()
        if self.adjacent and not self.delegate :
            opposite_end = self.adjacent.get_opposite_end(self)
            if opposite_end and not opposite_end.multi_adjacency :
                if opposite_end.adjacent is None :
                    opposite_end.adjacent = self.owner
                else :
                    if opposite_end.adjacent != self.owner :
                        raise ValueError("incorrect adjacency, section %s connected to %s which is connected to %s" % \
                            (str(self.owner), str(opposite_end.owner), str(opposite_end.adjacent)))

    def is_left(self) :
        return self.direction==DIR_LEFT

    def is_right(self) :
        return self.direction==DIR_RIGHT

    def set_multi_adjacency(self) :
        self.multi_adjacency = True
        
    def delegate_to(self, delegate) :
        self.delegate = delegate
        delegate.adjacent = self.adjacent

    def __str__(self) :
        return self.owner.name + '.' + self.dir_string

    def show_adjacent(self) :
        if self.adjacent :
            if isinstance(self.adjacent, str) :
                return self.adjacent
            else :
                return self.adjacent.name
        else :
            return "<None>"
