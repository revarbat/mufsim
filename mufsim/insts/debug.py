from mufsim.logger import log
from mufsim.errors import MufBreakExecution
from mufsim.insts.base import Instruction, instr


@instr("debug_on")
class InstDebugOn(Instruction):
    def execute(self, fr):
        fr.trace = True


@instr("debug_off")
class InstDebugOff(Instruction):
    def execute(self, fr):
        fr.trace = False


@instr("debug_line")
class InstDebugLine(Instruction):
    def execute(self, fr):
        log(fr.get_trace_line(), msgtype='trace')


@instr("debugger_break")
class InstDebuggerBreak(Instruction):
    def execute(self, fr):
        raise MufBreakExecution()


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
