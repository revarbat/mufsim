#!/usr/bin/env python

from __future__ import print_function

import os
import re
import sys
import time
import math
import copy
import random
import argparse
import readline
from subprocess import call

EMULATED_VERSION = 'Muck2.2fb6.09'
MAX_VARS = 54
HISTORY_FILE = os.path.expanduser("~/.mufsim_history")

primitives = {}
literal_handlers = []


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


fp_errors = [
    ("DIV_ZERO", "Division by zero attempted."),
    ("NAN", "Result was not a number."),
    ("IMAGINARY", "Result was imaginary."),
    ("FBOUNDS", "Floating-point inputs were infinite or out of range."),
    ("IBOUNDS", "Calculation resulted in an integer overflow."),
]
fp_error_bits = [(1 << k) for k, v in enumerate(fp_errors)]
fp_error_names = [v[0] for v in fp_errors]
fp_error_descrs = [v[1] for v in fp_errors]

player_names = {}

objects_db = {}
db_top = 0
recycled_list = []
descriptors_list = []
descriptors = {}
execution_mode = 1


class StackItem(object):
    value = 0

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return "Unknown"

    def __repr__(self):
        return str(self)


class StackMark(StackItem):
    def __init__(self):
        super(StackMark, self).__init__(0)

    def __str__(self):
        return "Mark"


class StackDBRef(StackItem):
    def __str__(self):
        return "#%d" % self.value

    def __cmp__(self, other):
        return cmp(self.value, other.value)


class StackLock(StackItem):
    def __str__(self):
        return "Lock:%s" % self.value

    def __cmp__(self, other):
        return cmp(self.value, other.value)


class StackAddress(StackItem):
    prog = -1

    def __init__(self, value, prog):
        self.prog = prog
        super(StackAddress, self).__init__(value)

    def __str__(self):
        return "Addr:%d" % self.value

    def __cmp__(self, other):
        return cmp(
            (self.prog, self.value),
            (other.prog, other.value)
        )


class StackGlobalVar(StackItem):
    def __str__(self):
        return "LV%d" % self.value


class StackFuncVar(StackItem):
    def __str__(self):
        return "SV%d" % self.value


class DBObject(object):
    def __init__(
        self, name, objtype="thing", owner=-1,
        props={}, flags="", location=-1
    ):
        global db_top
        global player_names
        self.dbref = db_top
        db_top += 1
        self.objtype = objtype
        self.name = name
        self.flags = flags
        if owner < 0:
            owner = self.dbref
        self.owner = owner
        self.location = -1
        self.contents = []
        self.exits = []
        self.links = [location] if objtype == "player" else []
        self.pennies = 0
        self.properties = props
        objects_db[self.dbref] = self
        self.moveto(location)
        self.descr = -1
        self.sources = None
        self.compiled = None
        if objtype == "player":
            player_names[self.name.lower()] = self.dbref
            self.descr = self.dbref * 2 + 1
            descriptors_list.append(self.descr)
            descriptors[self.descr] = self.dbref

    def moveto(self, dest):
        loc = self.location
        if loc >= 0:
            locobj = getobj(loc)
            if self.objtype == "exit":
                idx = locobj.exits.index(self.dbref)
                del locobj.exits[idx]
            else:
                idx = locobj.contents.index(self.dbref)
                del locobj.contents[idx]
        dest = normobj(dest)
        if dest >= 0:
            destobj = getobj(dest)
            if self.objtype == "exit":
                destobj.exits.insert(0, self.dbref)
                self.exits = dest
            else:
                destobj.contents.insert(0, self.dbref)
                self.location = dest

    def normalize_prop(self, prop):
        prop = prop.strip().lower()
        prop = re.sub(r'//*', r'/', prop)
        if not prop:
            return prop
        if prop[0] == '/':
            prop = prop[1:]
        if prop[-1] == '/':
            prop = prop[:-1]
        return prop

    def getprop(self, prop, suppress=False):
        prop = self.normalize_prop(prop)
        if prop not in self.properties:
            val = None
        else:
            val = self.properties[prop]
        if not suppress:
            if type(val) is str:
                print("GETPROP \"%s\" on #%d = %s" %
                      (prop, self.dbref, escape_str(val)))
            else:
                print("GETPROP \"%s\" on #%d = %s" % (prop, self.dbref, val))
        return val

    def setprop(self, prop, val, suppress=False):
        prop = self.normalize_prop(prop)
        self.properties[prop] = val
        if not suppress:
            if type(val) is str:
                print("SETPROP \"%s\" on #%d = %s" %
                      (prop, self.dbref, escape_str(val)))
            else:
                print("SETPROP \"%s\" on #%d = %s" % (prop, self.dbref, val))

    def delprop(self, prop):
        prop = self.normalize_prop(prop)
        print("DELPROP \"%s\" on #%d" % (prop, self.dbref))
        if prop in self.properties:
            del self.properties[prop]
        prop += '/'
        for prp in self.properties:
            prp = self.normalize_prop(prp)
            if prp.startswith(prop):
                del self.properties[prp]
                print("DELPROP \"%s\" on #%d" % (prp, self.dbref))

    def is_propdir(self, prop):
        prop = self.normalize_prop(prop)
        val = False
        prop += '/'
        for prp in self.properties:
            prp = self.normalize_prop(prp)
            if prp.startswith(prop):
                val = True
                break
        print("PROPDIR? \"%s\" on #%d = %s" % (prop, self.dbref, val))
        return val

    def next_prop(self, prop, suppress=False):
        if not prop or prop[-1] == '/':
            prop = self.normalize_prop(prop)
            if prop:
                pfx = prop + '/'
            else:
                pfx = ''
            prev = ''
        else:
            prop = self.normalize_prop(prop)
            if '/' in prop:
                pfx, prev = prop.rsplit('/', 1)
                pfx += '/'
            else:
                pfx = ''
                prev = prop
        plen = len(pfx)
        out = ''
        for prp in self.properties:
            prp = self.normalize_prop(prp)
            if prp.startswith(pfx):
                sub = prp[plen:].split('/', 1)[0]
                if sub > prev:
                    if not out or pfx + sub < out:
                        out = pfx + sub
        if not suppress:
            print("NEXTPROP \"%s\" on #%d = \"%s\"" % (prop, self.dbref, out))
        return out

    def prodir_props(self, prop):
        prop = self.normalize_prop(prop)
        if prop:
            prop += '/'
        plen = len(prop)
        out = []
        for prp in self.properties:
            prp = self.normalize_prop(prp)
            if prp.startswith(prop):
                sub = prop + prp[plen:].split('/', 1)[0]
                if sub not in out:
                    out.append(sub)
        out.sort()
        print("PROPDIRPROPS \"%s\" on #%d = %s" % (prop, self.dbref, out))
        return out

    def __repr__(self):
        return "%s(#%d)" % (self.name, self.dbref)


def normobj(obj):
    if type(obj) is DBObject:
        obj = obj.dbref
    elif type(obj) is StackDBRef:
        obj = obj.value
    return obj


def validobj(obj):
    obj = normobj(obj)
    if obj not in objects_db:
        return False
    return True


def getobj(obj):
    obj = normobj(obj)
    if obj not in objects_db:
        raise MufRuntimeError("Invalid object.")
    return objects_db[obj]


def get_content_objects(obj):
    return [getobj(x) for x in getobj(obj).contents]


def get_action_objects(obj):
    return [getobj(x) for x in getobj(obj).exits]


def get_env_objects(obj):
    obj = getobj(obj)
    if not validobj(obj.location):
        return [obj]
    out = get_env_objects(obj.location)
    out.insert(0, obj)
    return out


def ok_name(s):
    return (
        s and
        s[0] not in ['*', '$', '#'] and
        '=' not in s and
        '&' not in s and
        '|' not in s and
        '!' not in s and
        '\r' not in s and
        '\033' not in s and
        s not in ["me", "here", "home"]
    )


def ok_player_name(s):
    return (
        ok_name(s) and
        len(s) < 32 and
        '(' not in s and
        ')' not in s and
        "'" not in s and
        ',' not in s and
        ' ' not in s and
        s.strip().lower() not in player_names
    )


def match_playername(pat):
    if not pat.startswith("*"):
        return -1
    pat = pat[1:].strip().lower()
    if pat not in player_names:
        return -1
    return player_names[pat]


def match_dbref(pat):
    if not pat.startswith("#"):
        return -1
    if not is_int(pat[1:]):
        return -1
    return int(pat[1:])


def match_registered(remote, pat):
    if not pat.startswith("$"):
        return -1
    obj = -1
    for targ in get_env_objects(remote):
        val = targ.getprop("_reg/" + pat[1:])
        if val:
            if type(val) is StackDBRef:
                val = val.value
            elif type(val) is str and val[0] == '#':
                val = int(val[1:])
            if type(val) is int:
                val = val
            if validobj(val):
                obj = val
                break
    return obj


def match_exits_on(remote, pat):
    for exit in get_action_objects(remote):
        for part in exit.name.lower().split(';'):
            part = part.strip()
            if pat == part:
                return exit.dbref
    return -1


def match_env_exits(remote, pat):
    for targ in get_env_objects(remote):
        obj = match_exits_on(targ, pat)
        if obj != -1:
            return obj
    return -1


def match_content_exits(remote, pat):
    for targ in get_content_objects(remote):
        if targ.objtype == "thing":
            obj = match_exits_on(targ, pat)
            if obj != -1:
                return obj
    return -1


def match_contents(remote, pat):
    obj = -1
    for item in get_content_objects(remote):
        # TODO: use word start matches.
        if pat in item.name.lower():
            if obj == -1:
                obj = item.dbref
            else:
                return -2
    return obj


def match_from(remote, pat):
    pat = pat.strip()
    obj = match_dbref(pat)
    if obj == -1:
        obj = match_registered(remote, pat)
    if obj == -1:
        obj = match_playername(pat)
    if obj == -1:
        obj = match_content_exits(remote, pat)
    if obj == -1:
        obj = match_content_exits(getobj(remote).location, pat)
    if obj == -1:
        obj = match_env_exits(remote, pat)
    if obj == -1:
        obj = match_contents(remote, pat)
    if obj == -1:
        obj = match_contents(getobj(remote).location, pat)
    return obj


global_env = DBObject(
    name="Global Environment Room",
    objtype="room",
    owner=1,
    props={
        "_defs/.tell": "me @ swap notify",
    },
)


wizard_player = DBObject(
    name="Wizard",
    objtype="player",
    flags="W3",
    location=0,
    props={
        "sex": "male"
    },
)


main_room = DBObject(
    name="Main Room",
    objtype="room",
    location=0,
    owner=wizard_player.dbref,
)


trigger_action = DBObject(
    name="test",
    objtype="exit",
    owner=wizard_player.dbref,
    location=main_room.dbref,
)


program_object = DBObject(
    name="cmd-test",
    objtype="program",
    flags="3",
    owner=wizard_player.dbref,
    location=wizard_player.dbref,
)
trigger_action.links.append(program_object.dbref)
global_env.setprop("_reg/cmd/test", StackDBRef(program_object.dbref),
                   suppress=True)


john_doe = DBObject(
    name="John_Doe",
    objtype="player",
    flags="3",
    location=main_room.dbref,
    props={
        "sex": "male",
        "test#": 5,
        "test#/1": "This is line one.",
        "test#/2": "This is line two.",
        "test#/3": "This is line three.",
        "test#/4": "This is line four.",
        "test#/5": "This is line five.",
        "abc": "prop_abc",
        "abc/def": "prop_def",
        "abc/efg": "prop_efg",
        "abc/efg/hij": "prop_hij",
        "abc/efg/klm": "prop_klm",
        "abc/nop/qrs": "prop_qrs",
        "abc/nop/tuv": "prop_tuv",
    },
)


jane_doe = DBObject(
    name="Jane_Doe",
    objtype="player",
    flags="1",
    location=main_room.dbref,
    props={
        "sex": "female"
    },
)


thing_object = DBObject(
    name="My Thing",
    objtype="thing",
    flags="",
    location=main_room.dbref,
    props={},
)


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


def sortcomp(a, b, nocase=False):
    if type(a) is type(b):
        if type(a) is str and nocase:
            a = a.upper()
            b = b.upper()
        return cmp(a, b)
    if is_number(a) and is_number(b):
        return cmp(a, b)
    if is_number(a):
        return -1
    if is_number(b):
        return 1
    if type(a) is StackDBRef:
        return -1
    if type(b) is StackDBRef:
        return 1
    if type(a) is str:
        return -1
    if type(b) is str:
        return 1
    return cmp(a, b)


def sortcompi(a, b):
    return sortcomp(a, b, nocase=True)


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
        return escape_str(x)
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


class MufCompileError(Exception):
    pass


class MufRuntimeError(Exception):
    pass


class MufBreakExecution(Exception):
    pass


# Decorator
def instr(inst_name):
    def instr_decorator(func):
        primitives[inst_name] = func
        func.prim_name = inst_name
        return func
    return instr_decorator


class Instruction(object):
    prim_name = None

    def __init__(self, line):
        self.line = line

    def execute(self, fr):
        pass

    def compile(self, cmplr, code, src):
        cls = type(self)
        inst = cls(self.line)
        code.append(inst)
        return (False, src)

    def __str__(self):
        if self.prim_name:
            return self.prim_name.upper().strip()
        primname = str(type(self))
        primname = primname.split('.', 1)[1]
        primname = primname.split("'", 1)[0][4:]
        primname = primname.strip()
        return primname

    def __repr__(self):
        return str(self)


@instr("$abort")
class InstDollarAbort(Instruction):
    def compile(self, cmplr, code, src):
        val, src = cmplr.get_to_eol(src)
        raise MufCompileError(val)


@instr("$echo")
class InstDollarEcho(Instruction):
    def compile(self, cmplr, code, src):
        val, src = cmplr.get_to_eol(src)
        print("$ECHO: %s" % val)
        return (False, src)


@instr("$pragma")
class InstDollarPragma(Instruction):
    def compile(self, cmplr, code, src):
        val, src = cmplr.get_to_eol(src)
        return (False, src)


@instr("$language")
class InstDollarLanguage(Instruction):
    def compile(self, cmplr, code, src):
        val, src = cmplr.get_to_eol(src)
        if val.strip().lower() == '"muv"':
            raise MufCompileError("MUV needs -m flag to compile.")
        return (False, src)


@instr("$author")
class InstDollarAuthor(Instruction):
    def compile(self, cmplr, code, src):
        val, src = cmplr.get_to_eol(src)
        comp = cmplr.compiled
        getobj(comp.program).setprop("_author", val)
        return (False, src)


@instr("$note")
class InstDollarNote(Instruction):
    def compile(self, cmplr, code, src):
        val, src = cmplr.get_to_eol(src)
        comp = cmplr.compiled
        getobj(comp.program).setprop("_note", val)
        return (False, src)


@instr("$version")
class InstDollarVersion(Instruction):
    def compile(self, cmplr, code, src):
        val, line, src = cmplr.get_word(src)
        comp = cmplr.compiled
        getobj(comp.program).setprop("_version", val)
        return (False, src)


@instr("$lib-version")
class InstDollarLibVersion(Instruction):
    def compile(self, cmplr, code, src):
        val, line, src = cmplr.get_word(src)
        comp = cmplr.compiled
        getobj(comp.program).setprop("_lib-version", val)
        return (False, src)


@instr("$def")
class InstDollarDef(Instruction):
    def compile(self, cmplr, code, src):
        nam, line, src = cmplr.get_word(src)
        val, src = cmplr.get_to_eol(src)
        cmplr.defines[nam] = val
        return (False, src)


@instr("$define")
class InstDollarDefine(Instruction):
    def compile(self, cmplr, code, src):
        nam, line, src = cmplr.get_word(src)
        if "$enddef" not in src:
            raise MufCompileError("Incomplete $define for %s" % nam)
        val, src = src.split("$enddef", 1)
        cmplr.defines[nam] = val
        return (False, src)


@instr("$undef")
class InstDollarUnDef(Instruction):
    def compile(self, cmplr, code, src):
        nam, line, src = cmplr.get_word(src)
        if nam in cmplr.defines:
            del cmplr.defines[nam]
        return (False, src)


@instr("$include")
class InstDollarInclude(Instruction):
    def compile(self, cmplr, code, src):
        comp = cmplr.compiled
        targ, line, src = cmplr.get_word(src)
        if targ == "this":
            obj = comp.program
        else:
            who = getobj(comp.program).owner
            obj = match_from(who, targ)
        cmplr.include_defs_from(obj)
        return (False, src)


@instr("$pubdef")
class InstDollarPubDef(Instruction):
    def compile(self, cmplr, code, src):
        comp = cmplr.compiled
        nam, line, src = cmplr.get_word(src)
        val, src = cmplr.get_to_eol(src)
        if nam == ":":
            getobj(comp.program).delprop("_defs")
        elif not val.strip():
            getobj(comp.program).delprop("_defs/%s" % nam)
        else:
            if nam[0] == '\\':
                nam = nam[1:]
                if getobj(comp.program).getprop("_defs/%s" % nam):
                    return (False, src)
            getobj(comp.program).setprop("_defs/%s" % nam, val)
        return (False, src)


@instr("$libdef")
class InstDollarLibDef(Instruction):
    def compile(self, cmplr, code, src):
        comp = cmplr.compiled
        nam, line, src = cmplr.get_word(src)
        if nam.startswith('\\'):
            nam = nam[1:]
            if getobj(comp.program).getprop("_defs/%s" % nam):
                return (False, src)
        prog = getobj(comp.program)
        val = "#%d %s call" % (prog.dbref, escape_str(nam))
        prog.setprop("_defs/%s" % nam, val)
        return (False, src)


@instr("$cleardefs")
class InstDollarClearDefs(Instruction):
    def compile(self, cmplr, code, src):
        val, line, src = cmplr.get_word(src)
        cmplr.defines = dict(cmplr.builtin_defines)
        if val.strip().upper() != "ALL":
            cmplr.include_defs_from(0, suppress=True)
        return (False, src)


@instr("$ifdef")
class InstDollarIfDef(Instruction):
    def compile(self, cmplr, code, src):
        cond, line, src = cmplr.get_word(src, expand=False)
        istrue = True
        if '=' in cond:
            nam, val = cond.split('=', 1)
            istrue = nam in cmplr.defines and cmplr.defines[nam] == val
        elif '>' in cond:
            nam, val = cond.split('>', 1)
            istrue = nam in cmplr.defines and cmplr.defines[nam] > val
        elif '<' in cond:
            nam, val = cond.split('<', 1)
            istrue = nam in cmplr.defines and cmplr.defines[nam] < val
        else:
            istrue = cond in cmplr.defines
        if not istrue:
            src = cmplr.skip_directive_if_block(src)
        return (False, src)


@instr("$ifndef")
class InstDollarIfNDef(Instruction):
    def compile(self, cmplr, code, src):
        cond, line, src = cmplr.get_word(src, expand=False)
        istrue = True
        if '=' in cond:
            nam, val = cond.split('=', 1)
            istrue = nam in cmplr.defines and cmplr.defines[nam] == val
        elif '>' in cond:
            nam, val = cond.split('>', 1)
            istrue = nam in cmplr.defines and cmplr.defines[nam] > val
        elif '<' in cond:
            nam, val = cond.split('<', 1)
            istrue = nam in cmplr.defines and cmplr.defines[nam] < val
        else:
            istrue = cond in cmplr.defines
        if istrue:
            src = cmplr.skip_directive_if_block(src)
        return (False, src)


@instr("$ifver")
class InstDollarIfVer(Instruction):
    def compile(self, cmplr, code, src):
        comp = cmplr.compiled
        obj, line, src = cmplr.get_word(src)
        ver, line, src = cmplr.get_word(src)
        if obj == "this":
            obj = comp.program
        else:
            who = getobj(comp.program).owner
            obj = match_from(who, obj)
        istrue = True
        if not validobj(obj):
            istrue = False
        else:
            val = getobj(obj).getprop("_version")
            if not val:
                istrue = False
            else:
                istrue = val >= ver
        if not istrue:
            src = cmplr.skip_directive_if_block(src)
        return (False, src)


@instr("$ifnver")
class InstDollarIfNVer(Instruction):
    def compile(self, cmplr, code, src):
        comp = cmplr.compiled
        obj, line, src = cmplr.get_word(src)
        ver, line, src = cmplr.get_word(src)
        if obj == "this":
            obj = comp.program
        else:
            who = getobj(comp.program).owner
            obj = match_from(who, obj)
        istrue = True
        if not validobj(obj):
            istrue = False
        else:
            val = getobj(obj).getprop("_version")
            if not val:
                istrue = False
            else:
                istrue = val >= ver
        if istrue:
            src = cmplr.skip_directive_if_block(src)
        return (False, src)


@instr("$iflibver")
class InstDollarIfLibVer(Instruction):
    def compile(self, cmplr, code, src):
        comp = cmplr.compiled
        obj, line, src = cmplr.get_word(src)
        ver, line, src = cmplr.get_word(src)
        if obj == "this":
            obj = comp.program
        else:
            who = getobj(comp.program).owner
            obj = match_from(who, obj)
        istrue = True
        if not validobj(obj):
            istrue = False
        else:
            val = getobj(obj).getprop("_lib-version")
            if not val:
                istrue = False
            else:
                istrue = val >= ver
        if not istrue:
            src = cmplr.skip_directive_if_block(src)
        return (False, src)


