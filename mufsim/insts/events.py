from mufsim.errors import MufRuntimeError
from mufsim.insts.base import Instruction, instr
import mufsim.stackitems as si


@instr("event_count")
class InstEventCount(Instruction):
    def execute(self, fr):
        fr.data_push(fr.events.count('*'))


@instr("event_exists")
class InstEventExists(Instruction):
    def execute(self, fr):
        pat = fr.data_pop(str)
        fr.data_push(fr.events.count(pat))


@instr("event_send")
class InstEventSend(Instruction):
    def execute(self, fr):
        data = fr.data_pop()
        name = fr.data_pop(str)
        pid = fr.data_pop(int)
        ofr = fr.lookup_process(pid)
        if not ofr:
            raise MufRuntimeError("No such Process.")
        ofr.events.add_event(
            "USER." + name[:32],
            dict(
                data=data,
                caller_pid=fr.pid,
                caller_prog=fr.caller_get(),
                descr=fr.descr,
                trigger=si.DBRef(fr.trigger),
                player=si.DBRef(fr.user),
            )
        )


@instr("timer_start")
class InstTimerStart(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        name = fr.data_pop(str)
        secs = fr.data_pop(int)
        fr.timer_start(secs, name)


@instr("timer_stop")
class InstTimerStop(Instruction):
    def execute(self, fr):
        name = fr.data_pop(str)
        fr.timer_stop(name)


@instr("watchpid")
class InstWatchPid(Instruction):
    def execute(self, fr):
        pid = fr.data_pop(int)
        fr.watch_pid(pid)


@instr("event_waitfor")
class InstEventWaitFor(Instruction):
    def execute(self, fr):
        pats = fr.data_pop(list)
        for pat in pats:
            fr.check_type(pat, [str])
        fr.pc_advance(1)
        fr.wait_for_events(pats)


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
