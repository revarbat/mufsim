import re
import copy
import time

from mufsim.errors import MufRuntimeError
import mufsim.utils as util
import mufsim.stackitems as si
import mufsim.connections as conn
from mufsim.logger import log


player_names = {}
objects_db = {}
db_top = 0
recycled_list = []


class InvalidObjectError(Exception):
    pass


class DBObject(object):
    def __init__(
        self, name, objtype="thing", owner=-1,
        props={}, flags="", location=-1,
        regname=None, passwd=None,
    ):
        global db_top
        global player_names
        global recycled_list
        if recycled_list:
            self.dbref = recycled_list.pop()
        else:
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
        self.blessed_properties = {}
        self.properties = props
        objects_db[self.dbref] = self
        self.moveto(location)
        self.descr = -1
        self.sources = None
        self.compiled = None
        self.password = None
        self.ts_created = int(time.time())
        self.ts_modified = int(time.time())
        self.ts_lastused = int(time.time())
        self.ts_usecount = 0
        if objtype == "player":
            player_names[self.name.lower()] = self.dbref
            self.descr = conn.connect(self.dbref)
            self.password = passwd
        if regname:
            register_obj(0, regname, si.DBRef(self.dbref))

    def mark_modify(self):
        self.ts_modified = int(time.time())

    def mark_use(self):
        self.ts_lastused = int(time.time())
        self.ts_usecount += 1

    def moveto(self, dest):
        self.mark_modify()
        loc = self.location
        if loc >= 0:
            locobj = getobj(loc)
            locobj.mark_modify()
            if self.objtype == "exit":
                idx = locobj.exits.index(self.dbref)
                del locobj.exits[idx]
            else:
                idx = locobj.contents.index(self.dbref)
                del locobj.contents[idx]
        dest = normobj(dest)
        if dest >= 0:
            destobj = getobj(dest)
            destobj.mark_modify()
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
            if isinstance(val, str):
                log("GETPROP \"%s\" on #%d = %s" %
                    (prop, self.dbref, util.escape_str(val)))
            else:
                log("GETPROP \"%s\" on #%d = %s" % (prop, self.dbref, val))
        return val

    def setprop(self, prop, val, suppress=False):
        prop = self.normalize_prop(prop)
        self.mark_modify()
        self.properties[prop] = val
        if not suppress:
            if isinstance(val, str):
                log("SETPROP \"%s\" on #%d = %s" %
                    (prop, self.dbref, util.escape_str(val)))
            else:
                log("SETPROP \"%s\" on #%d = %s" % (prop, self.dbref, val))

    def delprop(self, prop):
        prop = self.normalize_prop(prop)
        log("DELPROP \"%s\" on #%d" % (prop, self.dbref))
        self.mark_modify()
        if prop in self.properties:
            del self.properties[prop]
        prop += '/'
        for prp in self.properties:
            prp = self.normalize_prop(prp)
            if prp.startswith(prop):
                del self.properties[prp]
                log("DELPROP \"%s\" on #%d" % (prp, self.dbref))

    def is_propdir(self, prop):
        prop = self.normalize_prop(prop)
        val = False
        prop += '/'
        for prp in self.properties:
            prp = self.normalize_prop(prp)
            if prp.startswith(prop):
                val = True
                break
        log("PROPDIR? \"%s\" on #%d = %s" % (prop, self.dbref, val))
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
            log("NEXTPROP \"%s\" on #%d = \"%s\"" % (prop, self.dbref, out))
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
        log("PROPDIRPROPS \"%s\" on #%d = %s" % (prop, self.dbref, out))
        return out

    def blessprop(self, prop, suppress=False):
        prop = self.normalize_prop(prop)
        self.mark_modify()
        if prop in self.properties:
            self.blessed_properties[prop] = 1
        if not suppress:
            log("BLESSPROP \"%s\" on #%d" % (prop, self.dbref))
        return

    def unblessprop(self, prop, suppress=False):
        prop = self.normalize_prop(prop)
        self.mark_modify()
        if prop in self.properties:
            del self.blessed_properties[prop]
        if not suppress:
            log("UNBLESSPROP \"%s\" on #%d" % (prop, self.dbref))
        return

    def is_blessed(self, prop, suppress=False):
        prop = self.normalize_prop(prop)
        val = prop in self.blessed_properties
        if not suppress:
            log("IS_BLESSED \"%s\" on #%d = %s" % (prop, self.dbref, val))
        return val

    def __repr__(self):
        return "%s(#%d)" % (self.name, self.dbref)


