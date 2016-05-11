import re
import sys
from numbers import Number
from collections import Set, Mapping, deque


def escape_str(s):
    out = ''
    for ch in list(s):
        if ch == "\r" or ch == "\n":
            out += "\\r"
        elif ch == "\033":
            out += "\\["
        elif ch == "\\":
            out += "\\\\"
        elif ch == '"':
            out += '\\"'
        else:
            out += ch
    return '"%s"' % out


def is_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


def is_dbref(s):
    if s[0] != '#':
        return False
    try:
        int(s[1:])
        return True
    except ValueError:
        return False


def is_float(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def is_number(s):
    return(is_int(s) or is_float(s))


def is_strlit(s):
    return s[0] == '"' and s[-1] == '"'


def smatch(pat, txt):
    pats = [
        ('{', '\b('),
        ('}', ')\b'),
        ('?', '.'),
        ('*', '.*'),
    ]
    for fnd, repl in pats:
        pat = pat.replace(fnd, repl)
    try:
        pat = re.compile(pat, re.IGNORECASE)
    except:
        return False
    if pat.search(txt):
        return True
    return False


def getsize(obj):
    """Recursively iterate to sum size of object & members."""
    try:  # Python 2
        zero_depth_bases = (basestring, Number, xrange, bytearray)
        iteritems = 'iteritems'
    except NameError:  # Python 3
        zero_depth_bases = (str, bytes, Number, range, bytearray)
        iteritems = 'items'

    def inner(obj, _seen_ids=set()):
        obj_id = id(obj)
        if obj_id in _seen_ids:
            return 0
        _seen_ids.add(obj_id)
        size = sys.getsizeof(obj)
        if isinstance(obj, zero_depth_bases):
            pass  # bypass remaining control flow and return
        elif isinstance(obj, (tuple, list, Set, deque)):
            size += sum(inner(i) for i in obj)
        elif isinstance(obj, Mapping) or hasattr(obj, iteritems):
            size += sum(
                inner(k) + inner(v)
                for k, v in getattr(obj, iteritems)()
            )
        # Now assume custom object instances
        elif hasattr(obj, '__slots__'):
            size += sum(
                inner(getattr(obj, s))
                for s in obj.__slots__
                if hasattr(obj, s)
            )
        else:
            attr = getattr(obj, '__dict__', None)
            if attr is not None:
                size += inner(attr)
        return size
    return inner(obj)


def compare_dicts(a, b):
    keys1 = sorted(list(a.keys()))
    keys2 = sorted(list(b.keys()))
    if keys1 != keys2:
        return (keys1 > keys2) - (keys1 < keys2)
    for k in keys1:
        val1 = a[k]
        val2 = b[k]
        if val1 != val2:
            return (val1 > val2) - (val1 < val2)
    return 0


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
