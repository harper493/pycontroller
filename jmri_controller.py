#
# jmri_controller - specialization of controller to work via JMRI
#

from layout_controller import layout_controller
import socket

class jmri_controller(layout_controller) :

    def __init__(self, address, port) :
        self.address, self.port = address, port
        self.socket = None
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        layout_controller.__init__(self)

    def _set_loco(dcc_id, speed, reverse, options) :
        pass

    def set_turnout(dcc_id, thrown) :
        pass
        

    