def normobj(obj):
    if isinstance(obj, DBObject):
        obj = obj.dbref
    elif isinstance(obj, si.DBRef):
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
        raise InvalidObjectError("Invalid object.")
    return objects_db[obj]


def get_db_top():
    return db_top


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


def get_all_programs():
    return [
        si.DBRef(ref)
        for ref, obj in objects_db.items()
        if obj.objtype == "program"
    ]


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


def match_playername_prefix(pat):
    global player_names
    pat = pat.strip().lower()
    found = -1
    for name, dbref in player_names.items():
        if name.startswith(pat):
            if found == -1:
                found = dbref
            else:
                found = -2
    return found


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
    if not util.is_int(pat[1:]):
        return -1
    return int(pat[1:])


def match_registered(remote, pat, suppress=False):
    if not pat.startswith("$"):
        return -1
    obj = -1
    for targ in get_env_objects(remote):
        val = targ.getprop("_reg/" + pat[1:], suppress=suppress)
        if val:
            if isinstance(val, si.DBRef):
                val = val.value
            elif isinstance(val, str) and val[0] == '#':
                val = int(val[1:])
            if isinstance(val, int):
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


def get_player_obj(who):
    return getobj(match_playername("*" + who))


def get_registered_obj(who, pat):
    who = normobj(who)
    return getobj(match_registered(getobj(who), pat, suppress=True))


def register_obj(where, name, ref):
    where = getobj(normobj(where))
    ref = si.DBRef(normobj(ref))
    where.setprop("_reg/" + name, ref, suppress=True)


def entrances_array(targ):
    targ = getobj(normobj(targ))
    out = []
    for dbref, obj in objects_db.items():
        for link in obj.links:
            if link == targ.dbref:
                out.append(dbref)
    return out


def copyobj(obj):
    global recycled_list
    global objects_db
    global db_top
    obj = getobj(normobj(obj))
    obj = copy.deepcopy(obj)
    if recycled_list:
        obj.dbref = recycled_list.pop()
    else:
        obj.dbref = db_top
        db_top += 1
        objects_db[obj.dbref] = obj
    return obj


def toadplayer(toad, inheritor):
    global objects_db
    toad = getobj(normobj(toad))
    inheritor = getobj(normobj(inheritor))
    if toad.objtype != "player":
        raise MufRuntimeError("Expected valid player object.")
    if inheritor.objtype != "player":
        raise MufRuntimeError("Expected valid player object.")
    if toad.dbref <= 1:
        raise MufRuntimeError("Cannot toad #1.")
    toad.objtype = "thing"
    toad.name = "A slimy toad named %s" % toad.name
    toad.flags = ""
    toad.owner = inheritor.dbref
    toad.moveto(inheritor)
    toad.links = []
    toad.descr = -1
    for dbref, obj in objects_db.items():
        if obj.owner == toad.dbref:
            obj.owner = inheritor.dbref


def recycle_object(obj):
    global recycled_list
    obj = getobj(normobj(obj))
    if obj.objtype == "player":
        raise MufRuntimeError("Expected valid non-player object.")
    if obj.dbref <= 1:
        raise MufRuntimeError("Cannot recycle #0 or #1.")
    obj.objtype = "garbage"
    obj.name = "Garbage"
    obj.flags = ""
    obj.owner = -1
    obj.location = -1
    obj.contents = []
    obj.exits = []
    obj.links = []
    obj.pennies = 0
    obj.properties = {}
    obj.descr = -1
    obj.sources = None
    obj.compiled = None
    recycled_list.append(obj.dbref)


def obect_db_statistics(who):
    stats = dict(
        total=0,
        players=0,
        rooms=0,
        things=0,
        exits=0,
        programs=0,
        garbages=0,
    )
    for dbref, obj in objects_db.items():
        if who == -1 or obj.owner == who:
            stats[obj.objtype + 's'] += 1
            stats['total'] += 1
    return stats


