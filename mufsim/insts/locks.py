import mufsim.locks as locks
import mufsim.stackitems as si
from mufsim.errors import MufRuntimeError
from mufsim.insts.base import Instruction, instr


@instr("locked?")
class InstLockedP(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        what = fr.data_pop_object()
        who = fr.data_pop_object()
        lock = what.getprop("_/lok")
        if not isinstance(lock, si.Lock):
            raise MufRuntimeError("Expected lock in property.")
        fr.data_push(0 if lock.value.eval(who) else 1)


@instr("parselock")
class InstParseLock(Instruction):
    def execute(self, fr):
        lockstr = fr.data_pop(str)
        lock = locks.lock_parse(lockstr, fr.user)
        fr.data_push(si.Lock(lock))


@instr("unparselock")
class InstUnParseLock(Instruction):
    def execute(self, fr):
        lock = fr.data_pop(si.Lock)
        fr.data_push(str(lock.value))


@instr("prettylock")
class InstPrettyLock(Instruction):
    def execute(self, fr):
        lock = fr.data_pop(si.Lock)
        fr.data_push(lock.value.pretty())


@instr("testlock")
class InstTestLock(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        lock = fr.data_pop(si.Lock)
        who = fr.data_pop_object()
        fr.data_push(1 if lock.value.eval(who) else 0)


@instr("setlockstr")
class InstSetLockStr(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        lockstr = fr.data_pop(str)
        what = fr.data_pop_object()
        lock = locks.lock_parse(lockstr, fr.user)
        if lock:
            what.setprop("_/lok", si.Lock(lock))
            fr.data_push(1)
        else:
            fr.data_push(0)


@instr("getlockstr")
class InstGetLockStr(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_object()
        lock = obj.getprop("_/lok")
        if not isinstance(lock, si.Lock):
            fr.data_push("*UNLOCKED*")
        else:
            fr.data_push(str(lock.value))


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
