import sys

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
        print(fr.get_trace_line())
        sys.stdout.flush()


@instr("debugger_break")
class InstDebuggerBreak(Instruction):
    def execute(self, fr):
        raise MufBreakExecution()


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
