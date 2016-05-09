import mufsim.gamedb as db
import mufsim.stackitems as si
# from mufsim.errors import MufRuntimeError
from mufsim.insts.base import Instruction, instr


@instr("int?")
class InstIntP(Instruction):
    def execute(self, fr):
        val = fr.data_pop()
        fr.data_push(1 if isinstance(val, int) else 0)


@instr("float?")
class InstFloatP(Instruction):
    def execute(self, fr):
        val = fr.data_pop()
        fr.data_push(1 if isinstance(val, float) else 0)


@instr("number?")
class InstNumberP(Instruction):
    def execute(self, fr):
        val = fr.data_pop()
        fr.data_push(1 if type(val) in [int, float] else 0)


@instr("dbref?")
class InstDBRefP(Instruction):
    def execute(self, fr):
        val = fr.data_pop()
        fr.data_push(1 if isinstance(val, si.DBRef) else 0)


@instr("string?")
class InstStringP(Instruction):
    def execute(self, fr):
        val = fr.data_pop()
        fr.data_push(1 if isinstance(val, str) else 0)


@instr("address?")
class InstAddressP(Instruction):
    def execute(self, fr):
        val = fr.data_pop()
        fr.data_push(1 if isinstance(val, si.Address) else 0)


@instr("array?")
class InstArrayP(Instruction):
    def execute(self, fr):
        val = fr.data_pop()
        fr.data_push(1 if type(val) in [list, dict] else 0)


@instr("dictionary?")
class InstDictionaryP(Instruction):
    def execute(self, fr):
        val = fr.data_pop()
        fr.data_push(1 if isinstance(val, dict) else 0)


@instr("lock?")
class InstLockP(Instruction):
    def execute(self, fr):
        val = fr.data_pop()
        fr.data_push(1 if isinstance(val, si.Lock) else 0)


@instr("ok?")
class InstOkP(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_dbref()
        if not db.validobj(obj):
            fr.data_push(0)
        elif db.getobj(obj).objtype == "garbage":
            fr.data_push(0)
        else:
            fr.data_push(1)


@instr("player?")
class InstPlayerP(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_dbref()
        if not db.validobj(obj):
            fr.data_push(0)
        elif db.getobj(obj).objtype == "player":
            fr.data_push(1)
        else:
            fr.data_push(0)


@instr("room?")
class InstRoomP(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_dbref()
        if not db.validobj(obj):
            fr.data_push(0)
        elif db.getobj(obj).objtype == "room":
            fr.data_push(1)
        else:
            fr.data_push(0)


@instr("exit?")
class InstExitP(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_dbref()
        if not db.validobj(obj):
            fr.data_push(0)
        elif db.getobj(obj).objtype == "exit":
            fr.data_push(1)
        else:
            fr.data_push(0)


@instr("program?")
class InstProgramP(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_dbref()
        if not db.validobj(obj):
            fr.data_push(0)
        elif db.getobj(obj).objtype == "program":
            fr.data_push(1)
        else:
            fr.data_push(0)


@instr("thing?")
class InstThingP(Instruction):
    def execute(self, fr):
        obj = fr.data_pop_dbref()
        if not db.validobj(obj):
            fr.data_push(0)
        elif db.getobj(obj).objtype == "thing":
            fr.data_push(1)
        else:
            fr.data_push(0)


@instr("controls")
class InstControls(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        obj = fr.data_pop_object()
        who = fr.data_pop_object()
        if obj.owner == who.dbref:
            fr.data_push(1)
        elif "W" in who.flags:
            fr.data_push(1)
        else:
            fr.data_push(0)


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