@instr("$ifnlibver")
class InstDollarIfNLibVer(Instruction):
    def compile(self, cmplr, code, src):
        comp = cmplr.compiled
        obj, line, src = cmplr.get_word(src)
        ver, line, src = cmplr.get_word(src)
        if obj == "this":
            obj = comp.program
        else:
            who = getobj(comp.program).owner
            obj = match_from(who, obj)
        istrue = True
        if not validobj(obj):
            istrue = False
        else:
            val = getobj(obj).getprop("_lib-version")
            if not val:
                istrue = False
            else:
                istrue = val >= ver
        if istrue:
            src = cmplr.skip_directive_if_block(src)
        return (False, src)


@instr("$iflib")
class InstDollarIfLib(Instruction):
    def compile(self, cmplr, code, src):
        comp = cmplr.compiled
        obj, line, src = cmplr.get_word(src)
        if obj == "this":
            obj = comp.program
        else:
            who = getobj(comp.program).owner
            obj = match_from(who, obj)
        istrue = validobj(obj) and getobj(obj).objtype == "program"
        if not istrue:
            src = cmplr.skip_directive_if_block(src)
        return (False, src)


@instr("$ifnlib")
class InstDollarIfNLib(Instruction):
    def compile(self, cmplr, code, src):
        comp = cmplr.compiled
        obj, line, src = cmplr.get_word(src)
        if obj == "this":
            obj = comp.program
        else:
            who = getobj(comp.program).owner
            obj = match_from(who, obj)
        istrue = validobj(obj) and getobj(obj).objtype == "program"
        if istrue:
            src = cmplr.skip_directive_if_block(src)
        return (False, src)


@instr("$ifcancall")
class InstDollarIfCanCall(Instruction):
    def compile(self, cmplr, code, src):
        comp = cmplr.compiled
        obj, line, src = cmplr.get_word(src)
        pub, line, src = cmplr.get_word(src)
        if obj == "this":
            obj = comp.program
        else:
            who = getobj(comp.program).owner
            obj = match_from(who, obj)
        obj = getobj(obj)
        istrue = (
            obj.objtype == "program" and
            obj.compiled and
            obj.compiled.publics and
            pub in obj.compiled.publics
        )
        if not istrue:
            src = cmplr.skip_directive_if_block(src)
        return (False, src)


@instr("$ifncancall")
class InstDollarIfNCanCall(Instruction):
    def compile(self, cmplr, code, src):
        comp = cmplr.compiled
        obj, line, src = cmplr.get_word(src)
        pub, line, src = cmplr.get_word(src)
        if obj == "this":
            obj = comp.program
        else:
            who = getobj(comp.program).owner
            obj = match_from(who, obj)
        obj = getobj(obj)
        istrue = (
            obj.objtype == "program" and
            obj.compiled and
            obj.compiled.publics and
            pub in obj.compiled.publics
        )
        if istrue:
            src = cmplr.skip_directive_if_block(src)
        return (False, src)


@instr("$else")
class InstDollarElse(Instruction):
    def compile(self, cmplr, code, src):
        level = 0
        while True:
            if not src:
                raise MufCompileError("Incomplete $else directive block.")
            word, line, src = cmplr.get_word(src, expand=False)
            if word.startswith("$if"):
                cond, line, src = cmplr.get_word(src, expand=False)
                level += 1
            elif word == "$endif":
                if not level:
                    break
                level -= 1
            elif word == "$else":
                if not level:
                    raise MufCompileError("Multiple $else clauses.")
        return (False, src)


@instr("$endif")
class InstDollarEndif(Instruction):
    def compile(self, cmplr, code, src):
        return (False, src)


class InstPushItem(Instruction):
    value = 0

    def __init__(self, line, val):
        self.value = val
        super(InstPushItem, self).__init__(line)

    def execute(self, fr):
        fr.data_push(self.value)

    def __str__(self):
        return item_repr(self.value)


class InstGlobalVar(Instruction):
    varnum = 0
    varname = 0

    def __init__(self, line, vnum, vname):
        self.varnum = vnum
        self.varname = vname
        super(InstGlobalVar, self).__init__(line)

    def execute(self, fr):
        fr.data_push(StackGlobalVar(self.varnum))

    def __str__(self):
        return "LV%d: %s" % (self.varnum, self.varname)


class InstFuncVar(Instruction):
    varnum = 0
    varname = 0

    def __init__(self, line, vnum, vname):
        self.varnum = vnum
        self.varname = vname
        super(InstFuncVar, self).__init__(line)

    def execute(self, fr):
        fr.data_push(StackFuncVar(self.varnum))

    def __str__(self):
        return "SV%d: %s" % (self.varnum, self.varname)


@instr("jmp")
class InstJmp(Instruction):
    value = 0

    def __init__(self, line, val=0):
        self.value = val
        super(InstJmp, self).__init__(line)

    def execute(self, fr):
        addr = fr.curr_addr()
        addr = StackAddress(self.value - 1, addr.prog)
        fr.pc_set(addr)

    def __str__(self):
        return "JMP: %d" % self.value


class InstJmpIfFalse(Instruction):
    value = 0

    def __init__(self, line, val):
        self.value = val
        super(InstJmpIfFalse, self).__init__(line)

    def execute(self, fr):
        val = fr.data_pop()
        if not val:
            addr = fr.curr_addr()
            addr = StackAddress(self.value - 1, addr.prog)
            fr.pc_set(addr)

    def __str__(self):
        return "JmpIfFalse: %d" % self.value


@instr(":")
class InstFunc(Instruction):
    funcname = "Unknown"
    varcount = 0

    def __init__(self, line, funcname=None, varcount=0):
        self.funcname = funcname
        self.varcount = varcount
        super(InstFunc, self).__init__(line)

    def execute(self, fr):
        fr.check_underflow(self.varcount)
        for i in reversed(range(self.varcount)):
            fr.funcvar_set(i, fr.data_pop())

    def get_header_vars(self, cmplr, src):
        funcvars = []
        while True:
            v, line, src = cmplr.get_word(src)
            if v == ']':
                break
            if v == '--':
                if ']' not in src:
                    raise MufCompileError("Function header incomplete.")
                src = src.split(']', 1)[1]
                src = cmplr.lstrip(src)
                break
            if v in funcvars:
                raise MufCompileError("Variable already declared.")
            funcvars.append(v)
            if not src:
                raise MufCompileError("Function header incomplete.")
        return (funcvars, src)

    def compile(self, cmplr, code, src):
        if cmplr.funcname:
            raise MufCompileError(
                "Function definition incomplete: %s" % cmplr.funcname)
        funcname, line, src = cmplr.get_word(src)
        comp = cmplr.compiled
        funcvars = []
        if funcname[-1] == '[':
            funcname = funcname[:-1]
            funcvars, src = self.get_header_vars(cmplr, src)
        if comp.get_function_addr(funcname) is not None:
            raise MufCompileError("Function already declared: %s" % funcname)
        comp.add_function(funcname, len(code))
        for v in funcvars:
            comp.add_func_var(funcname, v)
        cmplr.funcname = funcname
        code.append(InstFunc(line, funcname, len(funcvars)))
        fcode, src = cmplr.compile_r(src)
        for inst in fcode:
            code.append(inst)
        cmplr.stmt_stack = []
        return (False, src)

    def __str__(self):
        return "Function: %s (%d vars)" % (self.funcname, self.varcount)


@instr(";")
class InstEndFunc(Instruction):
    def compile(self, cmplr, code, src):
        code.append(InstExit(self.line))
        cmplr.funcname = None
        cmplr.check_for_incomplete_block()
        return (True, src)


@instr("public")
class InstPublic(Instruction):
    def compile(self, cmplr, code, src):
        nam, line, src = cmplr.get_word(src)
        comp = cmplr.compiled
        if not comp.publicize_function(nam):
            raise MufCompileError("Unrecognized identifier: %s" % nam)
        print("EXPOSED '%s' AS PUBLIC" % nam)
        return (False, src)


@instr("wizcall")
class InstWizCall(Instruction):
    def compile(self, cmplr, code, src):
        # TODO: Check wizbit on call!
        nam, line, src = cmplr.get_word(src)
        comp = cmplr.compiled
        if not comp.publicize_function(nam):
            raise MufCompileError("Unrecognized identifier: %s" % nam)
        print("EXPOSED '%s' AS WIZCALL" % nam)
        return (False, src)


@instr("execute")
class InstExecute(Instruction):
    def execute(self, fr):
        addr = fr.data_pop_address()
        fr.call_push(addr, fr.caller_get())
        fr.pc_advance(-1)


@instr("call")
class InstCall(Instruction):
    def execute(self, fr):
        saddr = fr.curr_addr()
        x = fr.data_pop(StackDBRef, str)
        if type(x) is str:
            pub = x
            obj = fr.data_pop_dbref()
        else:
            pub = None
            obj = x
        obj = getobj(obj)
        if obj.objtype != "program":
            raise MufRuntimeError("Expected program object!")
        if pub:
            if pub not in obj.compiled.publics:
                raise MufRuntimeError("Unrecognized public call.")
            addr = obj.compiled.publics[pub]
        else:
            addr = obj.compiled.lastfunction
        fr.call_push(addr, saddr.prog)
        fr.pc_advance(-1)


@instr("exit")
class InstExit(Instruction):
    def execute(self, fr):
        fr.call_pop()


