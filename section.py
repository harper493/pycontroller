from logger import log
from utility import *
from section_end import section_end
from dispatcher import dispatcher
from train import train
from simtime import simtime
from symbols import *
import random
import constants
import re
import traceback

STATUS_INTERVAL = 10

# section states

class section(object) :

    """
    Base class for all kinds of track section

    Supports the follwing operations:
    -- book - book a section for a given train and previous section
    -- prepare - set up the route for the imminent arrival of the train
    -- enter - the train has arrived in the section
    -- leave - the train has definitely left the section
    """

    arg_table = { 'container' : None,
                  'max_speed' : constants.default_max_speed,
                  'radius' : None,
                  'length' : 0,
                  'exclude' : [],
                  'template' : None,
                  'hold' : False,
                  'terminus' : False,
                  'blocked' : False,
                  'book_through' : False,
                  'through_prob' : constants.section_through_prob,
              }

    sections = {}
    types = {}
    first = True

    def __init__(self, name, **args) :
        self.my_class = 'section'
        self.name = name
        self.left = section_end(self, DIR_LEFT, explicit_args=args)
        self.right = section_end(self, DIR_RIGHT, explicit_args=args)
        construct(self, section.arg_table, args, check=True)
        if self.template :
            construct(self, section.arg_table, self.template.__dict__)
        self.my_train = None
        self.my_state = SECTION_EMPTY
        self.next_section = None
        self.prev_section = None
        self.manager = None
        self.state = SECTION_BLOCKED if self.blocked else SECTION_EMPTY
        self.direction = DIR_NONE
        self.position = 0
        self.prev_position = 0
        self.try_next_sec = None
        self.terminating = False
        if self.terminus or self.hold :
            self.book_through = False
        self.stop_position = None
        self.set_sensor_listen(self.left)
        self.set_sensor_listen(self.right)
        section.sections[name] = self
        dispatcher.add_tick_client(self.tick)
        if section.first :
            section.first = False
            section.init_class()

    @staticmethod
    def enroll_type(name, factory) :
        section.types[name] = factory

    @staticmethod
    def init_class() :
        dispatcher.add_ten_second_client(section.status_reporter)

    @staticmethod
    def factory(name, **args) :
        try :
            my_type = args['type']
            del args['type']
        except KeyError :
            my_type = 'simple'
        try :
            fn = section.types[my_type]
        except KeyError :
            raise ValueError("unknown section type '%s'" % (my_type,))
        (fn)(name, **args)

    def is_booked(self) :
        return self.state in (SECTION_BOOKED, SECTION_CLEAR)

    def is_empty(self) :
        return self.state==SECTION_EMPTY

    def is_clear(self) :
        return self.state==SECTION_CLEAR

    def is_clear_for(self, t) :
        return self.state==SECTION_CLEAR \
            or (self.state>=SECTION_OCCUPIED and self.my_train==t)

    def is_leftbound(self) :
        return self.direction==DIR_LEFT

    def is_rightbound(self) :
        return self.direction==DIR_RIGHT

    def is_unoccupied(self) :
        return self.state < SECTION_OCCUPIED 

    def is_occupied(self) :
        return not self.is_unoccupied()

    def is_stopping(self) :
        return self.state==SECTION_STOPPING

    def is_continuing(self) :
        return self.state==SECTION_CONTINUING

    def is_same_direction(self, other) :
        return self.direction==other.direction

    def is_stopped(self) :
        return self.state==SECTION_STOPPED

    def get_occupancy(self) :
        if self.manager :
            return self.manager.get_occupancy(self)
        else :
            return 1 if self.is_occupied() else 0

    def get_left(self) :
        return self.left

    def get_right(self) :
        return self.right

    def is_head(self) :
        return self.is_occupied() and \
            (self.next_section is None or not self.next_section.is_occupied())

    def set_manager(self, mgr) :
        self.manager = mgr

    def get_my_train(self, dir) :
        return self.my_train

    def has_available_train(self, dir) :
        return self.is_occupied() \
                and self.my_train.is_available() \
                and (self.is_leftbound()==(dir==DIR_LEFT) \
                         or self.my_train.is_reversible())

    def set_terminating(self) :
        if not self.terminating :
            self.terminating = True
            self._log_me("terminating")

    def get_departure_end(self) :
        return self.left if self.is_leftbound() else self.right

    def get_arrival_end(self) :
        return self.right if self.is_leftbound() else self.left

    def book(self, sect, tr, dir) :
        done = result = False
        if self.manager :
            done, result = self.manager.book(self, sect, tr, dir)
        if done :
            if result :
                self.try_next_sect = self._get_next_section(sect)
            return result
        else :
            return self._book(sect, tr, dir)

    def _book(self, sect, tr, dir) :
        return self.book_base(sect, tr, dir)

    def book_base(self, sect, tr, dir) :
        result = False
        self.try_next_sec = self._get_next_section(sect)
        if self.can_book_through(sect, tr, dir) :
            self.make_booking(sect, tr, dir)
            result = True
        return result

    def can_book(self, sect, tr, dir, urgent=False) :
        done = result = False
        if self.manager :
            done, result = self.manager.can_book(self, sect, tr, dir, urgent)
        if done :
            return result
        else :
            return self._can_book(sect, tr, dir, urgent)

    def _can_book(self, sect, tr, dir, urgent) :
        return self.is_empty() and self.is_bookable(tr)

    def can_book_through(self, sect, tr, dir, urgent=False) :
        cb = self.can_book(sect, tr, dir, urgent)
        cbt = False
        assert(self.try_next_sec != self)
        if not self.hold and self.try_next_sec :
            self._log_me("can_book_through", "try_next %s", self.try_next_sec)
            cbt = self.try_next_sec.can_book_through(self, tr, dir)
        result = cb and (cbt or not self.book_through)
        return result

    def extend_booking(self) :
        if not self.is_empty() \
           and not self.hold \
           and not self.next_section \
           and self.my_train and self.my_train.is_active() :
            return self.force_extend_booking()
        else :
            return False

    def force_extend_booking(self) :
        result = False
        if self.try_next_sec is None :
            if self.direction==DIR_LEFT:
                self.try_next_sec = self.left.adjacent
            else :
                assert(self.direction==DIR_RIGHT)
                self.try_next_sec = self.right.adjacent
        if self.try_next_sec and self.try_next_sec.is_empty() :
            assert(isinstance(self.my_train, train))
            result = self.try_next_sec.book(self, self.my_train, self.direction)
            if result :
                self.next_section = self.try_next_sec
                self.try_next_sec = None
                self._log_me("extended")
        return result

    def _get_next_section(self, sect) :
        return self.right.adjacent if sect==self.left.adjacent else self.left.adjacent

    def _get_connected_end(self, sect) :
        for e in [ self.left, self.right ] :
            if sect==e.adjacent :
                return e
        return None

    def is_bookable(self, tr) :
        return tr.name not in self.exclude and \
            (self.radius is None or tr.min_radius <= self.radius)

    def make_booking(self, sect, tr, dir) :
        assert(isinstance(tr, train))
        self.my_train = tr
        self.prev_section = sect
        self.state = SECTION_BOOKED
        self.direction = dir
        self.make_booking_v()
        self._test_clear()
        self._log_me("book")

    def _test_clear(self) :
        if self.is_booked() :
            self.state = SECTION_CLEAR

    def make_booking_v(self) :
        pass

    def prepare(self, sect) :
        self.prepare_base()

    def prepare_base(self) :
        self._log_me("prepare")

    def enter(self, from_, offset=0, sensor=False) :
        if not self.is_occupied() :
            self.enter_base(from_, offset, sensor=sensor)

    def enter_base(self, from_, offset=0, sensor=False) :
        entry = self.left if self.is_rightbound() else self.right
        exit_ = self.right if self.is_rightbound() else self.left
        if sensor or (entry and entry.sensor is None) or dispatcher.is_simulated() :
            if self.is_unoccupied() :
                self.state = SECTION_OCCUPIED
                self.position = offset
                self.stop_position = self.length - exit_.sensor_offset
                prev_head = self.my_train.head
                while True :
                    next = prev_head.next_section
                    prev_head.depart()
                    if next==self :
                        break
                    prev_head = next
                    next.enter(self)
                self.my_train.set_head(self)
                self.prev_section.unhead()
                self.review_progress()
                self._log_me("enter")

    def unhead(self) :
        self.state = SECTION_LEAVING

    def review_progress(self) :
        if self.state==SECTION_STOPPING or self.state==SECTION_OCCUPIED :
            if self.terminating :
                self.state = self.TERMINATING
            elif self.next_section \
               and self.next_section.is_clear_for(self.my_train) \
               and not self.terminating :
                self.state = SECTION_CONTINUING
            else :
                self.state = SECTION_STOPPING

    def set_offset(self, offset) :
        self.position = offset

    def leave(self) :
        self.leave_base()

    def leave_base(self) :
        if self.prev_section :
            self.prev_section.leave()
        self.my_train.set_tail(self.next_section)
        self.state = SECTION_EMPTY
        self.direction = DIR_NONE
        self.my_train = None
        self.prev_section = None
        self.next_section = None
        self.leave_v()
        self._log_me("leave")

    def leave_v(self) :
        pass

    def leave_previous(self) :
        if self.prev_section :
            self.prev_section.leave()
            self.prev_section = None
            self.pre_booked_section = None

    def dispatch(self) :
        if self.manager and self.manager.dispatch(self) :
            return True
        if self.is_booked() \
           and not self.next_section \
           and random.random() < self.through_prob :
            self.force_extend_booking()

    def entry_sensor(self, end) :
        if self.prev_section :
            if self.prev_section==end.adjacent :
                self.enter(self, end.sensor_offset, sensor=True)

    def departure_sensor(self, end) :
        if self.my_train and self.my_train.is_active() :
            self.depart()

    def depart(self) :
        if self.state != SECTION_LEAVING :
            end = self.get_departure_end()
            self._log_me("departure sensor", "end %s", end)
            if self.length > self.my_train.get_length() * constants.train_length_fudge :
                self.leave_previous()
            if self.state==SECTION_STOPPING :
                if self.terminus :
                    self.state = SECTION_TERMINATED
                    self.terminate_train()
                else :
                    self.state = SECTION_STOPPED
            elif self.state==SECTION_TERMINATING :
                self.state = SECTION_TERMINATED
            else :
                self.state = SECTION_LEAVING
                self.next_section.enter(self, -end.sensor_offset)

    def set_train_speed(self, speed=None, cruise=False, slowing=False, stopping=False) :
        if self.state==SECTION_STOPPING or self.state==SECTION_TERMINATING :
            if self.position > self.stop_position - constants.stopping_margin :
                self.my_train.set_speed(stopping=True)
            else :
                self.my_train.set_speed(slowing=True)
        elif self.state==SECTION_CONTINUING :
            self.my_train.set_speed(cruise=True)
        elif self.my_state==SECTION_STARTING :
            self.my_train.set_speed(slowing=True)
        elif self.my_state==SECTION_STOPPED or self.my_state==SECTION_TERMINATED :
            self.my_train.set_speed(0)

    def terminate_train(self, do_wait=True) :
        self.terminate_train_base(do_wait)

    def terminate_train_base(self, do_wait) :
        self.state = SECTION_TERMINATED
        self.my_train.deactivate(do_wait=do_wait)

    def tick(self, duration) :
        self.tick_base(duration)

    def tick_base(self, duration) :
        self.extend_booking()
        self.update_position(duration)
        self.review_progress()
        self.set_train_speed()
        self.dispatch()

    def set_position(self, pos) :
        self.position = pos

    def update_position(self, duration) :
        self.prev_position = self.position
        if self.my_train and self.is_occupied() :
            speed = self.my_train.get_actual_speed()
            if speed > 0 :
                self.position += speed * duration * constants.scale_factor * \
                                 constants.mph2fps * constants.speed_fudge
                if self.position > self.length and self.next_section :
                    self.next_section.enter(self)
            self.review_position()

    def review_position(self) :
        self.review_position_base()

    def review_position_base(self) :
        if self.my_train :
            entry_dist = exit_dist = None
            if self.is_rightbound() :
                entry = self.left
                exit_ = self.right
            else :
                entry = self.right
                exit_ = self.left
            entry_dist = entry.sensor_offset
            exit_dist = self.length - exit_.sensor_offset
            if entry.sensor :
                if self.position >= entry_dist > self.prev_position  :
                    dispatcher.fake_sensor(entry.sensor)
            if exit_.sensor :
                if self.position >= exit_dist > self.prev_position :
                    dispatcher.fake_sensor(exit_.sensor)
            elif self.position >= self.length > self.prev_position :
                self.departure_sensor(exit_)

    def activate(self) :
        pass

    def _can_cruise(self) :
        return False

    def enliven_connections(self) :
        self.enliven_connections_v()

    def enliven_connections_v(self) :
        self.enliven_connections_base()

    def enliven_connections_base(self) :
        self.left.enliven_connections()
        self.right.enliven_connections()

    def get_opposite_end(self, adjacent_end) :
        if adjacent_end.is_left() :
            result = self.right
        else :
            result = self.left
        return result

    def set_adjacent(self, dir, sect) :
        if dir==DIR_LEFT :
            self.left.adjacent = sect
        else :
            self.right.adjacent = sect

    def set_sensor_listen(self, end) :
        if end.sensor:
            end.sensor.listen(self.sensor_listen, end)

    def sensor_listen(self, end) :
        self._log_me("sensor", "sensor %s pos %.1f", end.sensor.name, self.length-end.sensor_offset)
        if not dispatcher.is_simulated() :
            self.set_position(end.sensor_offset)
        if end==self.get_arrival_end() :
            self.entry_sensor(end)
        else :
            self.departure_sensor(end)

    def set_container(self, cont) :
        self.container = cont

    def get_top_container(self) :
        return self.container.get_top_container() if self.container else self

    @staticmethod
    def enliven(section_name) :
        return section.get(section_name) if isinstance(section_name, str) else section_name

    def enliven_m(self, section_name) :
        return section.enliven(section_name)

    @staticmethod
    def get(name) :
        try :
            return section.sections[name]
        except KeyError :
            raise KeyError("section '%s' does not exist" % (name,))

    @staticmethod
    def get_if(name) :
        try :
            return section.sections[name]
        except KeyError :
            return None

    @staticmethod
    def visit_all(fn) :
        return [ fn(section.sections[k]) for k in sorted(section.sections.keys()) ]

    @staticmethod
    def dump_all() :
        return '\n'.join(section.visit_all(section.dump))

    def _make_dcc_id(self) :
        if self.dcc_id is None :
            self.dcc_id = make_dcc_id(self.name)

    def __str__(self) :
        return self.name

    def show_state(self, value=None) :
        if value is None :
            value = self.state
        return select(value,
                      SECTION_EMPTY, "EMPTY",
                      SECTION_BLOCKED, "BLOCKED",
                      SECTION_BOOKED, "BOOKED",
                      SECTION_CLEAR, "CLEAR",
                      SECTION_OCCUPIED, "OCC",
                      SECTION_STOPPING, "STOPPING",
                      SECTION_CONTINUING, "CONT",
                      SECTION_STARTING, "START",
                      SECTION_STOPPED, "STOPPED",
                      SECTION_LEAVING, "LEAVE",
                      SECTION_TERMINATING, "TERM",
                      SECTION_TERMINATED, "TERMED",
                      "???")

    def show_dir(self, value=None) :
        if value is None :
            value = self.direction
        return select(value,
                      DIR_NONE, "NONE",
                      DIR_LEFT, "LEFT",
                      DIR_RIGHT, "RIGHT",
                      "???")

    def _log_me(self, why, extra=None, *args) :
        x = ''
        if extra :
            x = extra % args
        log(self, "%s: next %s try %s prev %s dir %s state %s train '%s' %s%s pos %.1f %s", \
            why, self.next_section, self.try_next_sec, self.prev_section, self.show_dir(), \
            self.show_state(), self.my_train, \
            "H" if self.my_train and self.my_train.head==self else "", \
            "T" if self.my_train and self.my_train.tail==self else "", \
            self.position, x)

    def _log_extra(self) :
        return ''

    def dump(self) :
        return "%s left=%s right=%s cont=%s %s" % \
            (self.name,
             self.left.show_adjacent(),
             self.right.show_adjacent(),
             self.container.name if self.container else "<None>",
             self._dump_extra())

    def _dump_extra(self) :
        return ''

    def report_status(self) :
        self._log_me("status")

    @staticmethod
    def status_reporter(x) :
        if constants.log_section_status :
            section.visit_all(section.report_status)

