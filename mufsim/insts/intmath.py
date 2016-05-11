import math
import random
import mufsim.stackitems as si
from mufsim.errors import MufRuntimeError
from mufsim.insts.base import Instruction, instr


@instr("int")
class InstInt(Instruction):
    def execute(self, fr):
        val = fr.data_pop()
        if isinstance(val, si.GlobalVar):
            val = val.value
        elif isinstance(val, si.FuncVar):
            val = val.value
        elif isinstance(val, si.DBRef):
            val = val.value
        elif isinstance(val, int):
            val = val
        elif isinstance(val, float):
            if (
                math.isinf(val) or
                math.isnan(val) or
                math.fabs(val) >= math.pow(2.0, 32.0)
            ):
                fr.set_error("IBOUNDS")
                val = 0
            else:
                val = int(val)
        else:
            raise MufRuntimeError("Expected number or var argument.")
        fr.data_push(val)


@instr("+")
class InstPlus(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(int, float, si.DBRef)
        a = fr.data_pop(int, float, si.DBRef)
        makedbref = False
        if isinstance(a, si.DBRef):
            if isinstance(b, float):
                raise MufRuntimeError("Cannot add float to dbref.")
            makedbref = True
            a = a.value
        if isinstance(b, si.DBRef):
            if isinstance(a, float):
                raise MufRuntimeError("Cannot add float to dbref.")
            makedbref = True
            b = b.value
        if makedbref:
            fr.data_push(si.DBRef(a + b))
        else:
            if math.isinf(a) or math.isinf(b):
                fr.set_error("FBOUNDS")
            out = a + b
            if math.isnan(out):
                fr.set_error("NAN")
            fr.data_push(out)

    def __str__(self):
        return "+"


@instr("++")
class InstPlusPlus(Instruction):
    def execute(self, fr):
        a = fr.data_pop(int, float, si.DBRef, si.FuncVar, si.GlobalVar)
        if isinstance(a, si.FuncVar):
            val = fr.funcvar_get(a) + 1
            fr.funcvar_set(a, val)
        elif isinstance(a, si.GlobalVar):
            val = fr.globalvar_get(a) + 1
            fr.globalvar_set(a, val)
        elif isinstance(a, si.DBRef):
            fr.data_push(si.DBRef(a.value + 1))
        elif isinstance(a, int):
            fr.data_push(a + 1)
        elif isinstance(a, float):
            if math.isinf(a):
                fr.set_error("FBOUNDS")
            fr.data_push(a + 1)

    def __str__(self):
        return "++"


@instr("-")
class InstMinus(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(int, float, si.DBRef)
        a = fr.data_pop(int, float, si.DBRef)
        makedbref = False
        if isinstance(a, si.DBRef):
            if isinstance(b, float):
                raise MufRuntimeError("Cannot add float to dbref.")
            makedbref = True
            a = a.value
        if isinstance(b, si.DBRef):
            if isinstance(a, float):
                raise MufRuntimeError("Cannot add float to dbref.")
            makedbref = True
            b = b.value
        if makedbref:
            fr.data_push(si.DBRef(a - b))
        else:
            if math.isinf(a) or math.isinf(b):
                fr.set_error("FBOUNDS")
            out = a - b
            if math.isnan(out):
                fr.set_error("NAN")
            fr.data_push(out)

    def __str__(self):
        return "-"


@instr("--")
class InstMinusMinus(Instruction):
    def execute(self, fr):
        a = fr.data_pop(int, float, si.DBRef, si.FuncVar, si.GlobalVar)
        if isinstance(a, si.FuncVar):
            val = fr.funcvar_get(a) - 1
            fr.funcvar_set(a, val)
        elif isinstance(a, si.GlobalVar):
            val = fr.globalvar_get(a) - 1
            fr.globalvar_set(a, val)
        elif isinstance(a, si.DBRef):
            fr.data_push(si.DBRef(a.value + 1))
        elif isinstance(a, int):
            fr.data_push(a - 1)
        elif isinstance(a, float):
            if math.isinf(a):
                fr.set_error("FBOUNDS")
            fr.data_push(a - 1)

    def __str__(self):
        return "--"


@instr("*")
class InstTimes(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(int, float)
        a = fr.data_pop(int, float)
        if math.isinf(a) or math.isinf(b):
            fr.set_error("FBOUNDS")
        out = a * b
        if math.isnan(out):
            fr.set_error("NAN")
        fr.data_push(out)

    def __str__(self):
        return "*"


@instr("/")
class InstDivide(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(int, float)
        a = fr.data_pop(int, float)
        if math.isinf(a) or math.isinf(b):
            fr.set_error("FBOUNDS")
        out = 0
        try:
            if isinstance(a, int) and isinstance(b, int):
                out = a // b
            else:
                out = a / b
            if math.isnan(out):
                fr.set_error("NAN")
        except ZeroDivisionError:
            fr.set_error("DIV_ZERO")
        fr.data_push(out)

    def __str__(self):
        return "/"


@instr("%")
class InstModulo(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(int, float)
        a = fr.data_pop(int, float)
        if math.isinf(a) or math.isinf(b):
            fr.set_error("FBOUNDS")
        out = 0
        try:
            out = a % b
            if math.isnan(out):
                fr.set_error("NAN")
        except ZeroDivisionError:
            fr.set_error("DIV_ZERO")
        fr.data_push(out)

    def __str__(self):
        return "%"


@instr("bitshift")
class InstBitShift(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(int)
        a = fr.data_pop(int)
        if b < 0:
            fr.data_push(a >> -b)
        else:
            fr.data_push(a << b)


@instr("bitor")
class InstBitOr(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(int)
        a = fr.data_pop(int)
        fr.data_push(a | b)


@instr("bitxor")
class InstBitXor(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(int)
        a = fr.data_pop(int)
        fr.data_push(a ^ b)


@instr("bitand")
class InstBitAnd(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(int)
        a = fr.data_pop(int)
        fr.data_push(a & b)


# TODO: Figure out a way to implement GETSEED
@instr("setseed")
class InstSetSeed(Instruction):
    def execute(self, fr):
        s = fr.data_pop(str)
        random.seed(s[:32])


@instr("srand")
class InstSRand(Instruction):
    def execute(self, fr):
        fr.data_push(random.randint(-(2 ** 31 - 2), (2 ** 31 - 2)))


# TODO: Make RANDOM distinct from SRAND.
# Currently, both get seeded by the random.seed() call in SETSEED.
@instr("random")
class InstRandom(Instruction):
    def execute(self, fr):
        fr.data_push(random.randint(-(2 ** 31 - 2), (2 ** 31 - 2)))


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
