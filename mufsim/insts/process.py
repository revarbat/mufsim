import time

import mufsim.gamedb as db
import mufsim.stackitems as si
# from mufsim.errors import MufRuntimeError
from mufsim.insts.base import Instruction, instr


@instr("pid")
class InstPid(Instruction):
    def execute(self, fr):
        fr.data_push(fr.pid)


@instr("ispid?")
class InstIsPidP(Instruction):
    def execute(self, fr):
        pid = fr.data_pop(int)
        fr.data_push(1 if fr.lookup_process(pid) else 0)


@instr("getpids")
class InstGetPids(Instruction):
    def execute(self, fr):
        obj = fr.get_data_dbref()
        allpids = fr.get_pids()
        if obj.value == -1:
            out = allpids
        else:
            out = []
            objtype = db.getobj(obj).objtype
            for pid in allpids:
                ofr = fr.lookup_process(pid)
                if (
                    (objtype == "player" and ofr.user == obj) or
                    (objtype == "program" and ofr.program == obj) or
                    (objtype == "exit" and ofr.trigger == obj)
                ):
                    out.append(pid)
        fr.data_push(out)


@instr("getpidinfo")
class InstGetPidInfo(Instruction):
    def execute(self, fr):
        pid = fr.data_pop(int)
        ofr = fr.lookup_process(pid)
        if not ofr:
            out = {}
        else:
            addr = ofr.curr_addr()
            currprog = si.DBRef(addr.prog) if addr else ofr.program
            out = {
                'PID': ofr.pid,
                'DESCR': ofr.descr,
                'PLAYER': ofr.user,
                'CALLED_PROG': currprog,
                'CALLED_DATA': ofr.command,
                'TRIG': ofr.trigger,
                'STARTED': ofr.start_time,
                'INSTCNT': ofr.cycles,
                'CPU': ofr.runtime,
                'TYPE': 'MUF',  # TODO: if we ever support queued MPI, update.
                'SUBTYPE': '',  # TODO: get real subtype
                'NEXTRUN': time.time(),  # TODO: Get real delay
            }
        fr.data_push(out)


@instr("instances")
class InstInstances(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_dbref()
        allpids = fr.get_pids()
        cnt = 0
        for pid in allpids:
            ofr = fr.lookup_process(pid)
            if ofr and ofr.uses_prog(obj):
                cnt += 1
        fr.data_push(cnt)


@instr("kill")
class InstKill(Instruction):
    def execute(self, fr):
        pid = fr.data_pop(int)
        if fr.lookup_process(pid):
            fr.kill_pid(pid)
            fr.data_push(1)
        else:
            fr.data_push(0)


@instr("queue")
class InstQueue(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        cmd = fr.data_pop(str)
        prog = fr.data_pop_object()
        secs = fr.data_pop(int)
        newproc = fr.proclist.new_process()
        newproc.setup(prog.dbref, fr.user, fr.program, cmd)
        newproc.sleep(secs)
        fr.data_push(newproc.pid)


@instr("fork")
class InstFork(Instruction):
    def execute(self, fr):
        newproc = fr.fork_process()
        newproc.data_push(0)
        fr.data_push(newproc.pid)


@instr("interp")
class InstInterp(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        cmd = fr.data_pop(str)
        trig = fr.data_pop_object()
        prog = fr.data_pop_object()
        newproc = fr.proclist.new_process()
        newproc.setup(prog.dbref, fr.user, trig.dbref, cmd)
        newproc.execute_code()
        fr.kill_pid(newproc.pid)
        fr.data_push(newproc.data_pop())


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