@instr("cancall?")
class InstCanCallP(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        pub = fr.data_pop(str)
        obj = fr.data_pop_object()
        if obj.compiled and obj.compiled.publics:
            if pub in obj.compiled.publics:
                fr.data_push(1)
                return
        fr.data_push(0)


@instr("try")
class InstTry(Instruction):
    def __init__(self, line):
        self.value = 0
        self.trycode = []
        self.detailed = False
        super(InstTry, self).__init__(line)

    def execute(self, fr):
        cnt = fr.data_pop(int)
        stacklock = fr.data_depth() - cnt
        addr = fr.curr_addr()
        addr = StackAddress(self.value, addr.prog)
        fr.catch_push(self.detailed, addr, stacklock)

    def compile(self, cmplr, code, src):
        inst = InstTry(self.line)
        cmplr.stmt_stack.append(inst)
        subcode, src = cmplr.compile_r(src)
        inst = cmplr.stmt_stack.pop()
        trycode = inst.trycode
        if not trycode:
            raise MufCompileError("Incomplete try-catch block.")
        inst.trycode = None
        trycode.append(InstJmp(self.line, len(subcode) + 1))
        inst.value = len(trycode) + 1
        code.append(inst)
        for prim in trycode:
            code.append(prim)
        for prim in subcode:
            code.append(prim)
        return (False, src)

    def __str__(self):
        return "Try: %d" % self.value


class InstTryPop(Instruction):
    def execute(self, fr):
        fr.catch_pop()


@instr("catch")
class InstCatch(Instruction):
    def compile(self, cmplr, code, src):
        if not cmplr.stmt_stack:
            raise MufCompileError("Must be inside try block. (catch)")
        inst = cmplr.stmt_stack[-1]
        if type(inst) is not InstTry:
            raise MufCompileError("Must be inside try block. (catch)")
        code.append(InstTryPop(self.line))
        inst.trycode = code[:]
        inst.detailed = False
        del code[:]
        return (False, src)


@instr("catch_detailed")
class InstCatchDetailed(Instruction):
    def compile(self, cmplr, code, src):
        if not cmplr.stmt_stack:
            raise MufCompileError("Must be inside try block. (catch_detailed)")
        inst = cmplr.stmt_stack[-1]
        if type(inst) is not InstTry:
            raise MufCompileError("Must be inside try block. (catch_detailed)")
        code.append(InstTryPop(self.line))
        inst.trycode = code[:]
        inst.detailed = True
        del code[:]
        return (False, src)


@instr("endcatch")
class InstEndCatch(Instruction):
    def compile(self, cmplr, code, src):
        if not cmplr.stmt_stack:
            raise MufCompileError("Must be inside try block. (endcatch)")
        inst = cmplr.stmt_stack[-1]
        if type(inst) is not InstTry:
            raise MufCompileError("Must be inside try block. (endcatch)")
        return (True, src)


@instr("abort")
class InstAbort(Instruction):
    def execute(self, fr):
        msg = fr.data_pop(str)
        raise MufRuntimeError(msg)


@instr("if")
class InstIf(Instruction):
    def compile(self, cmplr, code, src):
        inst = InstIf(self.line)
        cmplr.stmt_stack.append(inst)
        subcode, src = cmplr.compile_r(src)
        cmplr.stmt_stack.pop()
        bodylen = len(subcode)
        brinst = InstJmpIfFalse(self.line, len(subcode)+1)
        code.append(brinst)
        for instnum, inst in enumerate(subcode):
            if type(inst) is InstElse:
                inst = InstJmp(inst.line, bodylen - instnum)
                brinst.value = instnum + 2
            code.append(inst)
        return (False, src)


@instr("else")
class InstElse(Instruction):
    def compile(self, cmplr, code, src):
        if not cmplr.stmt_stack:
            raise MufCompileError("ELSE must be inside if block.")
        inst = cmplr.stmt_stack[-1]
        if type(inst) is not InstIf:
            raise MufCompileError("ELSE must be inside if block.")
        code.append(InstElse(self.line))
        return (False, src)


@instr("then")
class InstThen(Instruction):
    def compile(self, cmplr, code, src):
        if not cmplr.stmt_stack:
            raise MufCompileError("THEN must end an if block.")
        inst = cmplr.stmt_stack[-1]
        if type(inst) is not InstIf:
            raise MufCompileError("THEN must end an if block.")
        return (True, src)


@instr("begin")
class InstBegin(Instruction):
    def compile(self, cmplr, code, src):
        inst = InstBegin(self.line)
        cmplr.stmt_stack.append(inst)
        subcode, src = cmplr.compile_r(src)
        cmplr.stmt_stack.pop()
        bodylen = len(subcode)
        for instnum, inst in enumerate(subcode):
            if type(inst) is InstWhile:
                inst = InstJmpIfFalse(inst.line, bodylen - instnum)
            elif type(inst) is InstBreak:
                inst = InstJmp(inst.line, bodylen - instnum)
            elif type(inst) is InstContinue:
                inst = InstJmp(inst.line, -instnum)
            code.append(inst)
        return (False, src)


@instr("for")
class InstFor(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        inc = fr.data_pop(int)
        end = fr.data_pop(int)
        start = fr.data_pop(int)
        fr.loop_iter_push("for", iter(xrange(start, end + inc, inc)))

    def compile(self, cmplr, code, src):
        inst = InstFor(self.line)
        code.append(inst)
        cmplr.stmt_stack.append(inst)
        src = "__foriter__ while " + src
        subcode, src = cmplr.compile_r(src)
        cmplr.stmt_stack.pop()
        bodylen = len(subcode)
        for instnum, inst in enumerate(subcode):
            if type(inst) is InstWhile:
                inst = InstJmpIfFalse(inst.line, bodylen - instnum)
            elif type(inst) is InstBreak:
                inst = InstJmp(inst.line, bodylen - instnum)
            elif type(inst) is InstContinue:
                inst = InstJmp(inst.line, -instnum)
            code.append(inst)
        code.append(InstForPop(inst.line))
        return (False, src)


@instr("foreach")
class InstForeach(Instruction):
    def execute(self, fr):
        arr = fr.data_pop(list, dict)
        if type(arr) is list:
            arr = {k: v for k, v in enumerate(arr)}
        fr.loop_iter_push("foreach", arr.iteritems())

    def compile(self, cmplr, code, src):
        inst = InstForeach(self.line)
        code.append(inst)
        cmplr.stmt_stack.append(inst)
        src = "__foriter__ while " + src
        subcode, src = cmplr.compile_r(src)
        cmplr.stmt_stack.pop()
        bodylen = len(subcode)
        for instnum, inst in enumerate(subcode):
            if type(inst) is InstWhile:
                inst = InstJmpIfFalse(inst.line, bodylen - instnum)
            elif type(inst) is InstBreak:
                inst = InstJmp(inst.line, bodylen - instnum)
            elif type(inst) is InstContinue:
                inst = InstJmp(inst.line, -instnum)
            code.append(inst)
        code.append(InstForPop(inst.line))
        return (False, src)


@instr("__foriter__")
class InstForIter(Instruction):
    def execute(self, fr):
        typ, topiter = fr.loop_iter_top()
        try:
            if typ == "for":
                v = next(topiter)
                fr.data_push(v)
                fr.data_push(1)
            elif typ == "foreach":
                k, v = next(topiter)
                fr.data_push(k)
                fr.data_push(v)
                fr.data_push(1)
            else:
                fr.data_push(1)
        except StopIteration:
            fr.data_push(0)


@instr(" __forpop__")
class InstForPop(Instruction):
    def execute(self, fr):
        fr.loop_iter_pop()


@instr("while")
class InstWhile(Instruction):
    def compile(self, cmplr, code, src):
        loopinst = cmplr.in_loop_inst()
        if not loopinst:
            raise MufCompileError("WHILE must be inside loop.")
        code.append(InstWhile(self.line))
        return (False, src)


@instr("break")
class InstBreak(Instruction):
    def compile(self, cmplr, code, src):
        loopinst = cmplr.in_loop_inst()
        if not loopinst:
            raise MufCompileError("BREAK must be inside loop.")
        code.append(InstBreak(self.line))
        return (False, src)


@instr("continue")
class InstContinue(Instruction):
    def compile(self, cmplr, code, src):
        loopinst = cmplr.in_loop_inst()
        if not loopinst:
            raise MufCompileError("CONTINUE must be inside loop.")
        code.append(InstContinue(self.line))
        return (False, src)


@instr("repeat")
class InstRepeat(Instruction):
    def compile(self, cmplr, code, src):
        loopinst = cmplr.in_loop_inst()
        if not loopinst:
            raise MufCompileError("REPEAT must end a loop.")
        if type(cmplr.stmt_stack[-1]) is InstIf:
            raise MufCompileError("REPEAT must end a loop.")
        code.append(InstJmp(self.line, -len(code)))
        return (True, src)


@instr("until")
class InstUntil(Instruction):
    def compile(self, cmplr, code, src):
        loopinst = cmplr.in_loop_inst()
        if not loopinst:
            raise MufCompileError("UNTIL must end a loop.")
        if type(cmplr.stmt_stack[-1]) is InstIf:
            raise MufCompileError("UNTIL must end a loop.")
        code.append(InstJmpIfFalse(self.line, -len(code)))
        return (True, src)


@instr("!")
class InstBang(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        v = fr.data_pop(StackGlobalVar, StackFuncVar)
        val = fr.data_pop()
        if type(v) is StackGlobalVar:
            fr.globalvar_set(v.value, val)
        elif type(v) is StackFuncVar:
            fr.funcvar_set(v.value, val)

    def __str__(self):
        return "!"


@instr("@")
class InstAt(Instruction):
    def execute(self, fr):
        v = fr.data_pop(StackGlobalVar, StackFuncVar)
        if type(v) is StackGlobalVar:
            val = fr.globalvar_get(v.value)
            fr.data_push(val)
        elif type(v) is StackFuncVar:
            val = fr.funcvar_get(v.value)
            fr.data_push(val)

    def __str__(self):
        return "@"


@instr("+")
class InstPlus(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(int, float, StackDBRef)
        a = fr.data_pop(int, float, StackDBRef)
        makedbref = False
        if type(a) is StackDBRef:
            if type(b) is float:
                raise MufRuntimeError("Cannot add float to dbref.")
            makedbref = True
            a = a.value
        if type(b) is StackDBRef:
            if type(a) is float:
                raise MufRuntimeError("Cannot add float to dbref.")
            makedbref = True
            b = b.value
        if makedbref:
            fr.data_push(StackDBRef(a + b))
        else:
            if math.isinf(a) or math.isinf(b):
                fr.set_error("FBOUNDS")
            out = a + b
            if math.isnan(out):
                fr.set_error("NAN")
            fr.data_push(out)

    def __str__(self):
        return "+"


@instr("++")
class InstPlusPlus(Instruction):
    def execute(self, fr):
        a = fr.data_pop(int, float, StackDBRef, StackFuncVar, StackGlobalVar)
        if type(a) is StackFuncVar:
            val = fr.funcvar_get(a) + 1
            fr.funcvar_set(a, val)
        elif type(a) is StackGlobalVar:
            val = fr.globalvar_get(a) + 1
            fr.globalvar_set(a, val)
        elif type(a) is StackDBRef:
            fr.data_push(StackDBRef(a.value + 1))
        elif type(a) is int:
            fr.data_push(a + 1)
        elif type(a) is float:
            if math.isinf(a):
                fr.set_error("FBOUNDS")
            fr.data_push(a + 1)

    def __str__(self):
        return "++"


@instr("-")
class InstMinus(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(int, float, StackDBRef)
        a = fr.data_pop(int, float, StackDBRef)
        makedbref = False
        if type(a) is StackDBRef:
            if type(b) is float:
                raise MufRuntimeError("Cannot add float to dbref.")
            makedbref = True
            a = a.value
        if type(b) is StackDBRef:
            if type(a) is float:
                raise MufRuntimeError("Cannot add float to dbref.")
            makedbref = True
            b = b.value
        if makedbref:
            fr.data_push(StackDBRef(a - b))
        else:
            if math.isinf(a) or math.isinf(b):
                fr.set_error("FBOUNDS")
            out = a - b
            if math.isnan(out):
                fr.set_error("NAN")
            fr.data_push(out)

    def __str__(self):
        return "-"


@instr("--")
class InstMinusMinus(Instruction):
    def execute(self, fr):
        a = fr.data_pop(int, float, StackDBRef, StackFuncVar, StackGlobalVar)
        if type(a) is StackFuncVar:
            val = fr.funcvar_get(a) - 1
            fr.funcvar_set(a, val)
        elif type(a) is StackGlobalVar:
            val = fr.globalvar_get(a) - 1
            fr.globalvar_set(a, val)
        elif type(a) is StackDBRef:
            fr.data_push(StackDBRef(a.value + 1))
        elif type(a) is int:
            fr.data_push(a - 1)
        elif type(a) is float:
            if math.isinf(a):
                fr.set_error("FBOUNDS")
            fr.data_push(a - 1)

    def __str__(self):
        return "--"


@instr("*")
class InstTimes(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(int, float)
        a = fr.data_pop(int, float)
        if math.isinf(a) or math.isinf(b):
            fr.set_error("FBOUNDS")
        out = a * b
        if math.isnan(out):
            fr.set_error("NAN")
        fr.data_push(out)

    def __str__(self):
        return "*"


@instr("/")
class InstDivide(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(int, float)
        a = fr.data_pop(int, float)
        if math.isinf(a) or math.isinf(b):
            fr.set_error("FBOUNDS")
        out = 0
        try:
            out = a / b
            if math.isnan(out):
                fr.set_error("NAN")
        except ZeroDivisionError:
            fr.set_error("DIV_ZERO")
        fr.data_push(out)

    def __str__(self):
        return "/"


@instr("%")
class InstModulo(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(int, float)
        a = fr.data_pop(int, float)
        if math.isinf(a) or math.isinf(b):
            fr.set_error("FBOUNDS")
        out = 0
        try:
            out = a % b
            if math.isnan(out):
                fr.set_error("NAN")
        except ZeroDivisionError:
            fr.set_error("DIV_ZERO")
        fr.data_push(out)

    def __str__(self):
        return "%"


@instr("bitshift")
class InstBitShift(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(int)
        a = fr.data_pop(int)
        if b < 0:
            fr.data_push(a >> -b)
        else:
            fr.data_push(a << b)


@instr("bitor")
class InstBitOr(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(int)
        a = fr.data_pop(int)
        fr.data_push(a | b)


@instr("bitxor")
class InstBitXor(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(int)
        a = fr.data_pop(int)
        fr.data_push(a ^ b)


@instr("bitand")
class InstBitAnd(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(int)
        a = fr.data_pop(int)
        fr.data_push(a & b)


@instr("or")
class InstOr(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop()
        a = fr.data_pop()
        fr.data_push(1 if a or b else 0)


@instr("xor")
class InstXor(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop()
        a = fr.data_pop()
        fr.data_push(1 if (a and not b) or (not a and b) else 0)


@instr("and")
class InstAnd(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop()
        a = fr.data_pop()
        fr.data_push(1 if a and b else 0)


@instr("not")
class InstNot(Instruction):
    def execute(self, fr):
        a = fr.data_pop()
        if type(a) is StackDBRef:
            fr.data_push(1 if a.value == -1 else 0)
        else:
            fr.data_push(1 if not a else 0)


@instr("=")
class InstEquals(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(int, float, StackDBRef)
        a = fr.data_pop(int, float, StackDBRef)
        if type(a) is StackDBRef:
            a = a.value
        if type(b) is StackDBRef:
            b = b.value
        fr.data_push(1 if a == b else 0)

    def __str__(self):
        return "="


@instr("<")
class InstLessThan(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(int, float, StackDBRef)
        a = fr.data_pop(int, float, StackDBRef)
        if type(a) is StackDBRef:
            a = a.value
        if type(b) is StackDBRef:
            b = b.value
        fr.data_push(1 if a < b else 0)

    def __str__(self):
        return "<"


@instr("<=")
class InstLessThanOrEquals(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(int, float, StackDBRef)
        a = fr.data_pop(int, float, StackDBRef)
        if type(a) is StackDBRef:
            a = a.value
        if type(b) is StackDBRef:
            b = b.value
        fr.data_push(1 if a <= b else 0)

    def __str__(self):
        return "<="


@instr(">")
class InstGreaterThan(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(int, float, StackDBRef)
        a = fr.data_pop(int, float, StackDBRef)
        if type(a) is StackDBRef:
            a = a.value
        if type(b) is StackDBRef:
            b = b.value
        fr.data_push(1 if a > b else 0)

    def __str__(self):
        return ">"


@instr(">=")
class InstGreaterThanOrEquals(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(int, float, StackDBRef)
        a = fr.data_pop(int, float, StackDBRef)
        if type(a) is StackDBRef:
            a = a.value
        if type(b) is StackDBRef:
            b = b.value
        fr.data_push(1 if a >= b else 0)

    def __str__(self):
        return ">="


@instr("abs")
class InstAbs(Instruction):
    def execute(self, fr):
        a = fr.data_pop(int)
        fr.data_push(abs(a))


@instr("sign")
class InstSign(Instruction):
    def execute(self, fr):
        a = fr.data_pop(int)
        fr.data_push(cmp(a, 0))


# TODO: Figure out a way to implement GETSEED
@instr("setseed")
class InstSetSeed(Instruction):
    def execute(self, fr):
        s = fr.data_pop(str)
        random.seed(s[:32])


@instr("srand")
class InstSRand(Instruction):
    def execute(self, fr):
        fr.data_push(random.randint(-(2 ** 31 - 2), (2 ** 31 - 2)))


# TODO: Make RANDOM distinct from SRAND.
# Currently, both get seeded by the random.seed() call in SETSEED.
@instr("random")
class InstRandom(Instruction):
    def execute(self, fr):
        fr.data_push(random.randint(-(2 ** 31 - 2), (2 ** 31 - 2)))


@instr("float")
class InstFloat(Instruction):
    def execute(self, fr):
        i = fr.data_pop(int)
        fr.data_push(float(i))


@instr("pi")
class InstPi(Instruction):
    def execute(self, fr):
        fr.data_push(math.pi)


@instr("inf")
class InstInf(Instruction):
    def execute(self, fr):
        fr.data_push(float("Inf"))


@instr("epsilon")
class InstEpsilon(Instruction):
    def execute(self, fr):
        fr.data_push(sys.float_info.epsilon)


@instr("ftostr")
class InstFToStr(Instruction):
    def execute(self, fr):
        x = fr.data_pop(int, float)
        a = "%.11e" % x
        b = "%.11f" % x
        x = a if len(a) < len(b) else b
        if "e" in x:
            fpval, mant = x.split("e", 1)
            if "." in fpval:
                fpval = fpval.rstrip("0")
            x = fpval + "e" + mant
        fr.data_push(x)


@instr("ftostrc")
class InstFToStrC(Instruction):
    def execute(self, fr):
        x = fr.data_pop(int, float)
        fr.data_push("%.12g" % x)


@instr("strtof")
class InstStrToF(Instruction):
    def execute(self, fr):
        x = fr.data_pop(str)
        try:
            x = float(x)
        except:
            x = 0.0
        fr.data_push(x)


@instr("fabs")
class InstFabs(Instruction):
    def execute(self, fr):
        x = float(fr.data_pop(int, float))
        if x < 0.0:
            fr.data_push(-x)
        else:
            fr.data_push(x)


@instr("ceil")
class InstCeil(Instruction):
    def execute(self, fr):
        x = fr.data_pop(float)
        fr.data_push(math.ceil(x))


@instr("floor")
class InstFloor(Instruction):
    def execute(self, fr):
        x = fr.data_pop(float)
        fr.data_push(math.floor(x))


@instr("round")
class InstRound(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(int)
        a = fr.data_pop(float)
        fr.data_push(round(a, b))


@instr("fmod")
class InstFMod(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(float)
        a = fr.data_pop(float)
        fr.data_push(math.fmod(a, b))


@instr("modf")
class InstModF(Instruction):
    def execute(self, fr):
        a = fr.data_pop(float)
        if a < 0.0:
            fr.data_push(math.ceil(a))
            fr.data_push(a - math.ceil(a))
        else:
            fr.data_push(math.floor(a))
            fr.data_push(a - math.floor(a))


@instr("sqrt")
class InstSqrt(Instruction):
    def execute(self, fr):
        x = fr.data_pop(float)
        if x < 0:
            fr.set_error("IMAGINARY")
            x = 0
        else:
            if math.isinf(x):
                fr.set_error("FBOUNDS")
            x = math.sqrt(x)
            if math.isnan(x):
                fr.set_error("NAN")
        fr.data_push(x)


@instr("sin")
class InstSin(Instruction):
    def execute(self, fr):
        x = fr.data_pop(float)
        if math.isinf(x) or math.isnan(x):
            fr.set_error("FBOUNDS")
            x = 0.0
        else:
            x = math.sin(x)
        fr.data_push(x)


@instr("cos")
class InstCos(Instruction):
    def execute(self, fr):
        x = fr.data_pop(float)
        if math.isinf(x) or math.isnan(x):
            fr.set_error("FBOUNDS")
            x = 0.0
        else:
            x = math.cos(x)
        fr.data_push(x)


@instr("tan")
class InstTan(Instruction):
    def execute(self, fr):
        x = fr.data_pop(float)
        if math.isinf(x) or math.isnan(x):
            fr.set_error("FBOUNDS")
            x = 0.0
        else:
            x = math.tan(x)
        fr.data_push(x)


@instr("asin")
class InstASin(Instruction):
    def execute(self, fr):
        x = fr.data_pop(float)
        if x < -1.0 or x > 1.0:
            fr.set_error("FBOUNDS")
            x = 0.0
        else:
            x = math.asin(x)
        fr.data_push(x)


@instr("acos")
class InstACos(Instruction):
    def execute(self, fr):
        x = fr.data_pop(float)
        if x < -1.0 or x > 1.0:
            fr.set_error("FBOUNDS")
            x = 0.0
        else:
            x = math.acos(x)
        fr.data_push(x)


@instr("atan")
class InstATan(Instruction):
    def execute(self, fr):
        x = fr.data_pop(float)
        try:
            x = math.atan(x)
        except:
            fr.set_error("FBOUNDS")
            x = 0.0
        fr.data_push(x)


@instr("atan2")
class InstATan2(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        x = fr.data_pop(float)
        y = fr.data_pop(float)
        try:
            out = math.atan2(y, x)
        except:
            raise MufRuntimeError("Math domain error.")
        fr.data_push(out)


@instr("pow")
class InstPow(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        y = fr.data_pop(float)
        x = fr.data_pop(float)
        try:
            x = x ** y
        except:
            fr.set_error("FBOUNDS")
            x = 0.0
        fr.data_push(x)


@instr("exp")
class InstExp(Instruction):
    def execute(self, fr):
        x = fr.data_pop(float)
        try:
            x = math.exp(x)
        except:
            fr.set_error("FBOUNDS")
            x = 0.0
        fr.data_push(x)


@instr("log")
class InstLog(Instruction):
    def execute(self, fr):
        x = fr.data_pop(float)
        try:
            x = math.log(x)
        except:
            fr.set_error("FBOUNDS")
            x = 0.0
        fr.data_push(x)


@instr("log10")
class InstLog10(Instruction):
    def execute(self, fr):
        x = fr.data_pop(float)
        try:
            x = math.log10(x)
        except:
            fr.set_error("FBOUNDS")
            x = 0.0
        fr.data_push(x)


@instr("diff3")
class InstDiff3(Instruction):
    def execute(self, fr):
        fr.check_underflow(6)
        z2 = fr.data_pop(float)
        y2 = fr.data_pop(float)
        x2 = fr.data_pop(float)
        z1 = fr.data_pop(float)
        y1 = fr.data_pop(float)
        x1 = fr.data_pop(float)
        if math.isinf(x1) or math.isinf(y1) or math.isinf(z1):
            fr.set_error("FBOUNDS")
        if math.isinf(x2) or math.isinf(y2) or math.isinf(z2):
            fr.set_error("FBOUNDS")
        fr.data_push(x1 - x2)
        fr.data_push(y1 - y2)
        fr.data_push(z1 - z2)


@instr("dist3d")
class InstDist3D(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        z = fr.data_pop(float)
        y = fr.data_pop(float)
        x = fr.data_pop(float)
        if math.isinf(x) or math.isinf(y) or math.isinf(z):
            fr.set_error("FBOUNDS")
        fr.data_push(math.sqrt(x * x + y * y + z * z))


@instr("xyz_to_polar")
class InstXyzToPolar(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        z = fr.data_pop(float)
        y = fr.data_pop(float)
        x = fr.data_pop(float)
        if math.isinf(x) or math.isinf(y) or math.isinf(z):
            fr.set_error("FBOUNDS")
        xy = math.sqrt(x * x + y * y)
        t = math.atan2(y, x)
        p = math.atan2(z, xy)
        r = math.sqrt(x * x + y * y + z * z)
        fr.data_push(r)
        fr.data_push(t)
        fr.data_push(p)


@instr("polar_to_xyz")
class InstPolarToXyz(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        p = fr.data_pop(float)
        t = fr.data_pop(float)
        r = fr.data_pop(float)
        if math.isinf(r) or math.isinf(p) or math.isinf(t):
            fr.set_error("FBOUNDS")
        x = r * math.cos(p) * math.cos(t)
        y = r * math.cos(p) * math.sin(t)
        z = r * math.sin(p)
        fr.data_push(x)
        fr.data_push(y)
        fr.data_push(z)


@instr("frand")
class InstFRand(Instruction):
    def execute(self, fr):
        fr.data_push(random.random())


@instr("gaussian")
class InstGaussian(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        m = fr.data_pop(float)
        s = fr.data_pop(float)
        if math.isinf(s) or math.isinf(m):
            fr.set_error("FBOUNDS")
        try:
            fr.data_push(random.gauss(m, s))
        except:
            fr.data_push(m)


@instr("clear")
class InstClear(Instruction):
    def execute(self, fr):
        fr.clear_errors()


@instr("clear_error")
class InstClearError(Instruction):
    def execute(self, fr):
        x = fr.data_pop(int, str)
        if type(x) is int:
            x = fp_error_names[x]
        fr.clear_error(x)


@instr("error?")
class InstErrorP(Instruction):
    def execute(self, fr):
        fr.data_push(1 if fr.has_errors() else 0)


@instr("error_bit")
class InstErrorBit(Instruction):
    def execute(self, fr):
        errname = fr.data_pop(str)
        errnum = -1
        if errname in fp_error_names:
            errnum = fp_error_names.index(errname)
        fr.data_push(errnum)


@instr("error_name")
class InstErrorName(Instruction):
    def execute(self, fr):
        errnum = fr.data_pop(int)
        try:
            fr.data_push(fp_error_names[errnum])
        except:
            fr.data_push("")


@instr("error_num")
class InstErrorNum(Instruction):
    def execute(self, fr):
        fr.data_push(len(fp_error_names))


@instr("error_str")
class InstErrorStr(Instruction):
    def execute(self, fr):
        x = fr.data_pop(int, str)
        if type(x) is str:
            if x in fp_error_names:
                x = fp_error_names.index(x)
            else:
                x = -1
        if x >= 0:
            try:
                x = fp_error_descrs[x]
            except:
                x = ""
        else:
            x = ""
        fr.data_push(x)


@instr("is_set?")
class InstIsSetP(Instruction):
    def execute(self, fr):
        x = fr.data_pop(int, str)
        if type(x) is int:
            x = fp_error_names[x]
        fr.data_push(1 if fr.has_error(x) else 0)


@instr("set_error")
class InstSetError(Instruction):
    def execute(self, fr):
        x = fr.data_pop(int, str)
        if type(x) is int:
            x = fp_error_names[x]
        fr.set_error(x)


@instr("read_wants_blanks")
class InstReadWantsBlanks(Instruction):
    def execute(self, fr):
        fr.read_wants_blanks = True


@instr("read")
class InstRead(Instruction):
    def execute(self, fr):
        while True:
            if fr.text_entry:
                txt = fr.text_entry.pop(0)
            else:
                txt = raw_input("READ>")
            if txt or fr.read_wants_blanks:
                break
            print("Blank line ignored.")
        if txt == "@Q":
            while fr.call_stack:
                fr.call_pop()
            while fr.catch_stack:
                fr.catch_pop()
            raise MufRuntimeError("Aborting program.")
        fr.data_push(txt)


@instr("tread")
class InstTRead(Instruction):
    def execute(self, fr):
        # TODO: make real timed read.
        fr.data_pop(int)
        while True:
            if fr.text_entry:
                txt = fr.text_entry.pop(0)
            else:
                txt = raw_input("TIMED READ (@T to force timeout) >")
            if txt or fr.read_wants_blanks:
                break
            print("Blank line ignored.")
        if txt == "@T":
            print("Faking time-out.")
            fr.data_push("")
            fr.data_push(1)
        elif txt == "@Q":
            while fr.call_stack:
                fr.call_pop()
            while fr.catch_stack:
                fr.catch_pop()
            raise MufRuntimeError("Aborting program.")
        else:
            fr.data_push(txt)
            fr.data_push(0)


@instr("userlog")
class InstUserLog(Instruction):
    def execute(self, fr):
        s = fr.data_pop(str)
        msg = "%s [%s] %s: %s\n" % (
            getobj(fr.user),
            getobj(fr.program),
            time.strftime("%m/%d/%y %H/%M/%S"),
            s
        )
        with open("userlog.log", "a") as f:
            f.write(msg)
        print("USERLOG: %s" % msg)


@instr("atoi")
class InstAtoI(Instruction):
    def execute(self, fr):
        a = fr.data_pop(str)
        try:
            fr.data_push(int(a))
        except:
            fr.data_push(0)


@instr("stod")
class InstStoD(Instruction):
    def execute(self, fr):
        a = fr.data_pop(str)
        if a[0] == '#':
            a = a[1:]
        try:
            fr.data_push(StackDBRef(int(a)))
        except:
            fr.data_push(StackDBRef(-1))


@instr("intostr")
class InstIntostr(Instruction):
    def execute(self, fr):
        a = fr.data_pop(int)
        fr.data_push("%d" % a)


@instr("itoc")
class InstItoC(Instruction):
    def execute(self, fr):
        c = fr.data_pop(int)
        if c == 13 or c == 27 or c >= 32 or c < 127:
            fr.data_push("%c" % c)
        else:
            fr.data_push("")


@instr("ctoi")
class InstCtoI(Instruction):
    def execute(self, fr):
        c = ord(fr.data_pop(str)[0])
        if c == 13 or c == 27 or c >= 32 or c < 127:
            fr.data_push(c)
        else:
            fr.data_push(0)


@instr("dup")
class InstDup(Instruction):
    def execute(self, fr):
        a = fr.data_pop()
        fr.data_push(a)
        fr.data_push(a)


@instr("dupn")
class InstDupN(Instruction):
    def execute(self, fr):
        n = fr.data_pop(int)
        fr.check_underflow(n)
        for i in xrange(n):
            fr.data_push(fr.data_pick(n))


@instr("ldup")
class InstLDup(Instruction):
    def execute(self, fr):
        n = fr.data_pick(1)
        if type(n) is not int:
            raise MufRuntimeError("Expected integer argument.")
        n += 1
        fr.check_underflow(n)
        for i in xrange(n):
            fr.data_push(fr.data_pick(n))


@instr("pop")
class InstPop(Instruction):
    def execute(self, fr):
        fr.data_pop()


@instr("popn")
class InstPopN(Instruction):
    def execute(self, fr):
        n = fr.data_pop(int)
        fr.check_underflow(n)
        for i in xrange(n):
            fr.data_pop()


@instr("swap")
class InstSwap(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop()
        a = fr.data_pop()
        fr.data_push(b)
        fr.data_push(a)


@instr("rot")
class InstRot(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        a = fr.data_pull(3)
        fr.data_push(a)


@instr("rotate")
class InstRotate(Instruction):
    def execute(self, fr):
        num = fr.data_pop(int)
        fr.check_underflow(num)
        if not num:
            return
        if num < 0:
            a = fr.data_pop()
            fr.data_insert((-num) - 1, a)
        else:
            a = fr.data_pull(num)
            fr.data_push(a)


@instr("pick")
class InstPick(Instruction):
    def execute(self, fr):
        num = fr.data_pop(int)
        fr.check_underflow(num)
        if not num:
            return
        if num < 0:
            raise MufRuntimeError("Expected positive integer.")
        else:
            a = fr.data_pick(num)
            fr.data_push(a)


@instr("over")
class InstOver(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        a = fr.data_pick(2)
        fr.data_push(a)


@instr("put")
class InstPut(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        num = fr.data_pop(int)
        val = fr.data_pop()
        fr.check_underflow(num)
        if not num:
            return
        if num < 0:
            raise MufRuntimeError("Value out of range")
        else:
            fr.data_put(num, val)


@instr("reverse")
class InstReverse(Instruction):
    def execute(self, fr):
        num = fr.data_pop(int)
        fr.check_underflow(num)
        if not num:
            return
        arr = [fr.data_pop() for i in xrange(num)]
        for val in arr:
            fr.data_push(val)


@instr("lreverse")
class InstLReverse(Instruction):
    def execute(self, fr):
        num = fr.data_pop(int)
        fr.check_underflow(num)
        if not num:
            return
        arr = [fr.data_pop() for i in xrange(num)]
        for val in arr:
            fr.data_push(val)
        fr.data_push(num)


@instr("{")
class InstMark(Instruction):
    def execute(self, fr):
        fr.data_push(StackMark())


@instr("}")
class InstMarkCount(Instruction):
    def execute(self, fr):
        for i in xrange(fr.data_depth()):
            a = fr.data_pick(i + 1)
            if type(a) is StackMark:
                fr.data_pull(i + 1)
                fr.data_push(i)
                return
        raise MufRuntimeError("StackUnderflow")


@instr("notify")
class InstNotify(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        msg = fr.data_pop(str)
        who = fr.data_pop_object()
        me = fr.globalvar_get(0)
        if who.dbref == me.value:
            print("NOTIFY: %s" % msg)
        else:
            print("NOTIFY TO %s: %s" % (who, msg))


@instr("array_notify")
class InstArrayNotify(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        targs = fr.data_pop(list)
        msgs = fr.data_pop(list)
        for targ in targs:
            if type(targ) is not StackDBRef:
                raise MufRuntimeError("Expected list array of dbrefs. (2)")
        for msg in msgs:
            if type(msg) is not str:
                raise MufRuntimeError("Expected list array of strings. (1)")
            targs = [getobj(o) for o in targs]
            print("NOTIFY TO %s: %s" % (targs, msg))


@instr("notify_except")
class InstNotifyExcept(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        msg = fr.data_pop(str)
        who = fr.data_pop_dbref()
        where = fr.data_pop_object()
        if validobj(who):
            who = getobj(who)
            print("NOTIFY TO ALL IN %s EXCEPT %s: %s" % (where, who, msg))
        else:
            print("NOTIFY TO ALL IN %s: %s" % (where, msg))


@instr("notify_exclude")
class InstNotifyExclude(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        msg = fr.data_pop(str)
        pcount = fr.data_pop(int)
        fr.check_underflow(pcount + 1)
        excl = []
        for i in xrange(pcount):
            who = fr.data_pop_object()
            excl.append(StackDBRef(who.dbref))
        where = fr.data_pop_object()
        excls = [getobj(o) for o in excl if validobj(o)]
        if excls:
            print("NOTIFY TO ALL IN %s EXCEPT %s: %s" % (where, excls, msg))
        else:
            print("NOTIFY TO ALL IN %s: %s" % (where, msg))


@instr("textattr")
class InstTextAttr(Instruction):
    ATTRCODES = {
        "reset": "0",
        "bold": "1",
        "dim": "2",
        "uline": "4",
        "flash": "5",
        "reverse": "7",
        "black": "30",
        "red": "31",
        "green": "32",
        "yellow": "33",
        "blue": "34",
        "magenta": "35",
        "cyan": "36",
        "white": "37",
        "bg_black": "40",
        "bg_red": "41",
        "bg_green": "42",
        "bg_yellow": "43",
        "bg_blue": "44",
        "bg_magenta": "45",
        "bg_cyan": "46",
        "bg_white": "47",
    }

    def execute(self, fr):
        fr.check_underflow(2)
        attrs = fr.data_pop(str)
        txt = fr.data_pop(str)
        codes = []
        endcode = ""
        for attr in attrs.split(','):
            attr = attr.strip()
            if attr in self.ATTRCODES:
                codes.append(self.ATTRCODES[attr])
        if codes:
            codes = "\033[%sm" % ";".join(codes)
            endcode = "\033[0m"
        fr.data_push(codes + txt + endcode)


@instr("array_make")
class InstArrayMake(Instruction):
    def execute(self, fr):
        num = fr.data_pop(int)
        fr.check_underflow(num)
        arr = []
        for i in xrange(num):
            arr.insert(0, fr.data_pop())
        fr.data_push(arr)


@instr("array_make_dict")
class InstArrayMakeDict(Instruction):
    def execute(self, fr):
        num = fr.data_pop(int)
        fr.check_underflow(num * 2)
        d = {}
        for i in xrange(num):
            val = fr.data_pop()
            key = fr.data_pop(int, str)
            d[key] = val
        fr.data_push(d)


@instr("array_count")
class InstArrayCount(Instruction):
    def execute(self, fr):
        arr = fr.data_pop(list, dict)
        fr.data_push(len(arr))


@instr("array_compare")
class InstArrayCompare(Instruction):
    def execute(self, fr):
        arr2 = fr.data_pop(list, dict)
        arr1 = fr.data_pop(list, dict)
        fr.data_push(cmp(arr1, arr2))


@instr("array_getitem")
class InstArrayGetItem(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        key = fr.data_pop()
        arr = fr.data_pop(list, dict)
        if type(arr) is list:
            if type(key) is not int:
                fr.data_push(0)
            elif key < 0 or key >= len(arr):
                fr.data_push(0)
            else:
                fr.data_push(arr[key])
        elif type(arr) is dict:
            if key in arr:
                fr.data_push(arr[key])
            else:
                fr.data_push(0)


@instr("array_setitem")
class InstArraySetItem(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        key = fr.data_pop()
        arr = fr.data_pop(list, dict)
        val = fr.data_pop()
        if type(arr) is list:
            if type(key) is not int:
                raise MufRuntimeError("List array expects integer index.")
            elif key < 0 or key > len(arr):
                raise MufRuntimeError("Index out of array bounds.")
            else:
                arr = arr[:]
                arr[key] = val
            fr.data_push(arr)
        elif type(arr) is dict:
            if type(key) is not int and type(key) is not str:
                raise MufRuntimeError("Index must be integer or string.")
            arr = dict(arr)
            arr[key] = val
            fr.data_push(arr)


@instr("array_insertitem")
class InstArrayInsertItem(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        key = fr.data_pop()
        arr = fr.data_pop(list, dict)
        val = fr.data_pop()
        if type(arr) is list:
            if type(key) is not int:
                raise MufRuntimeError("List array expects integer index.")
            elif key < 0 or key > len(arr):
                raise MufRuntimeError("Index out of array bounds.")
            else:
                arr = arr[:]
                arr.insert(key, val)
            fr.data_push(arr)
        elif type(arr) is dict:
            if type(key) is not int and type(key) is not str:
                raise MufRuntimeError("Index must be integer or string.")
            arr = dict(arr)
            arr[key] = val
            fr.data_push(arr)


@instr("array_delitem")
class InstArrayDelItem(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        key = fr.data_pop()
        arr = fr.data_pop(list, dict)
        if type(arr) is list:
            if type(key) is not int:
                raise MufRuntimeError("List array expects integer index.")
            elif key < 0 or key > len(arr):
                raise MufRuntimeError("Index out of array bounds.")
            else:
                arr = arr[:]
                del arr[key]
            fr.data_push(arr)
        elif type(arr) is dict:
            if type(key) is not int and type(key) is not str:
                raise MufRuntimeError("Index must be integer or string.")
            arr = dict(arr)
            del arr[key]
            fr.data_push(arr)


@instr("array_appenditem")
class InstArrayAppendItem(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        arr = fr.data_pop(list)
        val = fr.data_pop()
        arr = arr[:]
        arr.append(val)
        fr.data_push(arr)


@instr("array_extract")
class InstArrayExtract(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        keys = fr.data_pop(list)
        arr = fr.data_pop(list, dict)
        if type(arr) is list:
            arr = {k: v for k, v in enumerate(arr)}
        out = {}
        for key in keys:
            if key in arr:
                out[key] = arr[key]
        fr.data_push(out)


@instr("array_getrange")
class InstArrayGetRange(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        end = fr.data_pop(int)
        st = fr.data_pop(int)
        arr = fr.data_pop(list)
        fr.data_push(arr[st:end + 1])


@instr("array_setrange")
class InstArraySetRange(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        items = fr.data_pop(list)
        st = fr.data_pop(int)
        arr = fr.data_pop(list)[:]
        for i, item in enumerate(items):
            arr[st + i] = item
        fr.data_push(arr)


@instr("array_delrange")
class InstArrayDelRange(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        end = fr.data_pop(int)
        st = fr.data_pop(int)
        arr = fr.data_pop(list)[:]
        if end >= len(arr):
            end = len(arr) - 1
        for i in xrange(st, end + 1):
            del arr[st]
        fr.data_push(arr)


@instr("array_insertrange")
class InstArrayInsertRange(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        items = fr.data_pop(list)
        st = fr.data_pop(int)
        arr = fr.data_pop(list)[:]
        if st < 0 or st > len(arr):
            raise MufRuntimeError("Index outside array bounds. (2)")
        for i, item in enumerate(items):
            arr.insert(st + i, item)
        fr.data_push(arr)


@instr("array_nested_get")
class InstArrayNestedGet(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        keys = fr.data_pop(list)
        arr = fr.data_pop(list, dict)
        for key in keys:
            if type(key) is not int and type(key) is not str:
                raise MufRuntimeError("Index must be integer or string.")
            if type(arr) is list:
                arr = {idx: val for idx, val in enumerate(arr)}
            if type(arr) is not dict:
                arr = 0
                break
            elif key not in arr:
                arr = 0
                break
            else:
                arr = arr[key]
        fr.data_push(arr)


@instr("array_nested_set")
class InstArrayNestedSet(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        keys = fr.data_pop(list)
        arr = fr.data_pop(list, dict)
        val = fr.data_pop()
        arr = copy.deepcopy(arr)
        subarr = arr
        keyslen = len(keys)
        for keynum, key in enumerate(keys):
            if type(subarr) is list:
                if type(key) is not int:
                    raise MufRuntimeError("List array expects integer index.")
                elif key < 0 or key > len(subarr):
                    raise MufRuntimeError("Index out of list array bounds.")
                if keynum < keyslen - 1:
                    if key == len(subarr):
                        subarr[key] = {}
                    subarr = subarr[key]
                else:
                    subarr[key] = val
            elif type(subarr) is dict:
                if type(key) is not int and type(key) is not str:
                    raise MufRuntimeError(
                        "Dictionary array index must be integer or string.")
                if keynum < keyslen - 1:
                    if key not in subarr:
                        subarr[key] = {}
                    subarr = subarr[key]
                else:
                    subarr[key] = val
            elif keynum < keyslen - 1:
                raise MufRuntimeError("Nested array not a list or dictionary.")
        fr.data_push(arr)


@instr("array_nested_del")
class InstArrayNestedDel(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        keys = fr.data_pop(list)
        arr = fr.data_pop(list, dict)
        arr = copy.deepcopy(arr)
        subarr = arr
        keyslen = len(keys)
        for keynum, key in enumerate(keys):
            if type(subarr) is list:
                if type(key) is not int:
                    raise MufRuntimeError("List array expects integer index.")
                elif key < 0 or key > len(subarr):
                    raise MufRuntimeError("Index out of list array bounds.")
                if keynum < keyslen - 1:
                    if key == len(subarr):
                        subarr[key] = {}
                    subarr = subarr[key]
                else:
                    del subarr[key]
            elif type(subarr) is dict:
                if type(key) is not int and type(key) is not str:
                    raise MufRuntimeError(
                        "Dictionary array index must be integer or string.")
                if keynum < keyslen - 1:
                    if key not in subarr:
                        subarr[key] = {}
                    subarr = subarr[key]
                else:
                    del subarr[key]
            elif keynum < keyslen - 1:
                raise MufRuntimeError("Nested array not a list or dictionary.")
        fr.data_push(arr)


@instr("array_keys")
class InstArrayKeys(Instruction):
    def execute(self, fr):
        arr = fr.data_pop(list, dict)
        cnt = 0
        if type(arr) is list:
            for key, val in enumerate(arr):
                fr.data_push(key)
                cnt += 1
            fr.data_push(cnt)
        elif type(arr) is dict:
            for key, val in arr.iteritems():
                fr.data_push(key)
                cnt += 1
            fr.data_push(cnt)


@instr("array_vals")
class InstArrayVals(Instruction):
    def execute(self, fr):
        arr = fr.data_pop(list, dict)
        cnt = 0
        if type(arr) is list:
            for key, val in enumerate(arr):
                fr.data_push(val)
                cnt += 1
            fr.data_push(cnt)
        elif type(arr) is dict:
            for key, val in arr.iteritems():
                fr.data_push(val)
                cnt += 1
            fr.data_push(cnt)


@instr("array_explode")
class InstArrayExplode(Instruction):
    def execute(self, fr):
        arr = fr.data_pop(list, dict)
        cnt = 0
        if type(arr) is list:
            for key, val in enumerate(arr):
                fr.data_push(key)
                fr.data_push(val)
                cnt += 1
            fr.data_push(cnt)
        elif type(arr) is dict:
            for key, val in arr.iteritems():
                fr.data_push(key)
                fr.data_push(val)
                cnt += 1
            fr.data_push(cnt)


@instr("array_join")
class InstArrayJoin(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        delim = fr.data_pop(str)
        arr = fr.data_pop(list)
        out = ""
        for idx, val in enumerate(arr):
            if idx > 0:
                out += delim
            if type(val) is str:
                out += val
            elif type(val) is int:
                out += "%d" % val
            elif type(val) is float:
                out += "%g" % val
            elif type(val) is StackDBRef:
                out += "#%d" % val.value
            elif type(val) is StackAddress:
                out += "Addr: " + val.value
            else:
                out += val
        fr.data_push(out)


@instr("array_findval")
class InstArrayFindVal(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        val = fr.data_pop()
        arr = fr.data_pop(list, dict)
        if type(arr) is list:
            arr = {k: v for k, v in enumerate(arr)}
        out = []
        for k, v in arr.iteritems():
            if v == val:
                out.append(k)
        fr.data_push(out)


@instr("array_matchkey")
class InstArrayMatchKey(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        pat = fr.data_pop(str)
        arr = fr.data_pop(list, dict)
        if type(arr) is list:
            arr = {k: v for k, v in enumerate(arr)}
        out = {}
        for k, v in arr.iteritems():
            if type(k) is str and smatch(pat, k):
                out[k] = v
        fr.data_push(out)


@instr("array_matchval")
class InstArrayMatchVal(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        pat = fr.data_pop(str)
        arr = fr.data_pop(list, dict)
        if type(arr) is list:
            arr = {k: v for k, v in enumerate(arr)}
        out = {}
        for k, v in arr.iteritems():
            if type(v) is str and smatch(pat, v):
                out[k] = v
        fr.data_push(out)


@instr("array_cut")
class InstArrayCut(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        pos = fr.data_pop(int, str)
        arr = fr.data_pop(list, dict)
        if type(arr) is list:
            if type(pos) is str:
                fr.data_push(arr[:])
                fr.data_push([])
            else:
                fr.data_push(arr[:pos])
                fr.data_push(arr[pos:])
        else:
            out1 = {}
            out2 = {}
            for k, v in arr.iteritems():
                if sortcomp(k, pos) < 0:
                    out1[k] = v
                else:
                    out2[k] = v
            fr.data_push(out1)
            fr.data_push(out2)


@instr("array_excludeval")
class InstArrayExcludeVal(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        val = fr.data_pop()
        arr = fr.data_pop(list, dict)
        if type(arr) is list:
            arr = {k: v for k, v in enumerate(arr)}
        out = []
        for k, v in arr.iteritems():
            if v != val:
                out.append(k)
        fr.data_push(out)


@instr("array_reverse")
class InstArrayReverse(Instruction):
    def execute(self, fr):
        arr = fr.data_pop(list)[:]
        arr = [x for x in reversed(arr)]
        fr.data_push(arr)


@instr("array_sort")
class InstArraySort(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        flags = fr.data_pop(int)
        arr = fr.data_pop(list)[:]
        nocase = flags & 1 != 0
        dorev = flags & 2 != 0
        doshuffle = flags & 4 != 0
        if doshuffle:
            for i in xrange(7):
                random.shuffle(arr)
        elif nocase:
            arr = sorted(arr, cmp=sortcompi, reverse=dorev)
        else:
            arr = sorted(arr, cmp=sortcomp, reverse=dorev)
        fr.data_push(arr)


@instr("array_sort_indexed")
class InstArraySortIndexed(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        idx = fr.data_pop(int, str)
        flags = fr.data_pop(int)
        arr = fr.data_pop(list)[:]
        nocase = flags & 1 != 0
        dorev = flags & 2 != 0
        doshuffle = flags & 4 != 0
        if doshuffle:
            random.shuffle(arr)
        elif nocase:
            arr = sorted(
                arr, key=lambda x: x[idx],
                cmp=sortcompi, reverse=dorev
            )
        else:
            arr = sorted(
                arr, key=lambda x: x[idx],
                cmp=sortcomp, reverse=dorev
            )
        fr.data_push(arr)


@instr("array_first")
class InstArrayFirst(Instruction):
    def execute(self, fr):
        arr = fr.data_pop(list, dict)
        if not arr:
            fr.data_push(0)
            fr.data_push(0)
        elif type(arr) is list:
            fr.data_push(0)
            fr.data_push(1)
        else:
            keys = sorted(arr.keys(), cmp=sortcomp, reverse=False)
            fr.data_push(keys[0])
            fr.data_push(1)


@instr("array_last")
class InstArrayLast(Instruction):
    def execute(self, fr):
        arr = fr.data_pop(list, dict)
        if not arr:
            fr.data_push(0)
            fr.data_push(0)
        elif type(arr) is list:
            fr.data_push(len(arr) - 1)
            fr.data_push(1)
        else:
            keys = sorted(arr.keys(), cmp=sortcomp, reverse=True)
            fr.data_push(keys[0])
            fr.data_push(1)


@instr("array_prev")
class InstArrayPrev(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        idx = fr.data_pop(int, str)
        arr = fr.data_pop(list, dict)
        if not arr:
            fr.data_push(0)
            fr.data_push(0)
            return
        if type(arr) is list:
            keys = range(len(arr))
        else:
            keys = arr.keys()
        keys = [k for k in keys if sortcomp(k, idx) < 0]
        keys = sorted(keys, cmp=sortcomp, reverse=True)
        if keys:
            fr.data_push(keys[0])
            fr.data_push(1)
        else:
            fr.data_push(0)
            fr.data_push(0)


@instr("array_next")
class InstArrayNext(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        idx = fr.data_pop(int, str)
        arr = fr.data_pop(list, dict)
        if not arr:
            fr.data_push(0)
            fr.data_push(0)
            return
        if type(arr) is list:
            keys = range(len(arr))
        else:
            keys = arr.keys()
        keys = [k for k in keys if sortcomp(k, idx) > 0]
        keys = sorted(keys, cmp=sortcomp)
        if keys:
            fr.data_push(keys[0])
            fr.data_push(1)
        else:
            fr.data_push(0)
            fr.data_push(0)


@instr("date")
class InstDate(Instruction):
    def execute(self, fr):
        when = time.localtime()
        fr.data_push(int(when.tm_mday))
        fr.data_push(int(when.tm_mon))
        fr.data_push(int(when.tm_year))


@instr("time")
class InstTime(Instruction):
    def execute(self, fr):
        when = time.localtime()
        fr.data_push(int(when.tm_sec))
        fr.data_push(int(when.tm_min))
        fr.data_push(int(when.tm_hour))


@instr("gmtoffset")
class InstGmtOffset(Instruction):
    def execute(self, fr):
        fr.data_push(-time.timezone)


@instr("force_level")
class InstForceLevel(Instruction):
    def execute(self, fr):
        # TODO: use real force level.
        fr.data_push(0)


@instr("timefmt")
class InstTimeFmt(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        when = fr.data_pop(int)
        fmt = fr.data_pop(str)
        when = time.localtime(when)
        fr.data_push(time.strftime(fmt, when))


@instr("systime")
class InstSysTime(Instruction):
    def execute(self, fr):
        fr.data_push(int(time.time()))


@instr("systime_precise")
class InstSysTimePrecise(Instruction):
    def execute(self, fr):
        fr.data_push(float(time.time()))


@instr("match")
class InstMatch(Instruction):
    def execute(self, fr):
        pat = fr.data_pop(str).lower()
        if pat == "me":
            obj = getobj(fr.user).dbref
        elif pat == "here":
            obj = getobj(getobj(fr.user).location).dbref
        elif pat == "home":
            obj = -3
        else:
            obj = match_from(getobj(fr.user), pat)
        fr.data_push(StackDBRef(obj))


@instr("rmatch")
class InstRMatch(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        pat = fr.data_pop(str).lower()
        remote = fr.data_pop_object()
        if pat == "me":
            obj = getobj(fr.user).dbref
        elif pat == "here":
            obj = getobj(getobj(fr.user).location).dbref
        elif pat == "home":
            obj = -3
        else:
            obj = match_from(remote, pat)
        fr.data_push(StackDBRef(obj))


@instr("pmatch")
class InstPMatch(Instruction):
    def execute(self, fr):
        nam = fr.data_pop(str)
        nam = nam.lower()
        if nam in player_names:
            obj = player_names[nam]
            fr.data_push(StackDBRef(obj))
        else:
            fr.data_push(StackDBRef(-1))


@instr("mode")
class InstMode(Instruction):
    def execute(self, fr):
        global execution_mode
        fr.data_push(execution_mode)


@instr("setmode")
class InstSetMode(Instruction):
    def execute(self, fr):
        mod = fr.data_pop(int)
        global execution_mode
        execution_mode = mod


@instr("name")
class InstName(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_object()
        fr.data_push(obj.name)


@instr("pennies")
class InstPennies(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_object()
        fr.data_push(obj.pennies)


@instr("addpennies")
class InstAddPennies(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        val = fr.data_pop(int)
        obj = fr.data_pop_object()
        obj.pennies += val


@instr("movepennies")
class InstMovePennies(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        val = fr.data_pop(int)
        dest = fr.data_pop_object()
        obj = fr.data_pop_object()
        obj.pennies -= val
        dest.pennies += val


@instr("unparseobj")
class InstUnparseObj(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_object()
        if obj.objtype == "program":
            typflag = "F"
        elif obj.objtype == "thing":
            typflag = ""
        else:
            typflag = obj.objtype.upper()[0]
        flags = "".join(sorted(list(obj.flags)))
        flags = flags.replace('1', 'M1').replace('2', 'M2').replace('3', 'M3')
        fr.data_push("%s(#%s%s%s)" % (obj.name, obj.dbref, typflag, flags))


@instr("setname")
class InstSetName(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        nam = fr.data_pop(str)
        obj = fr.data_pop_object()
        obj.name = nam


@instr("name-ok?")
class InstNameOkP(Instruction):
    def execute(self, fr):
        nam = fr.data_pop(str)
        fr.data_push(1 if ok_name(nam) else 0)


@instr("pname-ok?")
class InstPNameOkP(Instruction):
    def execute(self, fr):
        nam = fr.data_pop(str)
        fr.data_push(1 if ok_player_name(nam) else 0)


@instr("ext-name-ok?")
class InstExtNameOkP(Instruction):
    def execute(self, fr):
        obj = fr.data_pop(str, StackDBRef)
        nam = fr.data_pop(str)
        if type(obj) is StackDBRef:
            typ = getobj(obj).objtype
        else:
            typ = obj
        if typ == "player":
            fr.data_push(1 if ok_player_name(nam) else 0)
        else:
            fr.data_push(1 if ok_name(nam) else 0)


@instr("set")
class InstSet(Instruction):
    def execute(self, fr):
        flg = fr.data_pop(str)
        obj = fr.data_pop_object()
        flg = flg.strip().upper()[0]
        if flg not in obj.flags:
            obj.flags += flg


@instr("flag?")
class InstFlagP(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        flg = fr.data_pop(str)
        obj = fr.data_pop_object()
        flg = flg.strip().upper()[0]
        ret = 1 if flg in obj.flags else 0
        fr.data_push(ret)


@instr("mlevel")
class InstMLevel(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_object()
        flags = obj.flags.upper()
        if "W" in flags:
            fr.data_push(4)
        elif "3" in flags:
            fr.data_push(3)
        elif "2" in flags:
            fr.data_push(2)
        elif "1" in flags or "M" in flags:
            fr.data_push(1)
        else:
            fr.data_push(0)


@instr("owner")
class InstOwner(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_object()
        fr.data_push(StackDBRef(obj.owner))


@instr("setown")
class InstSetOwn(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        newowner = fr.data_pop_object()
        obj = fr.data_pop_object()
        if newowner.objtype != "player":
            raise MufRuntimeError("Expected player dbref.")
        obj.owner = newowner.dbref


@instr("contents")
class InstContents(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_object()
        if obj.contents:
            fr.data_push(StackDBRef(obj.contents[0]))
        else:
            fr.data_push(StackDBRef(-1))


@instr("contents_array")
class InstContentsArray(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_object()
        arr = [StackDBRef(x) for x in obj.contents]
        fr.data_push(arr)


@instr("moveto")
class InstMoveTo(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        dest = fr.data_pop_object()
        obj = fr.data_pop_object()
        obj.moveto(dest)


@instr("force")
class InstForce(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        cmd = fr.data_pop(str)
        obj = fr.data_pop_object()
        print("FORCE %s(#%d) TO DO: %s" % (obj.name, obj.dbref, cmd))
        # TODO: Real forcing!  (pipe dream)
        # obj.force(cmd)


@instr("exits")
class InstExits(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_object()
        if obj.exits:
            fr.data_push(StackDBRef(obj.exits[0]))
        else:
            fr.data_push(StackDBRef(-1))


@instr("exits_array")
class InstExitsArray(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_object()
        arr = [StackDBRef(x) for x in obj.exits]
        fr.data_push(arr)


@instr("next")
class InstNext(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_object()
        loc = obj.location
        if loc < 0:
            fr.data_push(StackDBRef(-1))
            return
        if obj.objtype == "exit":
            arr = getobj(loc).exits
        else:
            arr = getobj(loc).contents
        if obj.dbref not in arr:
            print("arr=%s" % arr)
            raise MufRuntimeError("DB inconsistent!")
        idx = arr.index(obj.dbref)
        if idx == len(arr) - 1:
            fr.data_push(StackDBRef(-1))
        else:
            fr.data_push(StackDBRef(arr[idx + 1]))


@instr("caller")
class InstCaller(Instruction):
    def execute(self, fr):
        fr.data_push(fr.caller_get())


@instr("prog")
class InstProg(Instruction):
    def execute(self, fr):
        fr.data_push(fr.program)


@instr("trig")
class InstTrig(Instruction):
    def execute(self, fr):
        fr.data_push(fr.trigger)


@instr("cmd")
class InstCmd(Instruction):
    def execute(self, fr):
        fr.data_push(fr.command)


@instr("dbtop")
class InstDBTop(Instruction):
    def execute(self, fr):
        fr.data_push(db_top)


@instr("location")
class InstLocation(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_object()
        fr.data_push(StackDBRef(obj.location))


@instr("setlink")
class InstSetLink(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        dest = fr.data_pop_object()
        obj = fr.data_pop_object()
        obj.links = [dest.dbref]


@instr("setlinks_array")
class InstSetLinksArray(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        dests = fr.data_pop(list)
        obj = fr.data_pop_object()
        for dest in dests:
            if type(dest) is not StackDBRef:
                raise MufRuntimeError("Expected list array of dbrefs.")
        obj.links = [getobj(dest).dbref for dest in dests]


@instr("getlink")
class InstGetLink(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_object()
        fr.data_push(StackDBRef(obj.links[0]))


@instr("getlinks")
class InstGetLinks(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_object()
        for link in obj.links:
            fr.data_push(StackDBRef(link))
        fr.data_push(len(obj.links))


@instr("getlinks_array")
class InstGetLinksArray(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_object()
        fr.data_push([StackDBRef(x) for x in obj.links])


@instr("ok?")
class InstOkP(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_dbref()
        if not validobj(obj):
            fr.data_push(0)
        elif getobj(obj).objtype == "garbage":
            fr.data_push(0)
        else:
            fr.data_push(1)


@instr("player?")
class InstPlayerP(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_dbref()
        if not validobj(obj):
            fr.data_push(0)
        elif getobj(obj).objtype == "player":
            fr.data_push(1)
        else:
            fr.data_push(0)


@instr("room?")
class InstRoomP(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_dbref()
        if not validobj(obj):
            fr.data_push(0)
        elif getobj(obj).objtype == "room":
            fr.data_push(1)
        else:
            fr.data_push(0)


@instr("exit?")
class InstExitP(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_dbref()
        if not validobj(obj):
            fr.data_push(0)
        elif getobj(obj).objtype == "exit":
            fr.data_push(1)
        else:
            fr.data_push(0)


@instr("program?")
class InstProgramP(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_dbref()
        if not validobj(obj):
            fr.data_push(0)
        elif getobj(obj).objtype == "program":
            fr.data_push(1)
        else:
            fr.data_push(0)


@instr("thing?")
class InstThingP(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_dbref()
        if not validobj(obj):
            fr.data_push(0)
        elif getobj(obj).objtype == "thing":
            fr.data_push(1)
        else:
            fr.data_push(0)


@instr("controls")
class InstControls(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        obj = fr.data_pop_object()
        who = fr.data_pop_object()
        if obj.owner == who.dbref:
            fr.data_push(1)
        elif "W" in who.flags:
            fr.data_push(1)
        else:
            fr.data_push(0)


@instr("awake?")
class InstAwakeP(Instruction):
    def execute(self, fr):
        who = fr.data_pop_object()
        fr.data_push(1 if who.dbref in descriptors.values() else 0)


@instr("online")
class InstOnline(Instruction):
    def execute(self, fr):
        for descr in descriptors_list:
            fr.data_push(StackDBRef(descriptors[descr]))
        fr.data_push(len(descriptors_list))


@instr("online_array")
class InstOnlineArray(Instruction):
    def execute(self, fr):
        out = [StackDBRef(descriptors[descr]) for descr in descriptors_list]
        fr.data_push(out)


@instr("concount")
class InstConCount(Instruction):
    def execute(self, fr):
        fr.data_push(len(descriptors_list))


@instr("condbref")
class InstConDBRef(Instruction):
    def execute(self, fr):
        con = fr.data_pop(int)
        try:
            descr = descriptors_list[con]
            fr.data_push(StackDBRef(descriptors[descr]))
        except:
            fr.data_push(StackDBRef(-1))


@instr("contime")
class InstConTime(Instruction):
    def execute(self, fr):
        con = fr.data_pop(int)
        try:
            descr = descriptors_list[con]
            # TODO: Generate real connection times.
            fr.data_push(descr * 731 + 1)
        except:
            fr.data_push(0)


@instr("conidle")
class InstConIdle(Instruction):
    def execute(self, fr):
        con = fr.data_pop(int)
        try:
            descr = descriptors_list[con]
            # TODO: Generate real idle times.
            fr.data_push(descr * 79 + 1)
        except:
            fr.data_push(0)


@instr("conuser")
class InstConUser(Instruction):
    def execute(self, fr):
        con = fr.data_pop(int)
        try:
            descr = descriptors_list[con]
            who = descriptors[descr]
            fr.data_push(getobj(who).name)
        except:
            fr.data_push("")


@instr("conhost")
class InstConHost(Instruction):
    def execute(self, fr):
        con = fr.data_pop(int)
        try:
            descr = descriptors_list[con]
            fr.data_push("host%d.remotedomain.com" % descr)
        except:
            fr.data_push("")


@instr("conboot")
class InstConBoot(Instruction):
    def execute(self, fr):
        con = fr.data_pop(int)
        if con >= 0 and con < len(descriptors_list):
            descr = descriptors_list[con]
            who = descriptors[descr]
            del descriptors_list[con]
            del descriptors[descr]
            print("BOOTED DESCRIPTOR %d: %s" % (descr, getobj(who)))


@instr("connotify")
class InstConNotify(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        msg = fr.data_pop(str)
        con = fr.data_pop(int)
        if con >= 0 and con < len(descriptors_list):
            descr = descriptors_list[con]
            who = descriptors[descr]
            print("NOTIFY TO DESCR %d, USER %s: %s" %
                  (descr, getobj(who), msg))


@instr("condescr")
class InstConDescr(Instruction):
    def execute(self, fr):
        con = fr.data_pop(int)
        try:
            descr = descriptors_list[con]
            fr.data_push(descr)
        except:
            fr.data_push(-1)


@instr("descriptors")
class InstDescriptors(Instruction):
    def execute(self, fr):
        who = fr.data_pop_dbref()
        if who.value == -1:
            descrs = descriptors_list
        else:
            if getobj(who).objtype != "player":
                raise MufRuntimeError("Expected #-1 or player dbref.")
            descrs = [
                d for d in descriptors_list if descriptors[d] == who.value
            ]
        for descr in descrs:
            fr.data_push(descr)
        fr.data_push(len(descrs))


@instr("descr_array")
class InstDescrArray(Instruction):
    def execute(self, fr):
        who = fr.data_pop_dbref()
        if who.value == -1:
            descrs = descriptors_list
        else:
            if getobj(who).objtype != "player":
                raise MufRuntimeError("Expected #-1 or player dbref.")
            descrs = [
                d for d in descriptors_list if descriptors[d] == who.value
            ]
        fr.data_push(descrs)


@instr("descrcon")
class InstDescrCon(Instruction):
    def execute(self, fr):
        descr = fr.data_pop(int)
        if descr in descriptors_list:
            fr.data_push(descriptors_list.index(descr))
        else:
            fr.data_push(-1)


@instr("descrdbref")
class InstDescrDBRef(Instruction):
    def execute(self, fr):
        descr = fr.data_pop(int)
        if descr in descriptors:
            who = descriptors[descr]
            fr.data_push(StackDBRef(who))
        else:
            fr.data_push(StackDBRef(-1))


@instr("descr_setuser")
class InstDescrSetUser(Instruction):
    def execute(self, fr):
        pw = fr.data_pop(str)
        who = fr.data_pop_object()
        descr = fr.data_pop(int)
        if descr in descriptors:
            was = descriptors[descr]
            descriptors[descr] = who.dbref
            print("BOOTED DESCRIPTOR %d: %s" % (descr, getobj(was)))
            # TODO: actually check password?
            print("RECONNECTED DESCRIPTOR %d TO %s USING PW '%s'" %
                  (descr, who, pw))


@instr("descrboot")
class InstDescrBoot(Instruction):
    def execute(self, fr):
        descr = fr.data_pop(int)
        if descr in descriptors:
            who = descriptors[descr]
            descriptors_list.remove(descr)
            del descriptors[descr]
            print("BOOTED DESCRIPTOR %d: %s" % (descr, getobj(who)))


@instr("descrnotify")
class InstDescrNotify(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        msg = fr.data_pop(str)
        descr = fr.data_pop(int)
        if descr in descriptors:
            who = descriptors[descr]
            print("NOTIFY TO DESCR %d, %s: %s" %
                  (descr, getobj(who), msg))


@instr("descrflush")
class InstDescrFlush(Instruction):
    def execute(self, fr):
        descr = fr.data_pop(int)
        if descr == -1:
            for descr in descriptors_list:
                who = descriptors[descr]
                print("DESCRFLUSH %d, %s" %
                      (descr, getobj(who)))
        elif descr in descriptors:
            who = descriptors[descr]
            print("DESCRFLUSH %d, %s" % (descr, getobj(who)))


@instr("descr")
class InstDescr(Instruction):
    def execute(self, fr):
        fr.data_push(getobj(fr.user).descr)


@instr("firstdescr")
class InstFirstDescr(Instruction):
    def execute(self, fr):
        who = fr.data_pop_dbref()
        for descr in descriptors_list:
            if who.value == -1 or descriptors[descr] == who.value:
                fr.data_push(descr)
                return
        fr.data_push(0)


@instr("lastdescr")
class InstLastDescr(Instruction):
    def execute(self, fr):
        who = fr.data_pop_dbref()
        for descr in reversed(descriptors_list):
            if who.value == -1 or descriptors[descr] == who.value:
                fr.data_push(descr)
                return
        fr.data_push(0)


@instr("nextdescr")
class InstNextDescr(Instruction):
    def execute(self, fr):
        descr = fr.data_pop(int)
        if descr in descriptors:
            pos = descriptors_list.index(descr) + 1
            if pos >= len(descriptors_list):
                fr.data_push(0)
            else:
                fr.data_push(descriptors_list[pos])
        else:
            fr.data_push(0)


@instr("descrbufsize")
class InstDescrBufSize(Instruction):
    def execute(self, fr):
        descr = fr.data_pop(int)
        if descr in descriptors:
            fr.data_push(4096)
        else:
            fr.data_push(0)


@instr("descrsecure?")
class InstDescrSecureP(Instruction):
    def execute(self, fr):
        descr = fr.data_pop(int)
        if descr in descriptors:
            who = descriptors[descr]
            fr.data_push(who % 2)
        else:
            fr.data_push(0)


@instr("descruser")
class InstDescrUser(Instruction):
    def execute(self, fr):
        descr = fr.data_pop(int)
        if descr in descriptors:
            who = descriptors[descr]
            fr.data_push(getobj(who).name)
        else:
            fr.data_push("")


@instr("descrhost")
class InstDescrHost(Instruction):
    def execute(self, fr):
        descr = fr.data_pop(int)
        if descr in descriptors:
            fr.data_push("host%d.remotedomain.com" % descr)
        else:
            fr.data_push("")


@instr("descrtime")
class InstDescrTime(Instruction):
    def execute(self, fr):
        descr = fr.data_pop(int)
        if descr in descriptors:
            fr.data_push(descr * 731 + 1)
        else:
            fr.data_push(0)


@instr("descridle")
class InstDescrIdle(Instruction):
    def execute(self, fr):
        descr = fr.data_pop(int)
        if descr in descriptors:
            # TODO: Generate real idle times.
            fr.data_push(descr * 79 + 1)
        else:
            fr.data_push(0)


@instr("descrleastidle")
class InstDescrLeastIdle(Instruction):
    def execute(self, fr):
        who = fr.data_pop_object()
        descrs = [k for k, v in descriptors.iteritems() if v == who.dbref]
        # TODO: Generate real idle times.
        idles = [descr * 79 + 1 for descr in descrs]
        fr.data_push(min(idles))


@instr("descrmostidle")
class InstDescrMostIdle(Instruction):
    def execute(self, fr):
        who = fr.data_pop_object()
        descrs = [k for k, v in descriptors.iteritems() if v == who.dbref]
        # TODO: Generate real idle times.
        idles = [descr * 79 + 1 for descr in descrs]
        fr.data_push(max(idles))


@instr("lvar")
class InstLVar(Instruction):
    def compile(self, cmplr, code, src):
        vname, line, src = cmplr.get_word(src)
        comp = cmplr.compiled
        if not vname:
            raise MufCompileError("Variable declaration incomplete.")
        if comp.get_global_var(vname):
            raise MufCompileError("Variable already declared.")
        comp.add_global_var(vname)
        return (False, src)


@instr("var")
class InstVar(Instruction):
    def compile(self, cmplr, code, src):
        vname, line, src = cmplr.get_word(src)
        comp = cmplr.compiled
        if not vname:
            raise MufCompileError("Variable declaration incomplete.")
        if cmplr.funcname:
            # Function scoped var
            if comp.get_func_var(cmplr.funcname, vname):
                raise MufCompileError("Variable already declared.")
            comp.add_func_var(cmplr.funcname, vname)
        else:
            # Global vars
            if comp.get_global_var(vname):
                raise MufCompileError("Variable already declared.")
            comp.add_global_var(vname)
        return (False, src)


@instr("var!")
class InstVarBang(Instruction):
    def compile(self, cmplr, code, src):
        vname, line, src = cmplr.get_word(src)
        comp = cmplr.compiled
        if not vname:
            raise MufCompileError("Variable declaration incomplete.")
        if comp.get_func_var(cmplr.funcname, vname):
            raise MufCompileError("Variable already declared.")
        vnum = comp.add_func_var(cmplr.funcname, vname)
        code.append(InstFuncVar(line, vnum, vname))
        code.append(InstBang(line))
        return (False, src)


@instr("variable")
class InstVariable(Instruction):
    def execute(self, fr):
        vnum = fr.data_pop(int)
        fr.data_push(StackGlobalVar(vnum))


@instr("localvar")
class InstLocalVar(Instruction):
    def execute(self, fr):
        vnum = fr.data_pop(int)
        fr.data_push(StackGlobalVar(vnum))


@instr("fmtstring")
class InstFmtString(Instruction):
    def execute(self, fr):
        def subfunc(matchobj):
            fmt = matchobj.group(1)
            ftyp = matchobj.group(3)
            if ftyp == "%":
                return "%"
            elif ftyp == "i":
                val = fr.data_pop(int)
                ftyp = "d"
            elif ftyp.lower() in ["e", "f", "g"]:
                val = fr.data_pop(float)
            elif ftyp == "s":
                val = fr.data_pop(str)
            elif ftyp == "D":
                val = fr.data_pop_object().name
                ftyp = "s"
            elif ftyp == "d":
                val = fr.data_pop_dbref()
                ftyp = "s"
            elif ftyp == "~":
                val = item_repr(fr.data_pop())
                ftyp = "s"
            elif ftyp == "?":
                val = fr.data_pop()
                if type(val) in [int, float, str, list, dict]:
                    val = str(type(val)).split("'")[1].title()
                else:
                    val = str(type(val)).split("'")[1].split(".")[1][5:]
                ftyp = "s"
            else:
                return ""
            while '*' in fmt:
                pre, post = fmt.split('*', 1)
                x = fr.data_pop(int)
                fmt = pre + str(x) + post
            fmt = fmt.replace('|', '^')
            fmt = fmt + ftyp
            return fmt % val

        fmt = fr.data_pop(str)
        out = re.sub(
            r'(%[| 0+-]*[0-9]*(\.[0-9]*)?)([idDefgEFGsl%?~])',
            subfunc, fmt
        )
        fr.data_push(out)


@instr("array_fmtstrings")
class InstArrayFmtStrings(Instruction):
    def execute(self, fr):
        def subfunc(matchobj):
            fmt = matchobj.group(1)
            key = matchobj.group(3)
            ftyp = matchobj.group(4)
            if ftyp == "%":
                return "%"
            elif ftyp == "i":
                val = d.get(key, 0)
                fr.check_type(val, [int])
                ftyp = "d"
            elif ftyp.lower() in ["e", "f", "g"]:
                val = d.get(key, 0.0)
                fr.check_type(val, [float])
            elif ftyp == "s":
                val = d.get(key, '')
                fr.check_type(val, [str])
            elif ftyp == "D":
                val = d.get(key, StackDBRef(-1))
                fr.check_type(val, [StackDBRef])
                val = getobj(val).name
                ftyp = "s"
            elif ftyp == "d":
                val = d.get(key, StackDBRef(-1))
                fr.check_type(val, [StackDBRef])
                ftyp = "s"
            elif ftyp == "~":
                val = d.get(key, 0)
                ftyp = "s"
            elif ftyp == "?":
                val = item_type_name(d.get(key, 0))
                ftyp = "s"
            else:
                return ""
            fmt = fmt.replace('|', '^')
            fmt = fmt + ftyp
            return fmt % val

        fmt = fr.data_pop(str)
        arr = fr.data_pop(list)
        outarr = []
        for d in arr:
            if type(d) is not dict:
                raise MufRuntimeError("Expected list of dictionaries.")
            out = re.sub(
                r'(%[| 0+-]*[0-9]*(\.[0-9]*)?)\[([^]]+)\]([idDefgEFGsl%?~])',
                subfunc, fmt
            )
            outarr.append(out)
        fr.data_push(outarr)


@instr("addprop")
class InstAddProp(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        val2 = fr.data_pop(int)
        val = fr.data_pop(str)
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        if val:
            obj.setprop(prop, val)
        else:
            obj.setprop(prop, val2)


@instr("setprop")
class InstSetProp(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        val = fr.data_pop()
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        obj.setprop(prop, val)


@instr("remove_prop")
class InstRemoveProp(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        obj.delprop(prop)


@instr("propdir?")
class InstPropDirP(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        val = obj.is_propdir(prop)
        fr.data_push(1 if val else 0)


@instr("nextprop")
class InstNextProp(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        val = obj.next_prop(prop)
        fr.data_push(val)


@instr("array_get_propdirs")
class InstArrayGetPropDirs(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        prop = fr.data_pop(str) + '/'
        obj = fr.data_pop_object()
        out = []
        while True:
            prop = obj.next_prop(prop)
            if not prop:
                break
            if obj.is_propdir(prop):
                out.append(prop)
        fr.data_push(out)


@instr("getprop")
class InstGetProp(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        val = obj.getprop(prop)
        if val is None:
            val = 0
        fr.data_push(val)


@instr("getpropstr")
class InstGetPropStr(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        val = obj.getprop(prop)
        if type(val) is not str:
            val = ""
        fr.data_push(val)


@instr("getpropval")
class InstGetPropVal(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        val = obj.getprop(prop)
        if type(val) is not int:
            val = 0
        fr.data_push(val)


@instr("getpropfval")
class InstGetPropFVal(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        val = obj.getprop(prop)
        if type(val) is not float:
            val = 0.0
        fr.data_push(val)


@instr("envprop")
class InstEnvProp(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        prop = fr.data_pop(str)
        obj = fr.data_pop_object().dbref
        while obj >= 0:
            val = getobj(obj).getprop(prop)
            if val is not None:
                break
            obj = getobj(obj).location
        if val is None:
            val = 0
        fr.data_push(val)


@instr("envpropstr")
class InstEnvPropStr(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        prop = fr.data_pop(str)
        obj = fr.data_pop_object().dbref
        while obj >= 0:
            val = getobj(obj).getprop(prop)
            if val is not None:
                break
            obj = getobj(obj).location
        if type(val) is str:
            fr.data_push(val)
        else:
            fr.data_push("")


@instr("array_get_proplist")
class InstArrayGetPropList(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        out = []
        val = obj.getprop("%s#" % prop)
        cnt = 0
        if val:
            if type(val) is str:
                try:
                    cnt = int(cnt)
                except:
                    cnt = 0
            elif type(val) is int:
                cnt = val
        for i in xrange(cnt):
            val = obj.getprop("%s#/%d" % (prop, i + 1))
            if type(val) is str:
                out.append(val)
        fr.data_push(out)


@instr("array_put_proplist")
class InstArrayPutPropList(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        items = fr.data_pop(list)
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        obj.setprop("%s#" % prop, len(items))
        for i, item in enumerate(items):
            obj.setprop("%s#/%d" % (prop, i + 1), item)


@instr("array_get_reflist")
class InstArrayGetReflist(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        val = obj.getprop(prop)
        if type(val) is not str:
            fr.data_push([])
        else:
            vals = [
                StackDBRef(int(x[1:]))
                for x in val.split(" ")
                if x.startswith('#') and is_int(x[1:])
            ]
            fr.data_push(vals)


@instr("array_put_reflist")
class InstArrayPutReflist(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        refs = fr.data_pop(list)
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        for ref in refs:
            if type(ref) is not StackDBRef:
                raise MufRuntimeError("Expected list of dbrefs.")
        refstr = " ".join(["#%d" % ref.value for ref in refs])
        obj.setprop(prop, refstr)


@instr("reflist_add")
class InstRefListAdd(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        ref = fr.data_pop_dbref()
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        val = obj.getprop(prop)
        if type(val) is not str:
            refs = []
        else:
            refs = [
                StackDBRef(int(x[1:]))
                for x in val.split(" ")
                if x.startswith('#') and is_int(x[1:])
            ]
        if ref in refs:
            del refs[refs.index(ref)]
        refs.append(ref)
        refstr = " ".join(["#%d" % x.value for x in refs])
        obj.setprop(prop, refstr)


@instr("reflist_del")
class InstRefListDel(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        ref = fr.data_pop_dbref()
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        val = obj.getprop(prop)
        if type(val) is not str:
            refs = []
        else:
            refs = [
                StackDBRef(int(x[1:]))
                for x in val.split(" ")
                if x.startswith('#') and is_int(x[1:])
            ]
        if ref in refs:
            del refs[refs.index(ref)]
        refstr = " ".join(["#%d" % x.value for x in refs])
        obj.setprop(prop, refstr)


@instr("reflist_find")
class InstRefListFind(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        ref = fr.data_pop_dbref()
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        val = obj.getprop(prop)
        if type(val) is not str:
            refs = []
        else:
            refs = [
                StackDBRef(int(x[1:]))
                for x in val.split(" ")
                if x.startswith('#') and is_int(x[1:])
            ]
        if ref in refs:
            fr.data_push(refs.index(ref) + 1)
        else:
            fr.data_push(0)


@instr("array_filter_prop")
class InstArrayFilterProp(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        pat = fr.data_pop(str)
        prop = fr.data_pop(str)
        objs = fr.data_pop(list)
        found = []
        for obj in objs:
            if type(obj) is not StackDBRef:
                raise MufRuntimeError("Expected list of dbrefs.")
            if validobj(obj):
                val = getobj(obj).getprop(prop)
                if val and smatch(pat, val):
                    found.append(obj)
        fr.data_push(found)


@instr("array_filter_flags")
class InstArrayFilterFlags(Instruction):
    type_map = {
        'E': "exit",
        'F': "program",
        'G': "garbage",
        'P': "player",
        'R': "room",
        'T': "thing",
    }

    def execute(self, fr):
        fr.check_underflow(2)
        flags = fr.data_pop(str).upper()
        objs = fr.data_pop(list)
        found = []
        for obj in objs:
            if type(obj) is not StackDBRef:
                raise MufRuntimeError("Expected list of dbrefs.")
            if validobj(obj):
                obj = getobj(obj)
                good = True
                invert = False
                for flg in list(flags):
                    goodpass = True
                    mlev = 1 if '1' in obj.flags else 0
                    mlev += 2 if '2' in obj.flags else 0
                    mlev += 3 if '3' in obj.flags else 0
                    if flg == '!':
                        invert = not invert
                        continue
                    elif flg in self.type_map:
                        goodpass = self.type_map[flg] == obj.objtype
                    elif flg in ['1', '2', '3']:
                        goodpass = int(flg) <= mlev
                    elif flg == 'M':
                        goodpass = mlev >= 1
                    elif flg == 'N':
                        goodpass = mlev % 2 == 1
                    else:
                        goodpass = flg in obj.flags
                    goodpass = not goodpass if invert else goodpass
                    good = good and goodpass
                    invert = False
                if good:
                    found.append(StackDBRef(obj.dbref))
        fr.data_push(found)


@instr("dbcmp")
class InstDBCmp(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop_dbref()
        a = fr.data_pop_dbref()
        fr.data_push(1 if a.value == b.value else 0)


@instr("explode_array")
class InstExplodeArray(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        delim = fr.data_pop(str)
        txt = fr.data_pop(str)
        fr.data_push(txt.split(delim))


@instr("regexp")
class InstRegExp(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        flags = fr.data_pop(int)
        pat = fr.data_pop(str)
        txt = fr.data_pop(str)
        flgs = 0
        if (flags % 0x1) != 0:
            flgs |= re.IGNORECASE
        try:
            pat = re.compile(pat, flgs)
        except:
            raise MufRuntimeError("Malformed regexp pattern. (2)")
        matches = pat.search(txt)
        if not matches:
            fr.data_push([])
            fr.data_push([])
        else:
            submatches = []
            indexes = []
            for i in xrange(len(matches.groups()) + 1):
                submatches.append(matches.group(i))
                indexes.append(list(matches.span(i)))
            fr.data_push(submatches)
            fr.data_push(indexes)


@instr("regsub")
class InstRegSub(Instruction):
    def execute(self, fr):
        fr.check_underflow(4)
        flags = fr.data_pop(int)
        repl = fr.data_pop(str)
        pat = fr.data_pop(str)
        txt = fr.data_pop(str)
        flgs = 0
        if (flags % 0x1) != 0:
            flgs |= re.IGNORECASE
        try:
            val = re.sub(pat, repl, txt, flgs)
        except:
            raise MufRuntimeError("Malformed regexp pattern. (2)")
        fr.data_push(val)


@instr("toupper")
class InstToUpper(Instruction):
    def execute(self, fr):
        txt = fr.data_pop(str)
        fr.data_push(txt.upper())


@instr("tolower")
class InstToLower(Instruction):
    def execute(self, fr):
        txt = fr.data_pop(str)
        fr.data_push(txt.lower())


@instr("explode")
class InstExplode(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        delim = fr.data_pop(str)
        txt = fr.data_pop(str)
        if not delim:
            raise MufRuntimeError("Expected non-null string argument. (2)")
        parts = txt.split(delim)
        for part in reversed(parts):
            fr.data_push(part)
        fr.data_push(len(parts))


@instr("split")
class InstSplit(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        delim = fr.data_pop(str)
        txt = fr.data_pop(str)
        parts = txt.split(delim, 1)
        fr.data_push(parts[0])
        if len(parts) > 1:
            fr.data_push(parts[1])
        else:
            fr.data_push("")


@instr("rsplit")
class InstRSplit(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        delim = fr.data_pop(str)
        txt = fr.data_pop(str)
        parts = txt.rsplit(delim, 1)
        fr.data_push(parts[0])
        if len(parts) > 1:
            fr.data_push(parts[1])
        else:
            fr.data_push("")


@instr("striplead")
class InstStripLead(Instruction):
    def execute(self, fr):
        txt = fr.data_pop(str)
        fr.data_push(txt.lstrip())


@instr("striptail")
class InstStripTail(Instruction):
    def execute(self, fr):
        txt = fr.data_pop(str)
        fr.data_push(txt.rstrip())


@instr("strlen")
class InstStrLen(Instruction):
    def execute(self, fr):
        txt = fr.data_pop(str)
        fr.data_push(len(txt))


@instr("strcat")
class InstStrCat(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        txt2 = fr.data_pop(str)
        txt = fr.data_pop(str)
        fr.data_push(txt + txt2)


@instr("instr")
class InstInstr(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        fnd = fr.data_pop(str)
        txt = fr.data_pop(str)
        fr.data_push(txt.find(fnd) + 1)


@instr("instring")
class InstInString(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        fnd = fr.data_pop(str).lower()
        txt = fr.data_pop(str).lower()
        fr.data_push(txt.find(fnd) + 1)


@instr("rinstr")
class InstRInstr(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        fnd = fr.data_pop(str)
        txt = fr.data_pop(str)
        fr.data_push(txt.rfind(fnd) + 1)


@instr("rinstring")
class InstRInString(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        fnd = fr.data_pop(str).lower()
        txt = fr.data_pop(str).lower()
        fr.data_push(txt.rfind(fnd) + 1)


@instr("strcut")
class InstStrCut(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(int)
        a = fr.data_pop(str)
        fr.data_push(a[:b])
        fr.data_push(a[b:])


@instr("midstr")
class InstMidStr(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        num = fr.data_pop(int)
        pos = fr.data_pop(int)
        s = fr.data_pop(str)
        fr.data_push(s[pos - 1:pos + num - 1])


@instr("depth")
class InstDepth(Instruction):
    def execute(self, fr):
        fr.data_push(fr.data_depth())


@instr("fulldepth")
class InstFullDepth(Instruction):
    def execute(self, fr):
        fr.data_push(fr.data_depth())


@instr("int?")
class InstIntP(Instruction):
    def execute(self, fr):
        val = fr.data_pop()
        fr.data_push(1 if type(val) is int else 0)


@instr("float?")
class InstFloatP(Instruction):
    def execute(self, fr):
        val = fr.data_pop()
        fr.data_push(1 if type(val) is float else 0)


@instr("number?")
class InstNumberP(Instruction):
    def execute(self, fr):
        val = fr.data_pop()
        fr.data_push(1 if type(val) in [int, float] else 0)


@instr("dbref?")
class InstDBRefP(Instruction):
    def execute(self, fr):
        val = fr.data_pop()
        fr.data_push(1 if type(val) is StackDBRef else 0)


@instr("string?")
class InstStringP(Instruction):
    def execute(self, fr):
        val = fr.data_pop()
        fr.data_push(1 if type(val) is str else 0)


@instr("address?")
class InstAddressP(Instruction):
    def execute(self, fr):
        val = fr.data_pop()
        fr.data_push(1 if type(val) is StackAddress else 0)


@instr("array?")
class InstArrayP(Instruction):
    def execute(self, fr):
        val = fr.data_pop()
        fr.data_push(1 if type(val) in [list, dict] else 0)


@instr("dictionary?")
class InstDictionaryP(Instruction):
    def execute(self, fr):
        val = fr.data_pop()
        fr.data_push(1 if type(val) is dict else 0)


@instr("lock?")
class InstLockP(Instruction):
    def execute(self, fr):
        val = fr.data_pop()
        fr.data_push(1 if type(val) is StackLock else 0)


@instr("int")
class InstInt(Instruction):
    def execute(self, fr):
        val = fr.data_pop()
        if type(val) is StackGlobalVar:
            val = val.value
        elif type(val) is StackFuncVar:
            val = val.value
        elif type(val) is StackDBRef:
            val = val.value
        elif type(val) is int:
            val = val
        elif type(val) is float:
            if (
                math.isinf(val) or
                math.isnan(val) or
                math.fabs(val) >= math.pow(2.0, 32.0)
            ):
                fr.set_error("IBOUNDS")
                val = 0
            else:
                val = int(val)
        else:
            raise MufRuntimeError("Expected number or var argument.")
        fr.data_push(val)


@instr("dbref")
class InstDBRef(Instruction):
    def execute(self, fr):
        val = fr.data_pop(int)
        fr.data_push(StackDBRef(val))


@instr("subst")
class InstSubst(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        fnd = fr.data_pop(str)
        repl = fr.data_pop(str)
        txt = fr.data_pop(str)
        fr.data_push(txt.replace(fnd, repl))


@instr("strcmp")
class InstStrCmp(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(str)
        a = fr.data_pop(str)
        fr.data_push(cmp(a, b))


@instr("strncmp")
class InstStrNCmp(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        n = fr.data_pop(int)
        b = fr.data_pop(str)
        a = fr.data_pop(str)
        fr.data_push(cmp(a[:n], b[:n]))


@instr("stringcmp")
class InstStringCmp(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(str).upper()
        a = fr.data_pop(str).upper()
        fr.data_push(cmp(a, b))


@instr("stringpfx")
class InstStringPfx(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(str).upper()
        a = fr.data_pop(str).upper()
        fr.data_push(0 if cmp(a[:len(b)], b) else 1)


@instr("smatch")
class InstSMatch(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        pat = fr.data_pop(str).upper()
        txt = fr.data_pop(str).upper()
        fr.data_push(1 if smatch(pat, txt) else 0)


@instr("strencrypt")
class InstStrEncrypt(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        key = fr.data_pop(str)
        data = fr.data_pop(str)
        enarr = list(range(256))
        for i in range(ord('A'), ord('M') + 1):
            enarr[i] += 13
        for i in range(ord('N'), ord('Z') + 1):
            enarr[i] -= 13
        enarr[13] = 127
        enarr[127] = 13
        enarr[27] = 31
        enarr[31] = 27
        charcount = 97
        seed = 0
        for cp in list(key):
            seed = ((ord(cp) ^ seed) + 170) % 192
        seed2 = 0
        for cp in list(data):
            seed2 = ((ord(cp) ^ seed2) + 21) & 0xff
        seed3 = seed2 = (seed2 ^ (seed ^ random.randint(0, 255))) & 0x3f
        count = seed + 11
        repkey = key * (len(data) / len(key) + 1)
        repkey = repkey[:len(data)]
        out = chr(32 + 2) + chr(32 + seed3)
        for upt, cp in zip(list(data), list(repkey)):
            count = ((ord(cp) ^ count) + (seed ^ seed2)) & 0xff
            seed2 = (seed2 + 1) & 0x3f
            result = (enarr[ord(upt)] - (32 - (charcount - 96))) + count + seed
            ups = enarr[(result % charcount) + (32 - (charcount - 96))]
            count = ((ord(upt) ^ count) + seed) & 0xff
            out += chr(ups)
        fr.data_push(out)


@instr("strdecrypt")
class InstStrDecrypt(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        key = fr.data_pop(str)
        data = fr.data_pop(str)
        if not data:
            fr.data_push("")
            return
        enarr = list(range(256))
        for i in range(ord('A'), ord('M') + 1):
            enarr[i] += 13
        for i in range(ord('N'), ord('Z') + 1):
            enarr[i] -= 13
        enarr[13] = 127
        enarr[127] = 13
        enarr[27] = 31
        enarr[31] = 27
        charset_count = [96, 97]
        rev = ord(data[0]) - 32
        if rev not in [1, 2]:
            fr.data_push("")
            return
        chrcnt = charset_count[rev - 1]
        seed2 = ord(data[1]) - 32
        data = data[2:]
        seed = 0
        for cp in list(key):
            seed = ((ord(cp) ^ seed) + 170) % 192
        count = seed + 11
        repkey = key * (len(data) / len(key) + 1)
        repkey = repkey[:len(data)]
        out = ''
        for upt, cp in zip(list(data), list(repkey)):
            count = ((ord(cp) ^ count) + (seed ^ seed2)) & 0xff
            seed2 = (seed2 + 1) & 0x3f
            result = (enarr[ord(upt)] - (32 - (chrcnt - 96))) - (count + seed)
            while result < 0:
                result += chrcnt
            ups = enarr[result + (32 - (chrcnt - 96))]
            count = ((ups ^ count) + seed) & 0xff
            out += chr(ups)
        fr.data_push(out)


@instr("tokensplit")
class InstTokenSplit(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        esc = fr.data_pop(str)
        delim = fr.data_pop(str)
        txt = fr.data_pop(str)
        txtlen = len(txt)
        pos = 0
        while pos < txtlen:
            if txt[pos] in esc:
                pos += 2
                continue
            if txt[pos] in delim:
                break
            pos += 1
        fr.data_push(txt[:pos])
        fr.data_push(txt[pos + 1:])
        fr.data_push(txt[pos])


@instr("pronoun_sub")
class InstPronounSub(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        txt = fr.data_pop(str)
        obj = fr.data_pop_object()
        sex = obj.getprop("sex")
        if type(sex) is not str:
            sex = ""
        if sex.strip().lower() == "male":
            subs = {
                "%a": "his",
                "%s": "he",
                "%o": "him",
                "%p": "his",
                "%r": "himself",
                "%n": obj.name,
                "%A": "His",
                "%S": "He",
                "%O": "Him",
                "%P": "His",
                "%R": "Himself",
                "%N": obj.name,
            }
        elif sex.strip().lower() == "female":
            subs = {
                "%a": "hers",
                "%s": "she",
                "%o": "her",
                "%p": "her",
                "%r": "herself",
                "%n": obj.name,
                "%A": "Hers",
                "%S": "She",
                "%O": "Her",
                "%P": "Her",
                "%R": "Herself",
                "%N": obj.name,
            }
        elif sex.strip().lower() in ["herm", "hermaphrodite"]:
            subs = {
                "%a": "hirs",
                "%s": "shi",
                "%o": "hir",
                "%p": "hir",
                "%r": "hirself",
                "%n": obj.name,
                "%A": "Hirs",
                "%S": "Shi",
                "%O": "Hir",
                "%P": "Hir",
                "%R": "Hirself",
                "%N": obj.name,
            }
        else:
            subs = {
                "%a": "its",
                "%s": "it",
                "%o": "it",
                "%p": "its",
                "%r": "itself",
                "%n": obj.name,
                "%A": "Its",
                "%S": "It",
                "%O": "It",
                "%P": "Its",
                "%R": "Itself",
                "%N": obj.name,
            }
        for fnd, repl in subs.iteritems():
            txt = txt.replace(fnd, repl)
        fr.data_push(txt)


@instr("ansi_strip")
class InstAnsiStrip(Instruction):
    def execute(self, fr):
        txt = fr.data_pop(str)
        pos = 0
        txtlen = len(txt)
        out = ""
        while pos < txtlen:
            if txt[pos] == "\033":
                while pos < txtlen and txt[pos] != "m":
                    pos += 1
                pos += 1
                continue
            out += txt[pos]
            pos += 1
        fr.data_push(out)


@instr("ansi_strlen")
class InstAnsiStrLen(Instruction):
    def execute(self, fr):
        txt = fr.data_pop(str)
        pos = 0
        txtlen = len(txt)
        outlen = 0
        while pos < txtlen:
            if txt[pos] == "\033":
                while pos < txtlen and txt[pos] != "m":
                    pos += 1
                pos += 1
                continue
            pos += 1
            outlen += 1
        fr.data_push(outlen)


@instr("ansi_strcut")
class InstAnsiStrCut(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        cutpos = fr.data_pop(int)
        txt = fr.data_pop(str)
        pos = 0
        txtlen = len(txt)
        while pos < txtlen:
            if cutpos == 0:
                break
            if txt[pos] == "\033":
                while pos < txtlen and txt[pos] != "m":
                    pos += 1
                pos += 1
                continue
            pos += 1
            cutpos -= 1
        fr.data_push(txt[:pos])
        fr.data_push(txt[pos:])


@instr("ansi_midstr")
class InstAnsiMidStr(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        end = fr.data_pop(int)
        start = fr.data_pop(int) - 1
        txt = fr.data_pop(str)
        pos = 0
        strpos = 0
        end += start
        txtlen = len(txt)
        while pos < txtlen:
            if strpos >= start:
                break
            if txt[pos] == "\033":
                while pos < txtlen and txt[pos] != "m":
                    pos += 1
                pos += 1
                continue
            pos += 1
            strpos += 1
        start = pos
        while pos < txtlen:
            if strpos >= end:
                break
            if txt[pos] == "\033":
                while pos < txtlen and txt[pos] != "m":
                    pos += 1
                pos += 1
                continue
            pos += 1
            strpos += 1
        end = pos
        fr.data_push(txt[start:end])


@instr("debug_on")
class InstDebugOn(Instruction):
    def execute(self, fr):
        fr.trace = True


@instr("debug_off")
class InstDebugOff(Instruction):
    def execute(self, fr):
        fr.trace = False


@instr("debug_line")
class InstDebugLine(Instruction):
    def execute(self, fr):
        inst = fr.curr_inst()
        addr = fr.curr_addr()
        line = inst.line
        print("% 5d: #%d line %d (%s) %s" %
              (addr.value, addr.prog, line, fr.get_stack_repr(999), inst))
        sys.stdout.flush()


@instr("debugger_break")
class InstDebuggerBreak(Instruction):
    def execute(self, fr):
        raise MufBreakExecution()


class CompiledMuf(object):
    def __init__(self, prog):
        self.program = prog
        self.srclines = getobj(prog).sources.split("\n")
        self.code = []
        self.functions = {}
        self.publics = {}
        self.func_vars = {}
        self.global_vars = ["me", "loc", "trigger", "command"]
        self.lastfunction = None

    def show_compiled_tokens(self):
        for instnum, inst in enumerate(self.code):
            inst = str(inst)
            if instnum > 0 and inst.startswith("Function:"):
                print("")
            print("% 5d: %s" % (instnum, inst))

    def add_function(self, funcname, addr):
        if type(addr) is int:
            addr = StackAddress(addr, self.program)
        self.functions[funcname] = addr
        self.func_vars[funcname] = []
        self.lastfunction = addr

    def get_functions(self):
        funcs = self.functions.keys()
        funcs.sort()
        return funcs

    def get_function_addr(self, funcname):
        if funcname not in self.functions:
            return None
        return self.functions[funcname]

    def publicize_function(self, funcname):
        if funcname not in self.functions:
            return False
        self.publics[funcname] = self.functions[funcname]
        return True

    def find_func(self, addr):
        if type(addr) is StackAddress:
            addr = addr.value
        while addr > 0 and type(self.code[addr]) is not InstFunc:
            addr -= 1
        if type(self.code[addr]) is not InstFunc:
            return ""
        return self.code[addr].funcname

    def show_line(self, addr):
        if type(addr) is StackAddress:
            addr = addr.value
        inst = self.code[addr]
        if (
            addr > 0 and addr < len(self.code) and
            self.code[addr - 1].line == inst.line
        ):
            print("Instruction %d: %s" % (addr, inst))
        print(">% 5d: %s" % (inst.line, self.srclines[inst.line - 1]))

    def get_inst(self, addr):
        if type(addr) is StackAddress:
            addr = addr.value
        return self.code[addr]

    def get_inst_line(self, addr):
        if type(addr) is StackAddress:
            addr = addr.value
        return self.code[addr].line

    def add_func_var(self, funcname, varname):
        varcount = len(self.func_vars[funcname])
        self.func_vars[funcname].append(varname)
        return varcount

    def get_func_var(self, funcname, varname):
        if funcname not in self.func_vars:
            return None
        if varname not in self.func_vars[funcname]:
            return None
        return StackFuncVar(self.func_vars[funcname].index(varname))

    def get_func_vars(self, funcname):
        if funcname not in self.func_vars:
            return None
        return self.func_vars[funcname]

    def add_global_var(self, varname):
        varcount = len(self.global_vars)
        self.global_vars.append(varname)
        return varcount

    def get_global_var(self, varname):
        if varname in self.global_vars:
            return StackGlobalVar(self.global_vars.index(varname))
        return None

    def get_global_vars(self, funcname):
        return self.global_vars


class MufCallFrame(object):
    def __init__(self, addr, caller):
        if type(caller) is int:
            caller = StackDBRef(caller)
        self.variables = {}
        self.loop_stack = []
        self.pc = addr
        self.caller = caller

    def pc_advance(self, delta):
        self.pc.value += delta

    def pc_set(self, addr):
        self.pc = copy.deepcopy(addr)

    def loop_iter_push(self, typ, it):
        self.loop_stack.append((typ, it))

    def loop_iter_pop(self):
        return self.loop_stack.pop()

    def loop_iter_top(self):
        return self.loop_stack[-1]

    def variable_get(self, varnum):
        if varnum in self.variables:
            return self.variables[varnum]
        return 0

    def variable_set(self, varnum, val):
        self.variables[varnum] = val


class MufStackFrame(object):
    MAX_STACK = 1024

    def __init__(self):
        self.user = StackDBRef(-1)
        self.program = StackDBRef(program_object.dbref)
        self.trigger = StackDBRef(-1)
        self.command = ""
        self.catch_stack = []
        self.call_stack = []
        self.data_stack = []
        self.globalvars = {}
        self.fp_errors = 0
        self.read_wants_blanks = False
        self.trace = False
        self.cycles = 0
        self.breakpoints = []
        self.break_after_steps = -1
        self.break_after_lines = -1
        self.break_on_finish = False
        self.prevaddr = StackAddress(-1, self.program)
        self.prevline = -1
        self.nextline = -1
        self.matches = []
        self.text_entry = []

    def get_compiled(self, prog=-1):
        if prog < 0:
            addr = self.curr_addr()
            prog = addr.prog
        return getobj(prog).compiled

    def setup(self, prog, user, trig, cmd):
        self.program = StackDBRef(prog.dbref)
        self.trigger = StackDBRef(trig.dbref)
        self.user = StackDBRef(user.dbref)
        self.command = cmd
        self.globalvar_set(0, StackDBRef(user.dbref))
        self.globalvar_set(1, StackDBRef(user.location))
        self.globalvar_set(2, StackDBRef(trig.dbref))
        self.globalvar_set(3, cmd)
        comp = self.get_compiled(prog)
        self.call_push(comp.lastfunction, trig.dbref)

    def set_trace(self, on_off):
        self.trace = on_off

    def set_text_entry(self, text):
        if type(text) is list:
            self.text_entry = text
        else:
            self.text_entry = text.split('\n')

    def curr_inst(self):
        if not self.call_stack:
            return None
        addr = self.curr_addr()
        comp = self.get_compiled()
        return comp.get_inst(addr)

    def curr_addr(self):
        if not self.call_stack:
            return None
        return self.call_stack[-1].pc

    def pc_advance(self, delta):
        if self.call_stack:
            return self.call_stack[-1].pc_advance(delta)
        return None

    def pc_set(self, addr):
        if type(addr) is not StackAddress:
            raise MufRuntimeError("Expected an address!")
        return self.call_stack[-1].pc_set(addr)

    def catch_push(self, detailed, addr, lockdepth):
        self.catch_stack.append((detailed, addr, lockdepth))

    def catch_pop(self):
        return self.catch_stack.pop()

    def catch_is_detailed(self):
        if not self.catch_stack:
            return False
        return self.catch_stack[-1][0]

    def catch_addr(self):
        if not self.catch_stack:
            return None
        return self.catch_stack[-1][1]

    def catch_locklevel(self):
        if not self.catch_stack:
            return 0
        return self.catch_stack[-1][2]

    def catch_trigger(self, e):
        addr = self.catch_addr()
        if not addr:
            return False
        if type(addr) is not StackAddress:
            raise MufRuntimeError("Expected an address!")
        # Clear stack down to stacklock
        while self.data_depth() > self.catch_locklevel():
            self.data_pop()
        if self.catch_is_detailed():
            # Push detailed exception info.
            inst = self.curr_inst()
            self.data_push({
                "error": str(e),
                "instr": inst.prim_name.upper(),
                "line": inst.line,
                "program": self.program,
            })
        else:
            # Push error message.
            self.data_push(str(e))
        self.catch_pop()
        self.pc_set(addr)
        return True

    def check_type(self, val, types):
        if types and type(val) not in types:
            self.raise_expected_type_error(types)

    def raise_expected_type_error(self, types):
        expected = []
        if int in types and float in types:
            expected.append("number")
        elif int in types:
            expected.append("integer")
        elif float in types:
            expected.append("float")
        if str in types:
            expected.append("string")
        if list in types and dict in types:
            expected.append("array")
        elif list in types:
            expected.append("list array")
        elif dict in types:
            expected.append("dictionary array")
        if StackDBRef in types:
            expected.append("dbref")
        if StackAddress in types:
            expected.append("address")
        if StackLock in types:
            expected.append("lock")
        if StackGlobalVar in types or StackFuncVar in types:
            expected.append("variable")
        expected = " or ".join(expected)
        raise MufRuntimeError("Expected %s argument." % expected)

    def check_underflow(self, cnt):
        if self.data_depth() < cnt:
            raise MufRuntimeError("Stack underflow.")

    def data_depth(self):
        return len(self.data_stack)

    def data_push(self, x):
        self.data_stack.append(x)
        if len(self.data_stack) > self.MAX_STACK:
            raise MufRuntimeError("Stack overflow.")

    def data_pop(self, *types):
        if len(self.data_stack) - self.catch_locklevel() < 1:
            raise MufRuntimeError("Stack underflow.")
        self.check_type(self.data_stack[-1], types)
        return self.data_stack.pop()

    def data_pop_dbref(self):
        return self.data_pop(StackDBRef)

    def data_pop_object(self):
        return getobj(self.data_pop(StackDBRef))

    def data_pop_address(self):
        return self.data_pop(StackAddress)

    def data_pop_lock(self):
        return self.data_pop(StackLock)

    def data_pick(self, n):
        if len(self.data_stack) < n:
            raise MufRuntimeError("Stack underflow.")
        return self.data_stack[-n]

    def data_pull(self, n):
        if len(self.data_stack) - self.catch_locklevel() < n:
            raise MufRuntimeError("Stack underflow.")
        a = self.data_stack[-n]
        del self.data_stack[-n]
        return a

    def data_put(self, n, val):
        if len(self.data_stack) - self.catch_locklevel() < n:
            raise MufRuntimeError("Stack underflow.")
        self.data_stack[-n] = val

    def data_insert(self, n, val):
        if len(self.data_stack) - self.catch_locklevel() < n:
            raise MufRuntimeError("StackUnderflow")
        if n < 1:
            self.data_stack.append(val)
        else:
            self.data_stack.insert(1 - n, val)

    def loop_iter_push(self, typ, it):
        return self.call_stack[-1].loop_iter_push(typ, it)

    def loop_iter_pop(self):
        return self.call_stack[-1].loop_iter_pop()

    def loop_iter_top(self):
        return self.call_stack[-1].loop_iter_top()

    def call_push(self, addr, caller):
        self.call_stack.append(
            MufCallFrame(copy.deepcopy(addr), caller)
        )

    def call_pop(self):
        self.call_stack.pop()

    def caller_get(self):
        return self.call_stack[-1].caller

    def funcvar_get(self, v):
        if type(v) is StackFuncVar:
            v = v.value
        return self.call_stack[-1].variable_get(v)

    def funcvar_set(self, v, val):
        if type(v) is StackFuncVar:
            v = v.value
        return self.call_stack[-1].variable_set(v, val)

    def globalvar_get(self, v):
        if type(v) is StackGlobalVar:
            v = v.value
        if v in self.globalvars:
            return self.globalvars[v]
        return 0

    def globalvar_set(self, v, val):
        if type(v) is StackGlobalVar:
            v = v.value
        self.globalvars[v] = val

    def get_stack_repr(self, maxcnt):
        out = ''
        depth = self.data_depth()
        if maxcnt > depth:
            maxcnt = depth
        else:
            out += '...'
        for i in xrange(-depth, 0):
            if out:
                out += ', '
            out += item_repr(self.data_stack[i])
        return out

    def show_compiled_tokens(self, prog):
        comp = self.get_compiled(prog)
        comp.show_compiled_tokens()

    def check_breakpoints(self):
        if not self.call_stack:
            raise MufBreakExecution()
        inst = self.curr_inst()
        addr = self.curr_addr()
        line = inst.line
        calllev = len(self.call_stack)
        if self.breakpoints:
            if line != self.prevline or addr.prog != self.prevaddr.prog:
                bp = (addr.prog, line)
                if bp in self.breakpoints:
                    bpnum = self.breakpoints.index(bp)
                    print("Stopped at breakpoint %d." % bpnum)
                    self.prevline = line
                    self.prevaddr = addr
                    raise MufBreakExecution()
        if self.break_on_finish and calllev < self.prev_call_level:
            print(
                "Stopped on call return at instruction %d in #%d." %
                (addr.value, addr.prog)
            )
            self.prevline = line
            self.prevaddr = addr
            self.break_on_finish = False
            raise MufBreakExecution()
        if calllev <= self.prev_call_level and self.break_after_lines > 0:
            if line != self.prevline:
                self.prevline = line
                self.break_after_lines -= 1
                if not self.break_after_lines:
                    self.prevaddr = addr
                    self.break_after_lines = -1
                    raise MufBreakExecution()
        if self.break_after_steps > 0:
            if line != self.prevline:
                self.prevline = line
                self.break_after_steps -= 1
                if not self.break_after_steps:
                    self.prevaddr = addr
                    self.break_after_steps = -1
                    raise MufBreakExecution()

    def execute_code(self):
        self.prev_call_level = len(self.call_stack)
        while self.call_stack:
            inst = self.curr_inst()
            addr = self.curr_addr()
            line = inst.line
            if self.trace:
                print("% 5d: #%d line %d (%s) %s" % (
                    addr.value, addr.prog, line,
                    self.get_stack_repr(999), inst))
                sys.stdout.flush()
            try:
                self.cycles += 1
                inst.execute(self)
                self.pc_advance(1)
                self.check_breakpoints()
            except MufBreakExecution as e:
                return
            except MufRuntimeError as e:
                if not self.catch_stack:
                    print(
                        "Error in #%d line %d (%s): %s" % (
                            addr.prog, line, str(inst), e
                        ),
                        file=sys.stderr
                    )
                    return
                elif self.trace:
                    print(
                        "Caught error in #%d line %d (%s): %s" %
                        (addr.prog, line, str(inst), e),
                        file=sys.stderr
                    )
                self.catch_trigger(e)
                try:
                    self.check_breakpoints()
                except MufBreakExecution as e:
                    return

    def show_call(self, addr=None):
        if not addr:
            addr = self.curr_addr()
        if addr:
            comp = self.get_compiled(addr.prog)
            line = comp.get_inst_line(addr)
            fun = comp.find_func(addr)
            print("In function '%s', Line %d:" % (fun, line))
            print("%s" % comp.srclines[line - 1])

    def complete(self, text, state):
        cmds = [
            'list ', 'quit', 'run', 'show ', 'next', 'step', 'break ',
            'continue', 'finish', 'stack', 'trace', 'notrace', 'delete ',
            'print ', 'pop', 'push ', 'rot', 'dup', 'swap', 'help'
        ]
        response = None

        origline = readline.get_line_buffer()
        begin = readline.get_begidx()
        end = readline.get_endidx()
        text = origline[begin:end]
        words = origline.split(' ')

        comp = self.get_compiled()
        if state == 0:
            # This is the first time for this text, so build a match list.
            if begin == 0:
                self.matches = [s for s in cmds if s and s.startswith(text)]
            elif words[0] in ['l', 'list', 'b', 'break']:
                self.matches = [
                    x for x in comp.get_functions() if x.startswith(text)
                ]
            elif words[0] == 'show':
                showcmds = ['breakpoints', 'functions', 'globals', 'vars']
                self.matches = [x for x in showcmds if x.startswith(text)]
            elif words[0] in ['p', 'print']:
                addr = self.curr_addr()
                fun = comp.find_func(addr)
                fvars = comp.get_func_vars(fun)
                gvars = comp.get_global_vars()
                self.matches = [
                    x for x in (fvars + gvars) if x.startswith(text)
                ]
            else:
                self.matches = cmds[:]

        # Return the state'th item from the match list,
        # if we have that many.
        try:
            response = self.matches[state]
        except IndexError:
            response = None
        return response

    def debug_cmd_step(self, args):
        if not args:
            args = "1"
        if not is_int(args):
            print("Usage: step [COUNT]")
        else:
            self.break_after_steps = int(args)
            self.execute_code()
            comp = self.get_compiled()
            comp.show_line(self.curr_addr())
            self.nextline = -1

    def debug_cmd_next(self, args):
        if not args:
            args = "1"
        if not is_int(args):
            print("Usage: next [COUNT]")
        else:
            self.break_after_lines = int(args)
            self.execute_code()
            comp = self.get_compiled()
            comp.show_line(self.curr_addr())
            self.nextline = -1

    def debug_cmd_continue(self, args):
        self.execute_code()
        comp = self.get_compiled()
        comp.show_line(self.curr_addr())
        self.nextline = -1

    def debug_cmd_finish(self, args):
        self.break_on_finish = True
        self.execute_code()
        comp = self.get_compiled()
        comp.show_line(self.curr_addr())
        self.nextline = -1

    def debug_cmd_break(self, args):
        # TODO: add support for breakpoints in other program objects.
        comp = self.get_compiled()
        if comp.get_function_addr(args):
            addr = comp.get_function_addr(args)
            line = comp.get_inst_line(addr.value)
            bp = (addr.prog, line)
            self.breakpoints.append(bp)
            print("Added breakpoint %d on line %d." %
                  (len(self.breakpoints), line))
        elif is_int(args):
            addr = self.curr_addr()
            line = int(args)
            bp = (addr.prog, line)
            self.breakpoints.append(bp)
            print("Added breakpoint %d on line %d." %
                  (len(self.breakpoints), line))
        else:
            print("Usage: break LINE")
            print("   or: break FUNCNAME")

    def debug_cmd_delete(self, args):
        if (
            not is_int(args) or
            int(args) < 0 or
            int(args) >= len(self.breakpoints)
        ):
            print("Usage: delete BREAKPOINTNUM")
        else:
            self.breakpoints[int(args)] = -1
            print("Deleted breakpoint %d." % int(args))

    def debug_cmd_list(self, args):
        comp = self.get_compiled()
        inst = self.curr_inst()
        if comp.get_function_addr(args):
            addr = comp.get_function_addr(args)
            start = comp.get_inst_line(addr)
            end = start + 10
        elif ',' in args:
            start, end = args.split(',', 1)
            start = start.strip()
            end = end.strip()
        elif args:
            start = end = args
        elif self.nextline < 0:
            start = str(inst.line - 5)
            end = str(inst.line + 5)
        else:
            start = self.nextline
            end = self.nextline + 10
        if not is_int(start) or not is_int(end):
            print("Usage: list [LINE[,LINE]]")
            print("   or: list FUNCNAME")
        else:
            start = int(start)
            if start < 1:
                start = 1
            if start > len(comp.srclines):
                start = len(comp.srclines)
            end = int(end)
            if end < 1:
                end = 1
            if end > len(comp.srclines):
                end = len(comp.srclines)
            self.nextline = end + 1
            for i in range(start, end + 1):
                if i == inst.line:
                    print(">% 5d: %s" % (i, comp.srclines[i - 1]))
                else:
                    print(" % 5d: %s" % (i, comp.srclines[i - 1]))

    def debug_cmd_print(self, args):
        comp = self.get_compiled()
        addr = self.curr_addr()
        fun = comp.find_func(addr)
        if comp.get_func_var(fun, args):
            v = comp.get_func_var(fun, args)
            val = self.funcvar_get(v)
        elif comp.get_global_var(args):
            v = comp.get_global_var(args)
            val = self.globalvar_get(v)
        else:
            print("Variable not found: %s" % args)
            val = None
        if val is not None:
            val = item_repr(val)
            print("%s = %s" % (args, val))

    def debug_cmd_show_breakpoints(self):
        print("Breakpoints")
        cnt = 0
        for i, bp in enumerate(self.breakpoints):
            prog, line = bp
            if line > 0:
                print("  %d: Program #%d Line %d" % (i + 1, prog, line))
                cnt += 1
        if not cnt:
            print("  - None -")

    def debug_cmd_show_functions(self):
        print("Declared Functions")
        comp = self.get_compiled()
        funcs = comp.get_functions()
        if funcs:
            for func in funcs:
                print("  %s" % func)
        else:
            print("  - None -")

    def debug_cmd_show_globals(self):
        print("Global Variables")
        comp = self.get_compiled()
        gvars = comp.get_global_vars()
        if gvars:
            for vnum, vname in enumerate(gvars):
                val = self.globalvar_get(vnum)
                val = item_repr(val)
                print("  LV%-3d %s = %s" % (vnum, vname, val))
        else:
            print("  - None -")

    def debug_cmd_show_vars(self):
        print("Function Variables")
        comp = self.get_compiled()
        addr = self.curr_addr()
        fun = comp.find_func(addr)
        fvars = comp.get_func_vars(fun)
        if fvars:
            for vnum, vname in enumerate(fvars):
                val = self.funcvar_get(vnum)
                val = item_repr(val)
                print("  SV%-3d %s = %s" % (vnum, vname, val))
        else:
            print("  - None -")

    def debug_cmd_show(self, args):
        if args == "breakpoints":
            self.debug_cmd_show_breakpoints()
        elif args == "functions":
            self.debug_cmd_show_functions()
        elif args == "globals":
            self.debug_cmd_show_globals()
        elif args == "vars":
            self.debug_cmd_show_vars()

    def debug_cmd_stack(self, args):
        if not args:
            args = "999999"
        if not is_int(args):
            print("Usage: stack [DEPTH]")
        else:
            depth = self.data_depth()
            args = int(args)
            if args > depth:
                args = depth
            for i in xrange(args):
                val = self.data_pick(i + 1)
                val = item_repr(val)
                print("Stack %d: %s" % (depth - i, val))
            if not depth:
                print("- Empty Stack -")

    def debug_cmd_trace(self, args):
        self.trace = True
        print("Turning on Trace mode.")

    def debug_cmd_notrace(self, args):
        self.trace = False
        print("Turning off Trace mode.")

    def debug_cmd_pop(self, args):
        self.data_pop()
        print("Stack item POPed.")

    def debug_cmd_dup(self, args):
        a = self.data_pick(1)
        self.data_push(a)
        print("Stack item DUPed.")

    def debug_cmd_swap(self, args):
        a = self.data_pop()
        b = self.data_pop()
        self.data_push(a)
        self.data_push(b)
        print("Stack items SWAPed.")

    def debug_cmd_rot(self, args):
        a = self.data_pop()
        b = self.data_pop()
        c = self.data_pop()
        self.data_push(b)
        self.data_push(a)
        self.data_push(c)
        print("Stack items ROTed.")

    def debug_cmd_push(self, args):
        if is_int(args):
            self.data_push(int(args))
        elif is_float(args):
            self.data_push(float(args))
        elif args[0] == '#' and is_int(args[1:]):
            self.data_push(StackDBRef(int(args[1:])))
        elif args[0] == '"' and args[-1] == '"':
            self.data_push(args[1:-1])
        print("Stack item pushed.")

    def debug_cmd_where(self, args):
        for callfr in self.call_stack:
            self.show_call(callfr.pc)

    def debug_cmd_run(self, args):
        self.data_stack = [args]
        self.call_stack = [MufCallFrame(self.start_addr, self.trigger)]
        self.catch_stack = []
        self.globalvars = {}
        print("Restarting program.")
        self.debug_cmd_list("")

    def debug_cmd_help(self, args):
        print("help               Show this message.")
        print("where              Display the call stack.")
        print("stack [DEPTH]      Show top N data stack items.")
        print("list               List next few source code lines.")
        print("list LINE          List source code LINE.")
        print("list START,END     List source code from START to END.")
        print("list FUNC          List source code at start of FUNC.")
        print("break LINE         Set breakpoint at given line.")
        print("break FUNC         Set breakpoint at start of FUNC.")
        print("delete BREAKNUM    Delete a breakpoint.")
        print("show breakpoints   Show current breakpoints.")
        print("show functions     List all declared functions.")
        print("show globals       List all global vars.")
        print("show vars          List all vars in the current func.")
        print("step [COUNT]       Step 1 or COUNT lines, enters calls.")
        print("next [COUNT]       Step 1 or COUNT lines, skips calls.")
        print("finish             Finish the current function.")
        print("cont               Continue until next breakpoint.")
        print("pop                Pop top data stack item.")
        print("dup                Duplicate top data stack item.")
        print("swap               Swap top two data stack items.")
        print("rot                Rot top three data stack items.")
        print("push VALUE         Push VALUE onto top of data stack.")
        print("print VARIABLE     Print the value of the variable.")
        print("trace              Turn on tracing of each instr.")
        print("notrace            Turn off tracing if each instr.")
        print("run COMMANDARG     Re-run program, with COMMANDARG.")
        print("quit               Exits the debugger.")

    def debug_code(self):
        prevcmd = ""
        self.nextline = -1
        readline.set_completer(self.complete)
        while True:
            if prevcmd:
                cmd = raw_input("DEBUG>")
                if not cmd:
                    cmd = prevcmd
            else:
                cmd = "list"
            prevcmd = cmd
            args = ""
            if " " in cmd:
                cmd, args = cmd.split(" ", 1)
                cmd = cmd.strip()
                args = args.strip()
            if cmd == "q" or cmd == "quit":
                print("Exiting.")
                return
            commands = {
                "break": self.debug_cmd_break,
                "c": self.debug_cmd_continue,
                "cont": self.debug_cmd_continue,
                "delete": self.debug_cmd_delete,
                "dup": self.debug_cmd_dup,
                "f": self.debug_cmd_finish,
                "finish": self.debug_cmd_finish,
                "help": self.debug_cmd_help,
                "l": self.debug_cmd_list,
                "list": self.debug_cmd_list,
                "n": self.debug_cmd_next,
                "next": self.debug_cmd_next,
                "notrace": self.debug_cmd_notrace,
                "pop": self.debug_cmd_pop,
                "p": self.debug_cmd_print,
                "print": self.debug_cmd_print,
                "push": self.debug_cmd_push,
                "rot": self.debug_cmd_rot,
                "run": self.debug_cmd_run,
                "show": self.debug_cmd_show,
                "stack": self.debug_cmd_stack,
                "s": self.debug_cmd_step,
                "step": self.debug_cmd_step,
                "swap": self.debug_cmd_swap,
                "t": self.debug_cmd_trace,
                "trace": self.debug_cmd_trace,
                "w": self.debug_cmd_where,
                "where": self.debug_cmd_where,
            }
            if cmd in commands:
                commands[cmd](args)
            else:
                self.debug_cmd_help(args)
            if not self.call_stack:
                break
            sys.stdout.flush()

    def has_errors(self):
        return self.fp_errors != 0

    def has_error(self, errname):
        errname = errname.upper()
        errnum = fp_error_names.index(errname)
        errbit = fp_error_bits[errnum]
        return (self.fp_errors & errbit) != 0

    def set_error(self, errname):
        errname = errname.upper()
        errnum = fp_error_names.index(errname)
        errbit = fp_error_bits[errnum]
        self.fp_errors |= errbit

    def clear_error(self, errname):
        errname = errname.upper()
        errnum = fp_error_names.index(errname)
        errbit = fp_error_bits[errnum]
        self.fp_errors &= ~errbit

    def clear_errors(self):
        self.fp_errors = 0


# Decorator
def literal_handler(cls):
    literal_handlers.append(cls)
    return cls


class MufCompiler(object):
    builtin_defines = {
        '__version': escape_str(EMULATED_VERSION),
        '__muckname': escape_str("MufSim"),
        '__fuzzball__': '1',
        'max_variable_count': str(MAX_VARS),

        '}array': '} array_make',
        '}list': '} array_make',
        '}dict': '} 2 / array_make_dict',
        '}join': '} array_make "" array_join',
        '}cat': '} array_make "" array_join',
        '}tell': '} array_make me @ 1 array_make array_notify',
        '[]': 'array_getitem',
        '[..]': 'array_getrange',
        '->[]': 'array_setitem',
        '[]<-': 'array_appenditem',
        'array_interpret': '"" array_join',
        'array_union': '2 array_nunion',
        'array_diff': '2 array_ndiff',
        'array_intersect': '2 array_nintersect',

        'desc': '"_/de" getpropstr',
        'idesc': '"_/ide" getpropstr',
        'succ': '"_/sc" getpropstr',
        'osucc': '"_/osc" getpropstr',
        'fail': '"_/fl" getpropstr',
        'ofail': '"_/ofl" getpropstr',
        'drop': '"_/dr" getpropstr',
        'odrop': '"_/odr" getpropstr',
        'oecho': '"_/oecho" getpropstr',
        'pecho': '"_/pecho" getpropstr',

        'setdesc': '"_/de" swap setprop',
        'setidesc': '"_/ide" swap setprop',
        'setsucc': '"_/sc" swap setprop',
        'setosucc': '"_/osc" swap setprop',
        'setfail': '"_/fl" swap setprop',
        'setofail': '"_/ofl" swap setprop',
        'setdrop': '"_/dr" swap setprop',
        'setodrop': '"_/odr" swap setprop',
        'setoecho': '"_/oecho" swap setprop',
        'setpecho': '"_/pecho" swap setprop',

        'truename': 'name',
        'version': '__version',
        'strip': 'striplead striptail',
        'event_wait': '0 array_make event_waitfor',

        'preempt': 'pr_mode setmode',
        'background': 'bg_mode setmode',
        'foreground': 'fg_mode setmode',

        'pr_mode': '0',
        'fg_mode': '1',
        'bg_mode': '2',

        'reg_icase': '1',
        'reg_all': '2',
        'reg_extended': '4',

        'sorttype_case_ascend': '0',
        'sorttype_nocase_ascend': '1',
        'sorttype_case_descend': '2',
        'sorttype_nocase_descend': '3',

        'sorttype_caseinsens': '1',
        'sorttype_descending': '2',
        'sorttype_shuffle': '4',
    }

    def __init__(self):
        self.compiled = None
        self.line = 1
        self.stmt_stack = []
        self.funcname = None
        self.defines = dict(self.builtin_defines)
        self.include_defs_from(0, suppress=True)

    def splitword(self, txt):
        txt = self.lstrip(txt)
        for i in xrange(len(txt)):
            if txt[i].isspace():
                break
            i += 1
        return (txt[:i], txt[i:])

    def lstrip(self, txt):
        i = 0
        while i < len(txt) and txt[i].isspace():
            if txt[i] == "\n":
                self.line += 1
            i += 1
        return txt[i:]

    def strip_comment(self, src):
        src = src[1:]
        lev = 1
        for i in xrange(len(src)):
            if lev <= 0:
                break
            if src[i] == "\n":
                self.line += 1
            elif src[i] == '(':
                lev += 1
            elif src[i] == ')':
                lev -= 1
        if lev > 0:
            raise MufCompileError("CommentNotTerminated")
        return src[i:]

    def get_string(self, src):
        out = '"'
        i = 1
        srclen = len(src)
        while i < srclen:
            if src[i] == "\n":
                raise MufCompileError("StringNotTerminated")
            elif src[i] == "\\":
                i += 1
                if src[i] in ["r", "n"]:
                    out += "\r"
                elif src[i] == "[":
                    out += "\033"
                else:
                    out += src[i]
            elif src[i] == '"':
                out += '"'
                src = self.lstrip(src[i + 1:])
                return (out, src)
            else:
                out += src[i]
            i += 1
        raise MufCompileError("StringNotTerminated")

    def get_to_eol(self, src):
        if "\n" in src:
            self.line += 1
            return src.split("\n", 1)
        else:
            return (src, "")

    def get_word(self, src, expand=True):
        while True:
            # Strip whitespace
            src = self.lstrip(src)
            if not src:
                return (None, None, None)
            if src[0] != '(':
                break
            src = self.strip_comment(src)
        line = self.line
        if src[0] == '"':
            word, src = self.get_string(src)
            return (word, line, src)
        # Get next word.
        word, src = self.splitword(src)
        # Expand defines if needed
        if word[0] == '\\':
            word = word[1:]
        elif expand and word in self.defines:
            src = self.defines[word] + " " + src
            word, line, src = self.get_word(src)
            return (word, line, src)
        # Return raw word.
        src = self.lstrip(src)
        return (word, line, src)

    def skip_directive_if_block(self, src):
        level = 0
        while True:
            if not src:
                raise MufCompileError("Incomplete $if directive block.")
            word, line, src = self.get_word(src)
            if word.startswith("$if"):
                cond, line, src = self.get_word(src, expand=False)
                level += 1
            elif word == "$endif":
                if not level:
                    break
                level -= 1
            elif word == "$else":
                if not level:
                    break
        return src

    def in_loop_inst(self):
        for inst in reversed(self.stmt_stack):
            if type(inst) in [InstBegin, InstFor, InstForeach]:
                return inst
        return None

    def include_defs_from(self, obj, suppress=False):
        obj = getobj(obj)
        prop = "_defs/"
        while prop:
            prop = obj.next_prop(prop, suppress=suppress)
            if not prop:
                break
            val = obj.getprop(prop, suppress=suppress)
            if val:
                defname = prop.split('/', 1)[1]
                self.defines[defname] = val

    def check_for_incomplete_block(self):
        if self.stmt_stack:
            if type(self.stmt_stack[-1]) is InstIf:
                raise MufCompileError("Incomplete if-then block.")
            if type(self.stmt_stack[-1]) is InstTry:
                raise MufCompileError("Incomplete try-catch block.")
            if type(self.stmt_stack[-1]) is InstBegin:
                raise MufCompileError("Incomplete loop.")
            if type(self.stmt_stack[-1]) is InstFor:
                raise MufCompileError("Incomplete for loop.")
            if type(self.stmt_stack[-1]) is InstForeach:
                raise MufCompileError("Incomplete foreach loop.")

    @literal_handler
    def literal_integer(self, line, code, word):
        if is_int(word):
            code.append(InstPushItem(line, int(word)))
            return True
        return False

    @literal_handler
    def literal_dbref(self, line, code, word):
        if is_dbref(word):
            code.append(InstPushItem(line, StackDBRef(int(word[1:]))))
            return True
        return False

    @literal_handler
    def literal_float(self, line, code, word):
        if is_float(word):
            code.append(InstPushItem(line, float(word)))
            return True
        return False

    @literal_handler
    def literal_string(self, line, code, word):
        if word.startswith('"'):
            code.append(InstPushItem(line, word[1:-1]))
            return True
        return False

    @literal_handler
    def literal_globalvar(self, line, code, word):
        comp = self.compiled
        if comp.get_global_var(word):
            v = comp.get_global_var(word)
            code.append(InstGlobalVar(line, v.value, word))
            return True
        return False

    @literal_handler
    def literal_funcvar(self, line, code, word):
        comp = self.compiled
        if comp.get_func_var(self.funcname, word):
            v = comp.get_func_var(self.funcname, word)
            code.append(InstFuncVar(line, v.value, word))
            return True
        return False

    @literal_handler
    def literal_tick(self, line, code, word):
        comp = self.compiled
        if word.startswith("'"):
            word = word[1:]
            addr = comp.get_function_addr(word)
            if addr is None:
                raise MufCompileError("Unrecognized identifier: %s" % word)
            code.append(InstPushItem(line, addr))
            return True
        return False

    @literal_handler
    def literal_function(self, line, code, word):
        comp = self.compiled
        if comp.get_function_addr(word) is not None:
            addr = comp.get_function_addr(word)
            code.append(InstPushItem(line, addr))
            code.append(InstExecute(line))
            return True
        return False

    def compile_r(self, src):
        code = []
        while True:
            word, line, src = self.get_word(src)
            if not word:
                return (code, src)
            if not self.funcname:
                if (
                    not word.startswith('$') and
                    word not in [":", "lvar", "var", "public", "wizcall"]
                ):
                    raise MufCompileError("Not in function: %s" % word)
            foundlit = False
            for fun in literal_handlers:
                if fun(self, line, code, word):
                    foundlit = True
                    break
            if foundlit:
                continue
            if word in primitives:
                instcls = primitives[word]
                inst = instcls(line)
                doret, src = inst.compile(self, code, src)
                if doret:
                    return (code, src)
            else:
                raise MufCompileError("Unrecognized identifier: %s" % word)

    def compile_source(self, prog):
        comp = CompiledMuf(prog)
        self.compiled = comp
        self.line = 1
        self.stmt_stack = []
        self.funcname = None
        self.defines = dict(self.builtin_defines)
        self.include_defs_from(0, suppress=True)
        src = getobj(prog).sources
        try:
            code, src = self.compile_r(src)
            if self.funcname:
                raise MufCompileError("Function incomplete.")
            self.check_for_incomplete_block()
            if code:
                for inum, inst in enumerate(code):
                    if type(inst) in [InstTry, InstJmp, InstJmpIfFalse]:
                        inst.value += inum
                comp.code = code
                getobj(prog).compiled = comp
                return True
            return False
        except MufCompileError as e:
            print("Error in line %d: %s" % (self.line, e), file=sys.stderr)
            return None


class MufSim(object):
    def print(self, *args):
        print(*args)
        sys.stdout.flush()

    def print_header(self, header):
        out = '#### %s ' % header
        out += '#' * (55 - len(out))
        self.print(out)

    def process_cmdline(self):
        parser = argparse.ArgumentParser(prog='mufsim')
        parser.add_argument("-u", "--uncompile",
                            help="Show compiled MUF tokens.",
                            action="store_true")
        parser.add_argument("-r", "--run",
                            help="Run compiled MUF tokens.",
                            action="store_true")
        parser.add_argument("--timing",
                            help="Show run execution timing.",
                            action="store_true")
        parser.add_argument("-t", "--trace",
                            help="Show stacktrace for each instrution.",
                            action="store_true")
        parser.add_argument("-d", "--debug",
                            help="Run MUF program in interactive debugger.",
                            action="store_true")
        parser.add_argument("-c", "--command", type=str, default="",
                            help="Specify text to push onto the stack for run.")
        parser.add_argument("-e", "--textentry", action='append', default=[],
                            help="Specify text to enter on READs.")
        parser.add_argument("-f", "--textfile", type=str,
                            help="File to read from for READs.")
        parser.add_argument(
            "-p", "--program", action='append', default=[],
            nargs=2, metavar=('REGNAME', 'FILE'), dest='progs',
            help="Create extra program, registered as $NAME, from source FILE."
        )
        parser.add_argument('infile', help='Input MUF sourcecode filename.')
        opts = parser.parse_args()
        opts.progs.append(['', opts.infile])
        if opts.debug:
            opts.run = True
        if opts.textfile:
            with open(opts.textfile, "r") as f:
                for line in f.readlines():
                    opts.textentry.append(line.rstrip("\n"))
        self.opts = opts
        return opts

    def readline_setup(self):
        try:
            readline.read_history_file(HISTORY_FILE)
        except:
            pass
        readline.set_history_length(1000)
        readline.parse_and_bind('tab: complete')
        readline.set_completer_delims(" ")

    def readline_teardown(self):
        try:
            readline.write_history_file(HISTORY_FILE)
        except:
            pass

    def process_muv(self, infile):
        tmpfile = infile
        if tmpfile[-4:] == ".muv":
            tmpfile = tmpfile[:-1] + 'f'
        else:
            tmpfile += ".muf"
        retcode = call(["muv", "-o", tmpfile, infile], stderr=sys.stderr)
        if retcode != 0:
            self.print("Aborting.")
            return None
        return tmpfile

    def run_code(self):
        self.readline_setup()
        fr = MufStackFrame()
        fr.setup(program_object, john_doe, trigger_action, self.opts.command)
        fr.set_trace(self.opts.trace)
        fr.set_text_entry(self.opts.textentry)
        fr.data_push(self.opts.command)
        if self.opts.debug:
            fr.debug_code()
        else:
            st = time.time()
            fr.execute_code()
            et = time.time()
            self.print("Execution completed in %d steps." % fr.cycles)
            if self.opts.timing:
                self.print("%g secs elapsed.  %g instructions/sec" %
                           (et-st, fr.cycles/(et-st)))
        self.readline_teardown()

    def main(self):
        self.process_cmdline()
        for name, filename in self.opts.progs:
            origfile = filename
            if filename.endswith(".muv"):
                self.print_header("Compiling MUV Code to MUF")
                filename = self.process_muv(filename)
                self.print("")
            if not filename:
                return
            srcs = ""
            with open(filename, "r") as f:
                srcs = f.read()
            if origfile.endswith(".muv"):
                os.unlink(filename)
            if name:
                progobj = DBObject(
                    name=name,
                    objtype="program",
                    flags="3",
                    owner=john_doe.dbref,
                    location=john_doe.dbref,
                )
                global_env.setprop(
                    "_reg/%s" % name, StackDBRef(progobj.dbref), suppress=True)
                print("CREATED PROG %s, REGISTERED AS $%s\n" % (progobj, name))
            else:
                progobj = program_object
            progobj.sources = srcs
            self.print_header("Compiling MUF Program %s" % progobj)
            success = MufCompiler().compile_source(progobj.dbref)
            self.print("")
            if not success:
                return
            if self.opts.uncompile:
                self.print_header("Showing Tokens for %s" % progobj)
                progobj.compiled.show_compiled_tokens()
                self.print("")
        if self.opts.run:
            self.print_header("Executing Tokens")
            self.run_code()
            self.print("")


if __name__ == "__main__":
    MufSim().main()


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
