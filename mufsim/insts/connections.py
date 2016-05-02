import mufsim.gamedb as db
import mufsim.stackitems as si
import mufsim.connections as conn
from mufsim.logger import log
# from mufsim.errors import MufRuntimeError
from mufsim.insts.base import Instruction, instr


@instr("awake?")
class InstAwakeP(Instruction):
    def execute(self, fr):
        who = fr.data_pop_object()
        fr.data_push(1 if conn.is_user_online(who.dbref) else 0)


@instr("online")
class InstOnline(Instruction):
    def execute(self, fr):
        users = conn.get_users_online()
        for who in users:
            fr.data_push(who)
        fr.data_push(len(users))


@instr("online_array")
class InstOnlineArray(Instruction):
    def execute(self, fr):
        fr.data_push(conn.get_users_online())


@instr("concount")
class InstConCount(Instruction):
    def execute(self, fr):
        fr.data_push(len(conn.get_descriptors()))


@instr("condbref")
class InstConDBRef(Instruction):
    def execute(self, fr):
        con = fr.data_pop(int)
        descr = conn.descr_from_con(con)
        fr.data_push(si.DBRef(conn.descr_user(descr)))


@instr("contime")
class InstConTime(Instruction):
    def execute(self, fr):
        con = fr.data_pop(int)
        descr = conn.descr_from_con(con)
        if descr >= 0:
            fr.data_push(conn.descr_time(descr))
        else:
            fr.data_push(0)


@instr("conidle")
class InstConIdle(Instruction):
    def execute(self, fr):
        con = fr.data_pop(int)
        descr = conn.descr_from_con(con)
        if descr >= 0:
            fr.data_push(conn.descr_idle(descr))
        else:
            fr.data_push(0)


@instr("conuser")
class InstConUser(Instruction):
    def execute(self, fr):
        con = fr.data_pop(int)
        descr = conn.descr_from_con(con)
        if descr >= 0:
            who = conn.descr_user(descr)
            fr.data_push(db.getobj(who).name)
        else:
            fr.data_push("")


@instr("conhost")
class InstConHost(Instruction):
    def execute(self, fr):
        con = fr.data_pop(int)
        descr = conn.descr_from_con(con)
        if descr >= 0:
            fr.data_push(conn.descr_host(descr))
        else:
            fr.data_push("")


@instr("conboot")
class InstConBoot(Instruction):
    def execute(self, fr):
        con = fr.data_pop(int)
        descr = conn.descr_from_con(con)
        if descr >= 0:
            who = conn.descr_user(descr)
            conn.disconnect(descr)
            log("BOOTED DESCRIPTOR %d: %s" % (descr, db.getobj(who)))


@instr("connotify")
class InstConNotify(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        msg = fr.data_pop(str)
        con = fr.data_pop(int)
        descr = conn.descr_from_con(con)
        if descr >= 0:
            who = conn.descr_user(descr)
            log("NOTIFY TO DESCR %d, USER %s: %s" %
                (descr, db.getobj(who), msg))


@instr("condescr")
class InstConDescr(Instruction):
    def execute(self, fr):
        con = fr.data_pop(int)
        descr = conn.descr_from_con(con)
        fr.data_push(descr)


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
