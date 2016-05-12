import time

# from mufsim.errors import MufRuntimeError
from mufsim.insts.base import Instruction, instr


@instr("date")
class InstDate(Instruction):
    def execute(self, fr):
        when = time.localtime()
        fr.data_push(int(when.tm_mday))
        fr.data_push(int(when.tm_mon))
        fr.data_push(int(when.tm_year))


@instr("time")
class InstTime(Instruction):
    def execute(self, fr):
        when = time.localtime()
        fr.data_push(int(when.tm_sec))
        fr.data_push(int(when.tm_min))
        fr.data_push(int(when.tm_hour))


@instr("gmtoffset")
class InstGmtOffset(Instruction):
    def execute(self, fr):
        fr.data_push(-time.timezone)


@instr("timesplit")
class InstTimeSplit(Instruction):
    def execute(self, fr):
        secs = fr.data_pop(int)
        when = time.localtime(secs)
        fr.data_push(int(when.tm_sec))
        fr.data_push(int(when.tm_min))
        fr.data_push(int(when.tm_hour))
        fr.data_push(int(when.tm_mday))
        fr.data_push(int(when.tm_mon))
        fr.data_push(int(when.tm_year))
        fr.data_push(int(when.tm_wday) + 1)
        fr.data_push(int(when.tm_yday))


@instr("timefmt")
class InstTimeFmt(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        when = fr.data_pop(int)
        fmt = fr.data_pop(str)
        when = time.localtime(when)
        fr.data_push(time.strftime(fmt, when))


@instr("systime")
class InstSysTime(Instruction):
    def execute(self, fr):
        fr.data_push(int(time.time()))


@instr("systime_precise")
class InstSysTimePrecise(Instruction):
    def execute(self, fr):
        fr.data_push(float(time.time()))


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
