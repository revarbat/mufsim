import mufsim.utils as util
from functools import cmp_to_key, total_ordering


class Item(object):
    value = 0

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return "Unknown"

    def __repr__(self):
        return str(self)


class Mark(Item):
    def __init__(self):
        super(Mark, self).__init__(0)

    def __str__(self):
        return "Mark"


@total_ordering
class DBRef(Item):
    def __str__(self):
        return "#%d" % self.value

    def __lt__(self, other):
        return self.value < other.value

    def __eq__(self, other):
        return self.value == other.value


@total_ordering
class Lock(Item):
    def __str__(self):
        return "Lock:%s" % self.value

    def __lt__(self, other):
        return self.value < other.value

    def __eq__(self, other):
        return self.value == other.value


@total_ordering
class Address(Item):
    prog = -1

    def __init__(self, value, prog):
        self.prog = prog
        super(Address, self).__init__(value)

    def __str__(self):
        return "Addr:'#%d'%d" % (self.prog, self.value)

    def __lt__(self, other):
        a = (self.prog, self.value)
        b = (other.prog, other.value)
        return (a < b)

    def __eq__(self, other):
        a = (self.prog, self.value)
        b = (other.prog, other.value)
        return (a == b)


class GlobalVar(Item):
    def __str__(self):
        return "LV%d" % self.value


class FuncVar(Item):
    def __str__(self):
        return "SV%d" % self.value


def sortcomp(a, b, nocase=False):
    if isinstance(a, type(b)):
        if isinstance(a, str) and nocase:
            a = a.upper()
            b = b.upper()
        return (a > b) - (a < b)
    if util.is_number(a) and util.is_number(b):
        return (a > b) - (a < b)
    if util.is_number(a):
        return -1
    if util.is_number(b):
        return 1
    if isinstance(a, DBRef):
        return -1
    if isinstance(b, DBRef):
        return 1
    if isinstance(a, str):
        return -1
    if isinstance(b, str):
        return 1
    return (a > b) - (a < b)


def sortcompi(a, b):
    return sortcomp(a, b, nocase=True)


def item_type_name(val):
    if type(val) in [int, float, str, list, dict]:
        val = str(type(val)).split("'")[1].title()
    else:
        val = str(type(val)).split("'")[1].split(".")[1][5:]
    return val


def item_repr(x):
    if isinstance(x, int):
        return "%d" % x
    elif isinstance(x, float):
        x = "%.12g" % x
        if "e" not in x and "." not in x and x not in ["-inf", "inf", "nan"]:
            x = "%s.0" % x
        return x
    elif isinstance(x, str):
        return util.escape_str(x)
    elif isinstance(x, list) or isinstance(x, tuple):
        out = "%d[" % len(x)
        out += ", ".join([item_repr(v) for v in x])
        out += "]"
        return out
    elif isinstance(x, dict):
        keys = sorted(list(x.keys()), key=cmp_to_key(sortcomp))
        out = "%d{" % len(x)
        out += ", ".join(
            ["%s: %s" % (item_repr(k), item_repr(x[k])) for k in keys]
        )
        out += "}"
        return out
    else:
        return str(x)


def item_repr_pretty(x, indent=""):
    subind = indent + '  '
    if isinstance(x, int):
        return "%s%d" % (indent, x)
    elif isinstance(x, float):
        x = "%.12g" % x
        if "e" in x or "." in x or x in ["-inf", "inf", "nan"]:
            return "%s%s" % (indent, x)
        else:
            return "%s%s.0" % (indent, x)
    elif isinstance(x, str):
        return "%s%s" % (indent, util.escape_str(x))
    elif isinstance(x, list) or isinstance(x, tuple):
        if not x:
            return "%s[]" % indent
        items = [
            item_repr_pretty(v, subind)
            for v in x
        ]
        return "%s[\n%s\n%s]" % (indent, ",\n".join(items), indent)
    elif isinstance(x, dict):
        if not x:
            return "%s{}" % indent
        items = [
            "%s: %s" % (
                item_repr_pretty(k, subind),
                item_repr_pretty(x[k], subind).lstrip(),
            )
            for k in sorted(list(x.keys()), key=cmp_to_key(sortcomp))
        ]
        return "%s{\n%s\n%s}" % (indent, ",\n".join(items), indent)
    else:
        return '%s%s' % (indent, str(x))


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