def flagsmatch(flags, obj):
    type_map = {
        'E': "exit",
        'F': "program",
        'G': "garbage",
        'P': "player",
        'R': "room",
        'T': "thing",
    }
    obj = getobj(obj)
    good = True
    invert = False
    for flg in list(flags.upper()):
        goodpass = True
        mlev = 1 if '1' in obj.flags else 0
        mlev += 2 if '2' in obj.flags else 0
        mlev += 3 if '3' in obj.flags else 0
        if flg == '!':
            invert = not invert
            continue
        elif flg in type_map:
            goodpass = type_map[flg] == obj.objtype
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
    return good


def findnext(obj, own, name, flags):
    obj = normobj(obj)
    found = obj == -1
    for dbref, o in objects_db.items():
        if not found:
            if dbref == obj:
                found = True
            continue
        if own != -1 and o.owner != own:
            continue
        if name and not util.smatch(name, o.name):
            continue
        if flags and not flagsmatch(flags, o):
            continue
        return dbref
    return -1


def nextentrance(targ, obj):
    targ = getobj(normobj(targ))
    obj = normobj(obj)
    found = obj == -1
    for dbref, o in objects_db.items():
        if not found:
            if dbref == obj:
                found = True
            continue
        for link in o.links:
            if link == targ.dbref:
                return dbref
    return -1


def nextowned(obj):
    obj = getobj(normobj(obj))
    if obj.objtype == "player":
        for dbref, o in objects_db.items():
            if o.owner == obj.owner:
                return o.dbref
        return -1
    found = False
    for dbref, o in objects_db.items():
        if not found:
            if dbref == obj.dbref:
                found = True
            continue
        if o.objtype == "player":
            continue
        if o.owner == obj.owner:
            return o.dbref
    return -1


# Notional build system to make custom databases easier to create.
# Doesn't actually do anything yet.
build_commands = [
    "@dig Main Room=#0=mainroom",
    "@action test=$mainroom=testaction",
    "@program cmd-test=cmd/test",
    "@set $cmd/test=3",
    "@link $testaction=$cmd/test",
    "@pcreate John_Doe=password",
    "@set *John_Doe=3",
    "@chown $cmd/test=John_Doe",
    "@link *John_Doe=$mainroom",
    "@teleport *John_Doe=$mainroom",
    "@pcreate Jane_Doe=password2",
    "@link *Jane_Doe=$mainroom",
    "@teleport *Jane_Doe=$mainroom",
    "@create My Thing=100=thingy",
    "connect John_Doe password"
    "connect Jane_Doe password2"
]


def init_object_db():
    global player_names
    global objects_db
    global db_top
    global recycled_list

    player_names = {}
    objects_db = {}
    db_top = 0
    recycled_list = []

    DBObject(
        name="Global Environment Room",
        objtype="room",
        owner=1,
        props={
            "_defs/.tell": "me @ swap notify",
        },
        regname="globalenv",
    )

    wizard_player = DBObject(
        name="Wizard",
        objtype="player",
        flags="W3",
        location=0,
        passwd="WizPass",
        props={
            "sex": "male"
        },
    )

    main_room = DBObject(
        name="Main Room",
        objtype="room",
        location=0,
        owner=wizard_player.dbref,
        regname="mainroom",
    )

    trigger_action = DBObject(
        name="test",
        objtype="exit",
        owner=wizard_player.dbref,
        location=main_room.dbref,
        regname="testaction",
    )

    program_object = DBObject(
        name="Untitled.muf",
        objtype="program",
        flags="3",
        owner=wizard_player.dbref,
        location=wizard_player.dbref,
        regname="cmd/test",
    )
    trigger_action.links.append(program_object.dbref)

    DBObject(
        name="John_Doe",
        objtype="player",
        flags="3",
        location=main_room.dbref,
        passwd="password",
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

    DBObject(
        name="Jane_Doe",
        objtype="player",
        flags="1",
        location=main_room.dbref,
        passwd="password2",
        props={
            "sex": "female"
        },
    )

    DBObject(
        name="My Thing",
        objtype="thing",
        flags="",
        location=main_room.dbref,
        props={},
        regname="testthing",
    )


init_object_db()


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
