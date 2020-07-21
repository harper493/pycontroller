#
# load_layout - read the layout description file and create the corresponding objects
#

import re
from section import section
from locomotive import locomotive
from train import train

types = { 'sections' : section.factory, \
          'locos' : locomotive, \
          'trains' : train, \
          'positions' : (lambda n,**a : _load_position(n, **a)) }

def load_layout(f) :
    item_class = None
    lineno = 0
    line = ''
    for l in f:
        line += l.strip()
        if len(line)==0 :
            continue
        if line[-1]=='\\' :
            line = line[:-1]
            continue
        lineno += 1
        error = None
        m = re.match(r'^\s*\[(.*)\]\s*|\s*(#).|\s*(.*?)\s*:\s*(.*)\s*$', line)
        if m :
            if m.group(1) :
                item_class = m.group(1).strip()
                if item_class not in types :
                    error = "unrecognised item class '%s'" % (item_class,)
                    item_class = None
            elif not m.group(2) : # not a comment
                attr_str = [ s.strip() for s in m.group(4).split(',') ]
                attrs = {}
                for a in attr_str :
                    aa = a.split('=')
                    if len(aa)==1 :
                        attrs[aa[0].strip()] = "True"
                    elif len(aa)==2 :
                        attrs[aa[0].strip()] = aa[1].strip()
                    else :
                        error = "incorrect syntax for attribute/value pair %s" % (a,)
                if not error :
                    try :
                        (types[item_class])(m.group(3), **attrs)
                    except ValueError as err :
                        error = err
        else :
            error = "syntax error"
        if error :
            print("error in line %d: %s\n    %s" % (lineno, error, line))
        line = ''
    section.visit_all(section.enliven_connections)

def _load_position(name, **attrs) :
    t = train.get(name)
    a0 = list(attrs.keys())[0]
    m = re.match(r'^(\w+)/(\d*)([LR])$', a0)
    if m :
        sect = section.get(m.group(1))
        offset = float(m.group(2)) if m.group(2) else -1
        left = m.group(3)=='L'
        sect.position_train(t, left, offset)
    else :
        raise ValueError("'%s' is not a valid train position" % (a0,))
