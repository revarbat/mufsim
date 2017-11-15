import copy
import mufsim.utils as util
from mufsim.errors import MufRuntimeError
from functools import cmp_to_key, total_ordering


class Item(object):
    value = 0

    def __init__(self, value):
        self.value = value

    def __nonzero__(self):
        return self.__bool__()

    def __bool__(self):
        return True

    def __str__(self):
        return "Unknown"

    def __repr__(self):
        return str(self)


@total_ordering
class Mark(Item):
    def __init__(self):
        super(Mark, self).__init__(0)

    def __bool__(self):
        return False

    def __lt__(self, other):
        return False

    def __eq__(self, other):
        return True

    def __str__(self):
        return "Mark"


@total_ordering
class DBRef(Item):
    def __str__(self):
        return "#%d" % self.value

    def __bool__(self):
        return self.value != -1

    def __lt__(self, other):
        return self.value < other.value

    def __eq__(self, other):
        return self.value == other.value


@total_ordering
class Lock(Item):
    def __str__(self):
        return "Lock:%s" % self.value

    def __bool__(self):
        return self.value is not None

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

    def __bool__(self):
        return self.value is not None

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


@total_ordering
class GlobalVar(Item):
    def __str__(self):
        return "LV%d" % self.value

    def __bool__(self):
        return True

    def __lt__(self, other):
        return self.value < other.value

    def __eq__(self, other):
        return self.value == other.value


@total_ordering
class FuncVar(Item):
    def __str__(self):
        return "SV%d" % self.value

    def __bool__(self):
        return True

    def __lt__(self, other):
        return self.value < other.value

    def __eq__(self, other):
        return self.value == other.value


@total_ordering
class MufList(Item):
    def __init__(self, val=[], pin=False):
        super(MufList, self).__init__(val)
        self.pinned = pin

    def __str__(self):
        return str(self.value)

    def __bool__(self):
        return self.value != -1

    def __len__(self):
        return len(self.value)

    def __lt__(self, other):
        return self.value < other.value

    def __eq__(self, other):
        return self.value == other.value

    def __getitem__(self, key):
        if not isinstance(key, int):
            raise MufRuntimeError("List array expects integer index.")
        return self.value[key]

    def __setitem__(self, key, val):
        if not isinstance(key, int):
            raise MufRuntimeError("List array expects integer index.")
        self.value[key] = val

    def __delitem__(self, key):
        del self.value[key]

    def __contains__(self, key):
        return key in self.value

    def __iter__(self):
        for val in self.value:
            yield val

    def keys(self):
        return range(len(self.value))

    def copy_unpinned(self):
        if self.pinned:
            return self
        return MufList(copy.copy(self.value), self.pinned)

    def set_item(self, idx, val):
        if not isinstance(idx, (int, slice)):
            raise MufRuntimeError("List array expects integer index.")
        arr = self.copy_unpinned()
        arr[idx] = val
        return arr

    def del_item(self, idx):
        if not isinstance(idx, (int, slice)):
            raise MufRuntimeError("List array expects integer index.")
        arr = self.copy_unpinned()
        del arr[idx]
        return arr


@total_ordering
class MufDict(Item):
    def __init__(self, val={}, pin=False):
        super(MufDict, self).__init__(val)
        self.pinned = pin

    def __str__(self):
        vals = [
            "{}=>{}".format(
                util.escape_str(k) if isinstance(k, str) else str(k),
                util.escape_str(self.value[k]) if isinstance(self.value[k], str) else str(self.value[k]),
            )
            for k in self.keys()
        ]
        if not vals:
            vals = ["=>"]
        return "[{}]".format(", ".join(vals))

    def __bool__(self):
        return self.value != -1

    def __len__(self):
        return len(self.value)

    def __lt__(self, other):
        return self.value < other.value

    def __eq__(self, other):
        return self.value == other.value

    def __getitem__(self, key):
        if not isinstance(key, (int, str)):
            raise MufRuntimeError("dictionary array expects integer or string index.")
        return self.value[key]

    def __setitem__(self, key, val):
        if not isinstance(key, (int, str)):
            raise MufRuntimeError("dictionary array expects integer or string index.")
        self.value[key] = val

    def __delitem__(self, key):
        del self.value[key]

    def __contains__(self, key):
        return key in self.value

    def __iter__(self):
        for key in self.keys():
            yield key

    def keys(self):
        return sorted(list(self.value.keys()), key=cmp_to_key(sortcomp))

    def copy_unpinned(self):
        if self.pinned:
            return self
        return MufDict(copy.copy(self.value), self.pinned)

    def set_item(self, idx, val):
        if not isinstance(idx, (int, str)):
            raise MufRuntimeError("Dictionary array expects integer or string index.")
        arr = self.copy_unpinned()
        arr[idx] = val
        return arr

    def del_item(self, idx):
        if not isinstance(idx, (int, str)):
            raise MufRuntimeError("Dictionary array expects integer or string index.")
        arr = self.copy_unpinned()
        del arr[idx]
        return arr


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
