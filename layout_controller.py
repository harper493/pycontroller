#
# layout_controller - static class for communicating with DCC controller
#

class layout_controller(object) :

    the_controller = None

    def __init__(self) :
        layout_controller.the_controller = self
        self.my_class = 'layout_controller'

    @staticmethod
    def set_loco(dcc_id, speed, reverse, options) :
        layout_controller.the_controller._set_loco(dcc_id, speed, reverse, options)

    @staticmethod
    def set_turnout(dcc_id, thrown, callback=None) :
        layout_controller.the_controller._set_turnout(dcc_id, thrown, callback=callback)

