import mufsim.gamedb as db
import mufsim.stackitems as si
from mufsim.interface import network_interface as netifc
from mufsim.logger import log
from mufsim.errors import MufRuntimeError
from mufsim.insts.base import Instruction, instr


@instr("descriptors")
class InstDescriptors(Instruction):
    def execute(self, fr):
        who = fr.data_pop_dbref()
        if who.value == -1:
            descrs = netifc.get_descriptors()
        else:
            if db.getobj(who).objtype != "player":
                raise MufRuntimeError("Expected #-1 or player dbref.")
            descrs = netifc.user_descrs(who.value)
        for descr in descrs:
            fr.data_push(descr)
        fr.data_push(len(descrs))


@instr("descr_array")
class InstDescrArray(Instruction):
    def execute(self, fr):
        who = fr.data_pop_dbref()
        if who.value == -1:
            descrs = netifc.get_descriptors()
        else:
            if db.getobj(who).objtype != "player":
                raise MufRuntimeError("Expected #-1 or player dbref.")
            descrs = netifc.user_descrs(who.value)
        fr.data_push(descrs)


@instr("descrcon")
class InstDescrCon(Instruction):
    def execute(self, fr):
        descr = fr.data_pop(int)
        fr.data_push(netifc.descr_con(descr))


@instr("descrdbref")
class InstDescrDBRef(Instruction):
    def execute(self, fr):
        descr = fr.data_pop(int)
        fr.data_push(si.DBRef(netifc.descr_dbref(descr)))


@instr("descr_setuser")
class InstDescrSetUser(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        pw = fr.data_pop(str)
        who = fr.data_pop_object()
        descr = fr.data_pop(int)
        if who.objtype != "player":
            raise MufRuntimeError("Expected player dbref.")
        was = netifc.descr_dbref(descr)
        if db.getobj(who).password != pw:
            raise MufRuntimeError("Incorrect password!")
        if netifc.descr_set_user(descr, who.dbref):
            was = db.getobj(was)
            # TODO: actually check password?
            log("RECONNECTED DESCRIPTOR %d FROM %s TO %s USING PW '%s'" %
                (descr, was, who, pw))


@instr("descrboot")
class InstDescrBoot(Instruction):
    def execute(self, fr):
        descr = fr.data_pop(int)
        who = netifc.descr_dbref(descr)
        if netifc.descr_disconnect(descr):
            log("BOOTED DESCRIPTOR %d: %s" % (descr, db.getobj(who)))


@instr("descrnotify")
class InstDescrNotify(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        msg = fr.data_pop(str)
        descr = fr.data_pop(int)
        who = netifc.descr_dbref(descr)
        if netifc.is_descr_online(descr):
            log("NOTIFY TO DESCR %d, %s: %s" %
                (descr, db.getobj(who), msg))


@instr("descrflush")
class InstDescrFlush(Instruction):
    def execute(self, fr):
        descr = fr.data_pop(int)
        if descr == -1:
            netifc.flush_all_descrs()
            log("DESCRFLUSH ALL DESCRS.")
        elif netifc.is_descr_online(descr):
            netifc.descr_flush(descr)
            who = netifc.descr_dbref(descr)
            log("DESCRFLUSH %d, %s" % (descr, db.getobj(who)))


@instr("descr")
class InstDescr(Instruction):
    def execute(self, fr):
        # TODO: get real descr.
        fr.data_push(db.getobj(fr.user).descr)


@instr("firstdescr")
class InstFirstDescr(Instruction):
    def execute(self, fr):
        who = fr.data_pop_dbref()
        if who.value < 0:
            descrs = netifc.get_descriptors()
        else:
            descrs = netifc.user_descrs(who.value)
        if descrs:
            fr.data_push(descrs[0])
        else:
            fr.data_push(0)


@instr("lastdescr")
class InstLastDescr(Instruction):
    def execute(self, fr):
        who = fr.data_pop_dbref()
        if who.value < 0:
            descrs = netifc.get_descriptors()
        else:
            descrs = netifc.user_descrs(who.value)
        if descrs:
            fr.data_push(descrs[-1])
        else:
            fr.data_push(0)


@instr("nextdescr")
class InstNextDescr(Instruction):
    def execute(self, fr):
        descr = fr.data_pop(int)
        descrs = netifc.get_descriptors()
        if descr in descrs:
            pos = descrs.index(descr) + 1
            if pos >= len(descrs):
                fr.data_push(0)
            else:
                fr.data_push(descrs[pos])
        else:
            fr.data_push(0)


@instr("descrbufsize")
class InstDescrBufSize(Instruction):
    def execute(self, fr):
        descr = fr.data_pop(int)
        fr.data_push(netifc.descr_bufsize(descr))


@instr("descrsecure?")
class InstDescrSecureP(Instruction):
    def execute(self, fr):
        descr = fr.data_pop(int)
        fr.data_push(1 if netifc.descr_secure(descr) else 0)


@instr("descruser")
class InstDescrUser(Instruction):
    def execute(self, fr):
        descr = fr.data_pop(int)
        who = netifc.descr_user(descr)
        if who >= 0:
            fr.data_push(db.getobj(who).name)
        else:
            fr.data_push("")


@instr("descrhost")
class InstDescrHost(Instruction):
    def execute(self, fr):
        descr = fr.data_pop(int)
        fr.data_push(netifc.descr_host(descr))


@instr("descrtime")
class InstDescrTime(Instruction):
    def execute(self, fr):
        descr = fr.data_pop(int)
        fr.data_push(netifc.descr_time(descr))


@instr("descridle")
class InstDescrIdle(Instruction):
    def execute(self, fr):
        descr = fr.data_pop(int)
        fr.data_push(netifc.descr_idle(descr))


@instr("descrleastidle")
class InstDescrLeastIdle(Instruction):
    def execute(self, fr):
        who = fr.data_pop_object()
        descrs = netifc.user_descrs(who.dbref)
        idles = [netifc.descr_idle(descr) for descr in descrs]
        fr.data_push(min(idles))


@instr("descrmostidle")
class InstDescrMostIdle(Instruction):
    def execute(self, fr):
        who = fr.data_pop_object()
        descrs = netifc.user_descrs(who.dbref)
        idles = [netifc.descr_idle(descr) for descr in descrs]
        fr.data_push(max(idles))


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
