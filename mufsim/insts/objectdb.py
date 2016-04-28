import mufsim.gamedb as db
import mufsim.stackitems as si
from mufsim.errors import MufRuntimeError
from mufsim.insts.base import Instruction, instr


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
        print("FORCE %s(#%d) TO DO: %s" % (obj.name, obj.dbref, cmd))
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
            print("arr=%s" % arr)
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


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
