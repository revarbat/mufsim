import mufsim.gamedb as db
import mufsim.stackitems as si
import mufsim.sysparms as sysparm
from mufsim.logger import log
from mufsim.errors import MufRuntimeError
from mufsim.insts.base import Instruction, instr


@instr("sysparm")
class InstSysParm(Instruction):
    def execute(self, fr):
        name = fr.data_pop(str)
        val = sysparm.get_sysparm_value(name)
        if val is None:
            raise MufRuntimeError("Non-existent sysparm.")
        fr.data_push(val)


@instr("setsysparm")
class InstSetSysParm(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        val = fr.data_pop(str)
        name = fr.data_pop(str)
        typ = sysparm.get_sysparm_type(name)
        if typ is None:
            raise MufRuntimeError("Non-existent sysparm.")
        if typ == "dbref":
            val = db.match_from(db.getobj(fr.user), val)
            if not db.validobj(val):
                raise MufRuntimeError("I don't know what object you mean!")
        elif typ == "integer" or typ == "timespan":
            try:
                val = int(val)
            except:
                raise MufRuntimeError("Not a valid integer!")
        elif typ == "boolean":
            val = 1 if val == "1" or val.lower() == "true" else 0
        sysparm.set_sysparm_value(name, val)


@instr("sysparm_array")
class InstSysParmArray(Instruction):
    def execute(self, fr):
        pat = fr.data_pop(str)
        out = [
            sysparm.get_sysparm_info(name)
            for name in sysparm.get_sysparm_names(pat)
        ]
        fr.data_push(out)


@instr("dbref")
class InstDBRef(Instruction):
    def execute(self, fr):
        val = fr.data_pop(int)
        fr.data_push(si.DBRef(val))


@instr("match")
class InstMatch(Instruction):
    def execute(self, fr):
        pat = fr.data_pop(str).lower()
        if pat == "me":
            obj = db.getobj(fr.user).dbref
        elif pat == "here":
            obj = db.getobj(db.getobj(fr.user).location).dbref
        elif pat == "home":
            obj = -3
        else:
            obj = db.match_from(db.getobj(fr.user), pat)
        fr.data_push(si.DBRef(obj))


@instr("rmatch")
class InstRMatch(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        pat = fr.data_pop(str).lower()
        remote = fr.data_pop_object()
        if pat == "me":
            obj = db.getobj(fr.user).dbref
        elif pat == "here":
            obj = db.getobj(db.getobj(fr.user).location).dbref
        elif pat == "home":
            obj = -3
        else:
            obj = db.match_from(remote, pat)
        fr.data_push(si.DBRef(obj))


@instr("pmatch")
class InstPMatch(Instruction):
    def execute(self, fr):
        nam = fr.data_pop(str)
        obj = db.match_playername("*" + nam)
        fr.data_push(si.DBRef(obj))


@instr("part_pmatch")
class InstPartPMatch(Instruction):
    def execute(self, fr):
        nam = fr.data_pop(str)
        obj = db.match_playername_prefix(nam)
        fr.data_push(si.DBRef(obj))


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
        fr.data_push(1 if db.ok_name(nam) else 0)


@instr("pname-ok?")
class InstPNameOkP(Instruction):
    def execute(self, fr):
        nam = fr.data_pop(str)
        fr.data_push(1 if db.ok_player_name(nam) else 0)


@instr("ext-name-ok?")
class InstExtNameOkP(Instruction):
    def execute(self, fr):
        obj = fr.data_pop(str, si.DBRef)
        nam = fr.data_pop(str)
        if type(obj) is si.DBRef:
            typ = db.getobj(obj).objtype
        else:
            typ = obj
        if typ == "player":
            fr.data_push(1 if db.ok_player_name(nam) else 0)
        else:
            fr.data_push(1 if db.ok_name(nam) else 0)


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
        fr.data_push(si.DBRef(obj.owner))


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
            fr.data_push(si.DBRef(obj.contents[0]))
        else:
            fr.data_push(si.DBRef(-1))


@instr("contents_array")
class InstContentsArray(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_object()
        arr = [si.DBRef(x) for x in obj.contents]
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
        log("FORCE %s(#%d) TO DO: %s" % (obj.name, obj.dbref, cmd))
        # TODO: Real forcing!  (pipe dream)
        # obj.force(cmd)


@instr("force_level")
class InstForceLevel(Instruction):
    def execute(self, fr):
        # TODO: use real force level.
        fr.data_push(0)


@instr("exits")
class InstExits(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_object()
        if obj.exits:
            fr.data_push(si.DBRef(obj.exits[0]))
        else:
            fr.data_push(si.DBRef(-1))


@instr("exits_array")
class InstExitsArray(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_object()
        arr = [si.DBRef(x) for x in obj.exits]
        fr.data_push(arr)


@instr("next")
class InstNext(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_object()
        loc = obj.location
        if loc < 0:
            fr.data_push(si.DBRef(-1))
            return
        if obj.objtype == "exit":
            arr = db.getobj(loc).exits
        else:
            arr = db.getobj(loc).contents
        if obj.dbref not in arr:
            raise MufRuntimeError("DB inconsistent!")
        idx = arr.index(obj.dbref)
        if idx == len(arr) - 1:
            fr.data_push(si.DBRef(-1))
        else:
            fr.data_push(si.DBRef(arr[idx + 1]))


@instr("dbtop")
class InstDBTop(Instruction):
    def execute(self, fr):
        fr.data_push(db.get_db_top())


@instr("location")
class InstLocation(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_object()
        fr.data_push(si.DBRef(obj.location))


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
            if type(dest) is not si.DBRef:
                raise MufRuntimeError("Expected list array of dbrefs.")
        obj.links = [db.getobj(dest).dbref for dest in dests]


@instr("getlink")
class InstGetLink(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_object()
        fr.data_push(si.DBRef(obj.links[0]))


@instr("getlinks")
class InstGetLinks(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_object()
        for link in obj.links:
            fr.data_push(si.DBRef(link))
        fr.data_push(len(obj.links))


@instr("getlinks_array")
class InstGetLinksArray(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_object()
        fr.data_push([si.DBRef(x) for x in obj.links])


@instr("entrances_array")
class InstEntrancesArray(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_object()
        arr = [si.DBRef(o) for o in db.entrances_array(obj)]
        fr.data_push(arr)


@instr("copyobj")
class InstCopyObj(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_object()
        if obj.objtype != "thing":
            raise MufRuntimeError("Expected thing dbref.")
        fr.data_push(si.DBRef(db.copyobj(obj).dbref))


@instr("copyplayer")
class InstCopyPlayer(Instruction):
    def execute(self, fr):
        pw = fr.data_pop(str)  # noqa
        name = fr.data_pop(str)
        obj = fr.data_pop_object()
        if obj.objtype != "player":
            raise MufRuntimeError("Expected player dbref.")
        if db.match_playername("*" + name) >= 0:
            raise MufRuntimeError("Player name already in use.")
        obj = db.copyobj(obj)
        obj.name = name
        # TODO: set password for real
        fr.data_push(si.DBRef(obj.dbref))


@instr("newplayer")
class InstNewPlayer(Instruction):
    def execute(self, fr):
        pw = fr.data_pop(str)  # noqa
        name = fr.data_pop(str)
        obj = db.DBObject(
            name=name,
            objtype="player",
            flags="",
            location=db.get_registered_obj(db.getobj(fr.user), "$mainroom"),
            props={},
        )
        fr.data_push(si.DBRef(obj.dbref))


@instr("newroom")
class InstNewRoom(Instruction):
    def execute(self, fr):
        name = fr.data_pop(str)
        parent = fr.data_pop_object()
        if parent.objtype not in ["room", "thing"]:
            raise MufRuntimeError("Expected room or thing dbref.")
        obj = db.DBObject(
            name=name,
            objtype="room",
            location=parent.dbref,
            owner=db.getobj(fr.user).dbref
        )
        fr.data_push(si.DBRef(obj.dbref))


@instr("newobject")
class InstNewObject(Instruction):
    def execute(self, fr):
        name = fr.data_pop(str)
        parent = fr.data_pop_object()
        if parent.objtype not in ["room", "thing", "player"]:
            raise MufRuntimeError("Expected room or thing or player dbref.")
        obj = db.DBObject(
            name=name,
            objtype="thing",
            location=parent.dbref,
            owner=db.getobj(fr.user).dbref
        )
        fr.data_push(si.DBRef(obj.dbref))


@instr("newexit")
class InstNewExit(Instruction):
    def execute(self, fr):
        name = fr.data_pop(str)
        parent = fr.data_pop_object()
        if parent.objtype not in ["room", "thing", "player"]:
            raise MufRuntimeError("Expected room or thing or player dbref.")
        obj = db.DBObject(
            name=name,
            objtype="exit",
            location=parent.dbref,
            owner=db.getobj(fr.user).dbref
        )
        fr.data_push(si.DBRef(obj.dbref))


@instr("newprogram")
class InstNewProgram(Instruction):
    def execute(self, fr):
        name = fr.data_pop(str)
        obj = db.DBObject(
            name=name,
            objtype="program",
            location=db.getobj(fr.user).dbref,
            owner=db.getobj(fr.user).dbref,
        )
        fr.data_push(si.DBRef(obj.dbref))


@instr("recycle")
class InstRecycle(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_object()
        if obj.objtype == "player":
            raise MufRuntimeError("Expected non-player dbref.")
        protect = [cl.pc.prog for cl in fr.call_stack]
        if obj.dbref in protect:
            raise MufRuntimeError("Cannot recycle running program.")
        db.recycle_object(obj)


@instr("nextowned")
class InstNextOwned(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_object()
        fr.data_push(si.DBRef(db.nextowned(obj)))


@instr("nextentrance")
class InstNextEntrance(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        obj = fr.data_pop_dbref()
        targ = fr.data_pop_object()
        fr.data_push(si.DBRef(db.nextentrance(targ, obj)))


@instr("findnext")
class InstFindNext(Instruction):
    def execute(self, fr):
        fr.check_underflow(4)
        flags = fr.data_pop(str)
        name = fr.data_pop(str)
        own = fr.data_pop_dbref()
        obj = fr.data_pop_dbref()
        fr.data_push(si.DBRef(db.findnext(obj, own.value, name, flags)))


@instr("stats")
class InstStats(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_dbref()
        if obj.value == -1:
            stats = db.obect_db_statistics(-1)
        elif not db.validobj(obj) or db.getobj(obj).objtype != "player":
            raise MufRuntimeError("Expected #-1 or player dbref.")
        else:
            stats = db.obect_db_statistics(obj.value)
        fr.data_push(stats['total'])
        fr.data_push(stats['rooms'])
        fr.data_push(stats['exits'])
        fr.data_push(stats['things'])
        fr.data_push(stats['programs'])
        fr.data_push(stats['players'])
        fr.data_push(stats['garbages'])


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
