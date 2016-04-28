import re

import mufsim.utils as util
import mufsim.stackitems as si
import mufsim.connections as conn


player_names = {}
objects_db = {}
db_top = 0
recycled_list = []


class InvalidObjectError(Exception):
    pass


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
            self.descr = conn.connect(self.dbref)

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
                      (prop, self.dbref, util.escape_str(val)))
            else:
                print("GETPROP \"%s\" on #%d = %s" % (prop, self.dbref, val))
        return val

    def setprop(self, prop, val, suppress=False):
        prop = self.normalize_prop(prop)
        self.properties[prop] = val
        if not suppress:
            if type(val) is str:
                print("SETPROP \"%s\" on #%d = %s" %
                      (prop, self.dbref, util.escape_str(val)))
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
    elif type(obj) is si.DBRef:
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


def get_all_compiled_programs():
    return [
        si.DBRef(obj.dbref)
        for obj in objects_db
        if obj.objtype == "program" and obj.compiled
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
            if type(val) is si.DBRef:
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


def get_player_obj(who):
    return getobj(match_playername("*" + who))


def get_registered_obj(who, pat):
    who = normobj(who)
    return getobj(match_registered(getobj(who), pat, suppress=True))


def register_obj(where, name, ref):
    where = getobj(normobj(where))
    ref = si.DBRef(normobj(ref))
    where.setprop("_reg/" + name, ref, suppress=True)


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
    "@pcreate Jane_Doe=password",
    "@link *Jane_Doe=$mainroom",
    "@teleport *Jane_Doe=$mainroom",
    "@create My Thing=100=thingy",
    "connect John_Doe password"
    "connect Jane_Doe password"
]


global_env = DBObject(
    name="Global Environment Room",
    objtype="room",
    owner=1,
    props={
        "_defs/.tell": "me @ swap notify",
    },
)
register_obj(global_env, "globalenv", global_env)


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
register_obj(global_env, "testaction", trigger_action)


program_object = DBObject(
    name="cmd-test",
    objtype="program",
    flags="3",
    owner=wizard_player.dbref,
    location=wizard_player.dbref,
)
register_obj(global_env, "cmd/test", program_object)
trigger_action.links.append(program_object.dbref)


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


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
