#
# sim_controller - dummy controller when running simulated
#

from layout_controller import layout_controller
from logger import log, trace

class sim_controller(layout_controller) :

    def __init__(self) :
        self.name = 'sim'
        layout_controller.__init__(self)

    def _set_loco(self, dcc_id, speed, reverse, options) :
        trace('controller', self, "setting loco %d speed %s%s options %s",
            dcc_id, '-' if reverse else '', speed, str(options) if options else '<None>')

    def _set_turnout(self, dcc_id, thrown, callback=None) :
        log(self, "setting turnout %d %s",
            dcc_id, "R" if thrown else "N")
        if callback :
            callback()
