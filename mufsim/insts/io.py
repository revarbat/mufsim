import time
import mufsim.stackitems as si
import mufsim.gamedb as db
from mufsim.logger import log
from mufsim.errors import MufRuntimeError
from mufsim.interface import network_interface
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


@instr("notify_nolisten")
class InstNotifyNolisten(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        msg = fr.data_pop(str)
        who = fr.data_pop_object()
        who.notify(msg)
        me = fr.globalvar_get(0)
        if who.dbref == me.value:
            log("NOTIFY_NOLISTEN: %s" % msg)
        else:
            log("NOTIFY_NOLISTEN TO %s: %s" % (who, msg))


@instr("array_notify")
class InstArrayNotify(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        targs = fr.data_pop_list()
        msgs = fr.data_pop_list()
        fr.check_list_type(msgs, (str), argnum=1)
        fr.check_list_type(targs, (si.DBRef), argnum=2)
        for msg in msgs:
            targs = [db.getobj(o) for o in targs]
            for targ in targs:
                targ.notify(msg)
            me = fr.globalvar_get(0)
            if len(targs) == 1 and targs[0].dbref == me.value:
                log("NOTIFY: %s" % msg)
            else:
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


@instr("array_notify_secure")
class InstArrayNotifySecure(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        insmsgs = fr.data_pop_list()
        secmsgs = fr.data_pop_list()
        whoall = fr.data_pop_list()
        fr.check_list_type(whoall, (si.DBRef), argnum=1)
        fr.check_list_type(secmsgs, (str), argnum=2)
        fr.check_list_type(insmsgs, (str), argnum=3)
        me = fr.globalvar_get(0)
        for who in whoall:
            for descr in network_interface.user_descrs(who.value):
                msgarr = secmsgs if network_interface.descr_secure(descr) else insmsgs
                for msg in msgarr:
                    network_interface.descr_notify(descr, msg)
            if who.dbref == me.value:
                log("NOTIFY (SECURE): %s" % secmsg)
                log("NOTIFY (INSECURE): %s" % insmsg)
            else:
                log("NOTIFY TO %s (SECURE): %s" % (who, secmsg))
                log("NOTIFY TO %s (INSECURE): %s" % (who, insmsg))


@instr("notify_secure")
class InstNotifySecure(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        insmsg = fr.data_pop(str)
        secmsg = fr.data_pop(str)
        who = fr.data_pop_object()
        for descr in network_interface.user_descrs(who.value):
            msg = secmsg if network_interface.descr_secure(descr) else insmsg
            network_interface.descr_notify(descr, msg)
        me = fr.globalvar_get(0)
        if who.dbref == me.value:
            log("NOTIFY (SECURE): %s" % secmsg)
            log("NOTIFY (INSECURE): %s" % insmsg)
        else:
            log("NOTIFY (SECURE) TO %s: %s" % (who, secmsg))
            log("NOTIFY (INSECURE) TO %s: %s" % (who, insmsg))


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
