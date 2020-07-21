#
# Base class for manager objects, i.e. ones that supervise traffic
# across multiple sections
#

from logger import log
from utility import *
import constants
from symbols import *
from section import section

class manager(object) :

    arg_table = { 'sections' : REQUIRED,
                  }

    def __init__(self, name, **args) :
        self.name = name
        self.my_class = 'manager'
        construct(self, manager.arg_table, args, check=True)
        self.my_sections = [ section.get(n) for n in self.sections.split(';') ]

    def can_book(self, to_sect, from_sect, tr, dir, urgent) :
        """
        Delegated can_book function. Return (True, result) if all required
        action has been taken, 'result' is whether the booking can be
        taken. Return (False, xxx) to re-delegate back to the section
        object.
        """
        return (False, False)

    def book(self, to_sect, from_sect, tr, dir) :
        """
        Delegated book function. Return (True, result) if all required action has
        been taken, (False, xxx) to allow the section to take care of its own booking.
        'result' says whether thebooking was successful.
        """
        return (False, False)

    def dispatch(self, sect) :
        """
        Delegated dispatch function. Return True if all required action
        has been taken, False to allow the section to take care of it.
        """
        return False

    def get_occupancy(self, sect) :
        """
        Delegated get_occupancy function. By default, returns the
        section's value. Used for shuffle_section and other to
        return the total number of trains in the managed collection.
        """
        return sect._get_occupancy()

    def make_booking(self, sect) :
        """
        Called when a booking is being made for managed section sect.
        """
        return

    def _log_me(self, why, extra=None, *args) :
        x = (extra % args) if extra else ''
        log(self, "%s: %s", \
            why, x)
