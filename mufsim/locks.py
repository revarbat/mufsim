import re

from mufsim.errors import MufRuntimeError
import mufsim.gamedb as db


class LockNode(object):
    def eval(self, supp):
        return False

    @classmethod
    def parse(cls, lockstr, user):
        lockstr = lockstr.strip()
        return (None, lockstr)

    def pretty(self):
        return "???"

    def __str__(self):
        return "???"


class LockNodeObject(LockNode):
    def __init__(self, obj):
        self.dbref = db.normobj(obj)

    def eval(self, supp):
        supp = db.normobj(supp)
        if not db.validobj(self.dbref):
            return False
        if db.getobj(self.dbref).objtype == "program":
            from mufsim.stackframe import MufStackFrame
            fr = MufStackFrame()
            trig = supp  # TODO: Use consistent real trigger!
            fr.setup(self.dbref, supp, trig, "")
            fr.execute_code()
            if fr.data_depth() < 1:
                return False
            return bool(fr.data_pop())
        if self.dbref == supp:
            return True
        if self.dbref in db.getobj(supp).contents:
            return True
        return False

    @classmethod
    def parse(cls, lockstr, user):
        lockstr = lockstr.strip()
        match = re.match(r'^([^!|&():]+)(|[^:].*)$', lockstr)
        if not match:
            return (None, lockstr)
        lockstr = match.group(2)
        obj = match.group(1).strip()
        if obj == "#-1":
            obj = -1
        elif obj == "me":
            obj = db.getobj(user).dbref
        elif obj == "here":
            obj = db.getobj(user).location
        else:
            obj = db.match_from(user, obj)
            if obj == -1:
                raise MufRuntimeError("Unrecognized object.")
            elif obj == -2:
                raise MufRuntimeError("Ambiguous object.")
        return (cls(obj), lockstr)

    def pretty(self):
        if db.validobj(self.dbref):
            return str(db.getobj(self.dbref))
        return "#%d" % self.dbref

    def __str__(self):
        return "#%d" % self.dbref


class LockNodeProp(LockNode):
    def __init__(self, prop, val):
        self.prop = prop
        self.value = val

    def eval(self, supp):
        supp = db.getobj(supp)
        val = supp.getprop(self.prop)
        if val and val == self.value:
            return True
        return False

    @classmethod
    def parse(cls, lockstr, user):
        lockstr = lockstr.strip()
        match = re.match(r'^([^!|&():]+):([^!|&():]+)(.*)$', lockstr)
        if match:
            return (cls(match.group(1), match.group(2)), match.group(3))
        return (None, lockstr)

    def pretty(self):
        return str(self)

    def __str__(self):
        return "%s:%s" % (self.prop, self.value)


class LockNodeAnd(LockNode):
    def __init__(self, node1, node2):
        self.node1 = node1
        self.node2 = node2

    def eval(self, supp):
        return self.node1.eval(supp) and self.node2.eval(supp)

    @classmethod
    def parse(cls, lockstr, user):
        lockstr = lockstr.strip()
        node, lockstr = lock_parse_leaf(lockstr, user)
        if node and lockstr.startswith('&'):
            node2, lockstr = cls.parse(lockstr[1:], user)
            if node2:
                node = cls(node, node2)
        return (node, lockstr)

    def pretty(self):
        return "(%s&%s)" % (self.node1.pretty(), self.node2.pretty())

    def __str__(self):
        return "(%s&%s)" % (self.node1, self.node2)


class LockNodeOr(LockNode):
    def __init__(self, node1, node2):
        self.node1 = node1
        self.node2 = node2

    def eval(self, supp):
        return self.node1.eval(supp) or self.node2.eval(supp)

    @classmethod
    def parse(cls, lockstr, user):
        lockstr = lockstr.strip()
        node, lockstr = LockNodeAnd.parse(lockstr, user)
        if node and lockstr.startswith('|'):
            node2, lockstr = cls.parse(lockstr[1:], user)
            if node2:
                node = cls(node, node2)
        return (node, lockstr)

    def pretty(self):
        return "(%s|%s)" % (self.node1.pretty(), self.node2.pretty())

    def __str__(self):
        return "(%s|%s)" % (self.node1, self.node2)


class LockNodeNot(LockNode):
    def __init__(self, node):
        self.node = node

    def eval(self, supp):
        return not self.node.eval(supp)

    @classmethod
    def parse(cls, lockstr, user):
        lockstr = lockstr.strip()
        node = None
        if lockstr.startswith('!'):
            node, lockstr = lock_parse_leaf(lockstr[1:], user)
            if node:
                node = cls(node)
        return (node, lockstr)

    def pretty(self):
        return "!%s" % self.node.pretty()

    def __str__(self):
        return "!%s" % self.node


class LockNodeGroup(LockNode):
    def __init__(self, node):
        self.node = node

    def eval(self, supp):
        return self.node.eval(supp)

    @classmethod
    def parse(cls, lockstr, user):
        lockstr = lockstr.strip()
        node = None
        if lockstr.startswith('('):
            node, lockstr = LockNodeOr.parse(lockstr[1:], user)
            if node and not lockstr.startswith(')'):
                raise MufRuntimeError("Malformed lock string.")
        return (node, lockstr)

    def pretty(self):
        return "%s" % self.node.pretty()

    def __str__(self):
        return "%s" % self.node


def lock_parse_leaf(lockstr, user):
    lockstr = lockstr.strip()
    node, lockstr = LockNodeGroup.parse(lockstr, user)
    if not node:
        node, lockstr = LockNodeNot.parse(lockstr, user)
    if not node:
        node, lockstr = LockNodeProp.parse(lockstr, user)
    if not node:
        node, lockstr = LockNodeObject.parse(lockstr, user)
    return (node, lockstr)


def lock_parse(lockstr, user):
    node, lockstr = LockNodeOr.parse(lockstr, user)
    return node


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
