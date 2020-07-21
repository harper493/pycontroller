#
# simtime - central repository for simulated time
#

class simtime(object) :

    now = 0

    def __init__(self, t=None) :
        if isinstance(t, simtime) :
            self.t = t.t
        else :
            self.t = t or simtime.now

    def __str__(self) :
        return '%.02f' % (self.t,)

    def __sub__(self, other) :
        if isinstance(other, simtime) :
            return self.t - other .t
        else :
            return simtime(self.t - other)

    def __add__(self, other) :
        if isinstance(other, simtime) :
            return simtime(self.t + other.t)
        else :
            return simtime(self.t + other)

    def __iadd__(self, other) :
        self.t += other
        return self

    def __eq__(self, other) :
        return self.t==(other.t if isinstance(other, simtime) else other)

    def __ne__(self, other) :
        return self.t!=(other.t if isinstance(other, simtime) else other)

    def __lt__(self, other) :
        return self.t<(other.t if isinstance(other, simtime) else other)

    def __le__(self, other) :
        return self.t<=(other.t if isinstance(other, simtime) else other)

    def __gt__(self, other) :
        return self.t>(other.t if isinstance(other, simtime) else other)

    def __ge__(self, other) :
        return self.t>=(other.t if isinstance(other, simtime) else other)

    def get(self) :
        return self.t

    @staticmethod
    def set_time(t) :
        simtime.now = t

    @staticmethod
    def advance(t) :
        simtime.now += t

    @staticmethod
    def time() :
        return simtime(simtime.now)
