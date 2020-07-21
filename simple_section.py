from section import *
from symbols import *
from dispatcher import dispatcher

arg_table = {
}

class simple_section(section) :

    """
    Simple point-to-point section
    """

    def __init__(self, name, **args) :
        construct(self, arg_table, args)
        section.__init__(self, name, **args)

    def position_train(self, t, left, offset) :
        self.my_train = t
        self.direction = DIR_LEFT if left else DIR_RIGHT
        self.state = SECTION_STOPPED
        if offset >= 0 :
            self.position = self.prev_position = offset
        else :
            end = self.left if left else self.right
            self.position = self.prev_position = \
                            self.length - end.sensor_offset + t.loco.magnet_offset
        t.set_head(self)
        t.set_tail(self)

section.enroll_type('simple', simple_section)
