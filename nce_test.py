from nce_controller import nce_controller
from logger import logger
from stop_server import stop_server

l = logger(console=True)
l._add_trace('controller')

n = nce_controller('')

n._set_turnout(3, 1)
n._set_turnout(1, 0)
n._set_turnout(511, 0)
n._set_loco(1, 0, False)
n._set_loco(1, 127, False)
n._set_loco(1, 127, True)
n._set_loco(15, 63, False)
n._set_loco(15, 63, False, [0])
n._set_loco(15, 63, False, [0,1])
n._set_loco(15, 63, False, [1])
n._set_loco(15, 63, False, [1,2,8])
n._set_loco(15, 63, False, [2,8,12])
n._set_loco(15, 63, False)

stop_server.stop()
