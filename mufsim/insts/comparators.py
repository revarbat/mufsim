import mufsim.stackitems as si
# from mufsim.errors import MufRuntimeError
from mufsim.insts.base import Instruction, instr


@instr("or")
class InstOr(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop()
        a = fr.data_pop()
        fr.data_push(1 if a or b else 0)


@instr("xor")
class InstXor(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop()
        a = fr.data_pop()
        fr.data_push(1 if (a and not b) or (not a and b) else 0)


@instr("and")
class InstAnd(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop()
        a = fr.data_pop()
        fr.data_push(1 if a and b else 0)


@instr("not")
class InstNot(Instruction):
    def execute(self, fr):
        a = fr.data_pop()
        if isinstance(a, si.DBRef):
            fr.data_push(1 if a.value == -1 else 0)
        else:
            fr.data_push(1 if not a else 0)


@instr("=")
class InstEquals(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(int, float, si.DBRef)
        a = fr.data_pop(int, float, si.DBRef)
        if isinstance(a, si.DBRef):
            a = a.value
        if isinstance(b, si.DBRef):
            b = b.value
        fr.data_push(1 if a == b else 0)

    def __str__(self):
        return "="


@instr("<")
class InstLessThan(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(int, float, si.DBRef)
        a = fr.data_pop(int, float, si.DBRef)
        if isinstance(a, si.DBRef):
            a = a.value
        if isinstance(b, si.DBRef):
            b = b.value
        fr.data_push(1 if a < b else 0)

    def __str__(self):
        return "<"


@instr("<=")
class InstLessThanOrEquals(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(int, float, si.DBRef)
        a = fr.data_pop(int, float, si.DBRef)
        if isinstance(a, si.DBRef):
            a = a.value
        if isinstance(b, si.DBRef):
            b = b.value
        fr.data_push(1 if a <= b else 0)

    def __str__(self):
        return "<="


@instr(">")
class InstGreaterThan(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(int, float, si.DBRef)
        a = fr.data_pop(int, float, si.DBRef)
        if isinstance(a, si.DBRef):
            a = a.value
        if isinstance(b, si.DBRef):
            b = b.value
        fr.data_push(1 if a > b else 0)

    def __str__(self):
        return ">"


@instr(">=")
class InstGreaterThanOrEquals(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(int, float, si.DBRef)
        a = fr.data_pop(int, float, si.DBRef)
        if isinstance(a, si.DBRef):
            a = a.value
        if isinstance(b, si.DBRef):
            b = b.value
        fr.data_push(1 if a >= b else 0)

    def __str__(self):
        return ">="


@instr("dbcmp")
class InstDBCmp(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop_dbref()
        a = fr.data_pop_dbref()
        fr.data_push(1 if a.value == b.value else 0)


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
