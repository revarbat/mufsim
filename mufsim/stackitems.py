import mufsim.utils as util


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


class DBRef(Item):
    def __str__(self):
        return "#%d" % self.value

    def __cmp__(self, other):
        return cmp(self.value, other.value)


class Lock(Item):
    def __str__(self):
        return "Lock:%s" % self.value

    def __cmp__(self, other):
        return cmp(self.value, other.value)


class Address(Item):
    prog = -1

    def __init__(self, value, prog):
        self.prog = prog
        super(Address, self).__init__(value)

    def __str__(self):
        return "Addr:%d" % self.value

    def __cmp__(self, other):
        return cmp(
            (self.prog, self.value),
            (other.prog, other.value)
        )


class GlobalVar(Item):
    def __str__(self):
        return "LV%d" % self.value


class FuncVar(Item):
    def __str__(self):
        return "SV%d" % self.value


def sortcomp(a, b, nocase=False):
    if type(a) is type(b):
        if type(a) is str and nocase:
            a = a.upper()
            b = b.upper()
        return cmp(a, b)
    if util.is_number(a) and util.is_number(b):
        return cmp(a, b)
    if util.is_number(a):
        return -1
    if util.is_number(b):
        return 1
    if type(a) is DBRef:
        return -1
    if type(b) is DBRef:
        return 1
    if type(a) is str:
        return -1
    if type(b) is str:
        return 1
    return cmp(a, b)


def sortcompi(a, b):
    return sortcomp(a, b, nocase=True)


def item_type_name(val):
    if type(val) in [int, float, str, list, dict]:
        val = str(type(val)).split("'")[1].title()
    else:
        val = str(type(val)).split("'")[1].split(".")[1][5:]
    return val


def item_repr(x):
    if type(x) is int:
        return "%d" % x
    elif type(x) is float:
        x = "%.12g" % x
        if "e" in x or "." in x or x in ["-inf", "inf", "nan"]:
            return x
        else:
            return "%s.0" % x
    elif type(x) is str:
        return util.escape_str(x)
    elif type(x) is list or type(x) is tuple:
        out = "%d[" % len(x)
        out += ", ".join([item_repr(v) for v in x])
        out += "]"
        return out
    elif type(x) is dict:
        keys = sorted(x.keys(), cmp=sortcomp)
        out = "%d{" % len(x)
        out += ", ".join(
            ["%s: %s" % (item_repr(k), item_repr(x[k])) for k in keys]
        )
        out += "}"
        return out
    else:
        return str(x)


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
