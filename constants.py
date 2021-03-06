

#
# Central place to keep all "compile time constants"
#

yard_through_prob           = 0.0        # prob of a train going straight through a yard
yard_departure_prob         = 1        # prob that a yard will start a departure in a given dispatch
section_through_prob        = 0.25        # prob of train going straight through a dispatcher-controlled section
max_train_speed             = 50          # highest possible train speed
default_cruise_speed        = 30          # default train running speed
default_slowing_speed       = 20          # default speed when slowing to stop
default_stopping_speed      = 10          # default speed just prior to stopping
default_normal_acceleration = 8           # mph/sec (urgh)
default_normal_deceleration = 12          # mph/sec (urgh)
default_max_speed           = 40          # mph (full size)
scale_factor                = 1/20.5      # correction for scale
mph2fps                     = 22.0/15.0   # convert MPH to ft/sec
speed_fudge                 = 0.5         # fydge factor for speed
dispatch_interval           = 0.05        # seconds between real-life dispatcher runs
sensor_active_time          = 2.0         # time for a sensor to remain active once triggered
default_time_dilution       = 100         # time scaling factor for simulation
train_length_fudge          = 1.2         # over estimate of train length
default_mean_wait           = 15.0        # default mean train wait time
default_max_wait            = 40.0        # default max train wait time
stopping_margin             = 2.0         # distance before stop point to slow to stopping speed
min_speed_change_interval   = 0.5         # minimum interval between loco speed changes
default_sensor_offset       = 1           # default sensor offset if present
weibull_shape               = 1.7         # shape parameter for Weibull distribution
speed_estop                 = -1          # emergency stop command
nce_response_wait_time      = 0.2         # time to wait for response from NCE controller
log_section_status          = False       # log status for all sections every 10S
log_train_status            = False       # log status for all trains every 10S

def _set_constant(args) :
    s = [ a.strip() for a in args.split('=')]
    if len(s) != 2 :
        raise ValueError("constant definition must have form 'name=value', not '%s'" % (a,))
    try :
        c = globals()[s[1]]
    except KeyError :
        raise ValueError("unknown constant '%s'" % (s[1],))
    try :
        v = type(c)(s[2])
    except ValueError :
        raise ValueError("illegal format '%s' for value for constant '%s'" \
            % (s[2], s[1]))
    c = v

def load_string(args) :
    for a in args :
        _set_constant(a)

def load_file(f) :
    for line in f :
        l = line.strip()
        if not l.empty() and l[0] != '#' :
            _set_constant(l)
