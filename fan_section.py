#
# Representation of a turnout fan
#
# A fan is described as a semicolon-separated list of turnouts followed
# by the normal and reverse adjacencies, as follows:
#
# T1:T2/S34; T2:T3/T4; T3:S35/S36; T4:S37/S31
#

from section import section
from turnout import turnout
from logger import log
import re
from utility import *
from symbols import *
from simtime import simtime

arg_table = { 'orientation' : lambda obj, dir : parse_direction(dir),
              'description' : '',
          }

class fan_section(section) :

    def __init__(self, name, **args) :
        construct(self, arg_table, args)
        section.__init__(self, name, **args)
        if self.is_leftwards() :
            self.right.set_multi_adjacency()
        else :
            self.left.set_multi_adjacency()
        self._build()
        self.selected = None
        self.sections = [ section.get(ss) for ss in self.exits.keys() ]
        self.route_set = False
        self.book_through = True
        for s in self.sections :
            s.set_adjacent(self.orientation, self)

    def is_leftwards(self) :
        return self.orientation==DIR_LEFT

    def set_route(self, _exit) :
        if not _exit.name in self.exits :
            raise ValueError("fan '%s' does not have an exit to section '%s'" \
                % (self.name, str(_exit)))
        self.route_set = False
        if self.selected != _exit :
            self.selected = _exit
            if self.is_leftwards() :
                self.right.adjacent = _exit
            else :
                self.left.adjacent = _exit
            self._log_me("set_route", "route %s", self._show_exit(self.exits[_exit.name]))
        return self.is_clear()

    def is_clear(self) :
        if not self.route_set and self.selected :
            self.route_set = and_all([ x[0].throw(x[1]) for x in self.exits[self.selected.name] ])
        return self.route_set

    #
    # _build - take the description and turn it into what we need to operate.
    #
    # We build the exits dict, which contains one entry for each section the fan leads
    # to, each of which is a list of tuples of (turnout, direction) - so to select
    # a section, we just go down the list making all those settings (see set_route).
    #
    # To do this, we keep an auxiliary list for each turnout saying which sections it
    # is relevant to. Then, when a further-out turnout references it, we know
    # which exit entry to add THIS turnout to. It's a bit complicated but it does work,
    # honest.
    #

    def _build(self) :
        self.exits = {}
        self.turnouts = {}
        turnout_exits = {}
        descriptions = [ re.match(r'^\s*(\w+)\s*:\s*(\w+)\s*/\s*(\w*)\s*$', tt) \
                         for tt in self.description.split(';') ]
            # make array of turnout:normal/thrown with optional whitespace
        for d in descriptions :
            if d is None :
                raise ValueError("fan descriptions for %s must be in the form Tx:Ty/Sz,... or similar: '%s'" % \
                    (self.name, self.description))
        progress = True
        good_values = 0
        done = {}
        while progress :
            progress = False
            for m in descriptions :
                if m in done :
                    continue
                tname, nname, rname = m.group(1), m.group(2), m.group(3)
                normal = section.get_if(nname) or turnout.get_if(nname)
                reverse = section.get_if(rname) or turnout.get_if(rname)
                if normal and reverse :
                    progress = True
                    good_values += 1
                    done[m] = None
                    t = turnout(tname, container=self)
                    self.turnouts[t.name] = t
                    turnout_exits[t.name] = []
                    for s in [normal, reverse] :
                        if isinstance(s, turnout) :
                            turnout_exits[t.name] += turnout_exits[s.name]
                            for ss in turnout_exits[s.name] :
                                self.exits[ss].append((t, s is reverse))
                        else :
                            turnout_exits[t.name].append(s.name)
                            self.exits[s.name] = [(t, s is reverse)]
        if good_values != len(descriptions) :
            raise ValueError("some sections for %s do not exist yet: '%s'" \
                % (self.name, self.description))
        log(self, "exits: %s", self._show_exits())

    def _show_exit(self, exits) :
        return ','.join([ "%s%s" % (tt[0], "R" if tt[1] else "N") \
                          for tt in exits ])

    def _show_exits(self) :
        return '; '.join([ "%s:%s" % (xn, self._show_exit(xv)) \
                                   for xn,xv in self.exits.items() ])
        
    def _get_next_section(self, prev_sect) :
        if simtime.time() > 30:
            i = 1
        result = None
        if self.orientation == DIR_LEFT :
            result = self.selected if prev_sect==self.left.adjacent else self.left.adjacent
        else :
            result = self.selected if prev_sect==self.right.adjacent else self.right.adjacent
        log(self, "_get_next_section: prev_sect %s selected %s result %s", prev_sect, self.selected, result)
        return result

    def make_booking_v(self) :
        if self.next_section in self.exits :
            self.set_route(self.next_section)

    def enliven_connections(self) :
        for x in self.sections :
            x.enliven_connections()

    def leave_v(self) :
        self.selected = None

    def _get_unique_adjacent(self) :
        if self.orientation==DIR_LEFT :
            return self.left.adjacent
        else :
            return self.right.adjacent

    def _set_direction(self, val) :
        self.orientation = parse_direction(val)

    def _log_extra(self) :
        return "selected " + str(self.selected)

    def _dump_extra(self) :
        return "exits=" + self._show_exits()

section.enroll_type('fan', fan_section)
    
