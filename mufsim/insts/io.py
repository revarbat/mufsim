import time
import mufsim.stackitems as si
import mufsim.gamedb as db
from mufsim.logger import log
from mufsim.errors import MufRuntimeError
from mufsim.insts.base import Instruction, instr


@instr("read_wants_blanks")
class InstReadWantsBlanks(Instruction):
    def execute(self, fr):
        fr.read_wants_blanks = True


@instr("read")
class InstRead(Instruction):
    def execute(self, fr):
        if fr.execution_mode == fr.MODE_BACKGROUND:
            raise MufRuntimeError("Cannot READ in background process.")
        fr.wait_for_read()


@instr("userlog")
class InstUserLog(Instruction):
    def execute(self, fr):
        s = fr.data_pop(str)
        msg = "%s [%s] %s: %s\n" % (
            db.getobj(fr.user),
            db.getobj(fr.program),
            time.strftime("%m/%d/%y %H/%M/%S"),
            s
        )
        with open("userlog.log", "a") as f:
            f.write(msg)
        log("USERLOG: %s" % msg)


@instr("notify")
class InstNotify(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        msg = fr.data_pop(str)
        who = fr.data_pop_object()
        who.notify(msg)
        me = fr.globalvar_get(0)
        if who.dbref == me.value:
            log("NOTIFY: %s" % msg)
        else:
            log("NOTIFY TO %s: %s" % (who, msg))


@instr("array_notify")
class InstArrayNotify(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        targs = fr.data_pop(list)
        msgs = fr.data_pop(list)
        for targ in targs:
            if not isinstance(targ, si.DBRef):
                raise MufRuntimeError("Expected list array of dbrefs. (2)")
        for msg in msgs:
            if not isinstance(msg, str):
                raise MufRuntimeError("Expected list array of strings. (1)")
        for msg in msgs:
            targs = [db.getobj(o) for o in targs]
            for targ in targs:
                targ.notify(msg)
            log("NOTIFY TO %s: %s" % (targs, msg))


@instr("notify_except")
class InstNotifyExcept(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        msg = fr.data_pop(str)
        who = fr.data_pop_dbref()
        where = fr.data_pop_object()
        for ref in where.contents:
            if ref != who.value:
                db.getobj(ref).notify(msg)
        if db.validobj(who):
            who = db.getobj(who)
            log("NOTIFY TO ALL IN %s EXCEPT %s: %s" % (where, who, msg))
        else:
            log("NOTIFY TO ALL IN %s: %s" % (where, msg))


@instr("notify_exclude")
class InstNotifyExclude(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        msg = fr.data_pop(str)
        pcount = fr.data_pop(int)
        fr.check_underflow(pcount + 1)
        excl = []
        for i in range(pcount):
            who = fr.data_pop_object()
            excl.append(who.dbref)
        where = fr.data_pop_object()
        for ref in where.contents:
            if ref not in excl:
                db.getobj(ref).notify(msg)
        excls = [db.getobj(o) for o in excl if db.validobj(o)]
        if excls:
            log("NOTIFY TO ALL IN %s EXCEPT %s: %s" % (where, excls, msg))
        else:
            log("NOTIFY TO ALL IN %s: %s" % (where, msg))


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
