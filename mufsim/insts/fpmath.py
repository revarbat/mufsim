import sys
import math
import random
from mufsim.errors import MufRuntimeError
from mufsim.insts.base import Instruction, instr


@instr("abs")
class InstAbs(Instruction):
    def execute(self, fr):
        a = fr.data_pop(int)
        fr.data_push(abs(a))


@instr("sign")
class InstSign(Instruction):
    def execute(self, fr):
        a = fr.data_pop(int)
        fr.data_push((a > 0) - (a < 0))


@instr("float")
class InstFloat(Instruction):
    def execute(self, fr):
        i = fr.data_pop(int)
        fr.data_push(float(i))


@instr("pi")
class InstPi(Instruction):
    def execute(self, fr):
        fr.data_push(math.pi)


@instr("inf")
class InstInf(Instruction):
    def execute(self, fr):
        fr.data_push(float("Inf"))


@instr("epsilon")
class InstEpsilon(Instruction):
    def execute(self, fr):
        fr.data_push(sys.float_info.epsilon)


@instr("ftostr")
class InstFToStr(Instruction):
    def execute(self, fr):
        x = fr.data_pop(int, float)
        a = "%.11e" % x
        b = "%.11f" % x
        x = a if len(a) < len(b) else b
        if "e" in x:
            fpval, mant = x.split("e", 1)
            if "." in fpval:
                fpval = fpval.rstrip("0")
            x = fpval + "e" + mant
        fr.data_push(x)


@instr("ftostrc")
class InstFToStrC(Instruction):
    def execute(self, fr):
        x = fr.data_pop(int, float)
        fr.data_push("%.12g" % x)


@instr("strtof")
class InstStrToF(Instruction):
    def execute(self, fr):
        x = fr.data_pop(str)
        try:
            x = float(x)
        except:
            x = 0.0
        fr.data_push(x)


@instr("fabs")
class InstFabs(Instruction):
    def execute(self, fr):
        x = float(fr.data_pop(int, float))
        if x < 0.0:
            fr.data_push(-x)
        else:
            fr.data_push(x)


@instr("ceil")
class InstCeil(Instruction):
    def execute(self, fr):
        x = fr.data_pop(float)
        fr.data_push(float(math.ceil(x)))


@instr("floor")
class InstFloor(Instruction):
    def execute(self, fr):
        x = fr.data_pop(float)
        fr.data_push(float(math.floor(x)))


@instr("round")
class InstRound(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(int)
        a = fr.data_pop(float)
        fr.data_push(round(a, b))


@instr("fmod")
class InstFMod(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(float)
        a = fr.data_pop(float)
        fr.data_push(math.fmod(a, b))


@instr("modf")
class InstModF(Instruction):
    def execute(self, fr):
        a = fr.data_pop(float)
        if a < 0.0:
            fr.data_push(float(math.ceil(a)))
            fr.data_push(a - math.ceil(a))
        else:
            fr.data_push(float(math.floor(a)))
            fr.data_push(a - math.floor(a))


@instr("sqrt")
class InstSqrt(Instruction):
    def execute(self, fr):
        x = fr.data_pop(float)
        if x < 0:
            fr.set_error("IMAGINARY")
            x = 0
        else:
            if math.isinf(x):
                fr.set_error("FBOUNDS")
            x = math.sqrt(x)
            if math.isnan(x):
                fr.set_error("NAN")
        fr.data_push(x)


@instr("sin")
class InstSin(Instruction):
    def execute(self, fr):
        x = fr.data_pop(float)
        if math.isinf(x) or math.isnan(x):
            fr.set_error("FBOUNDS")
            x = 0.0
        else:
            x = math.sin(x)
        fr.data_push(x)


@instr("cos")
class InstCos(Instruction):
    def execute(self, fr):
        x = fr.data_pop(float)
        if math.isinf(x) or math.isnan(x):
            fr.set_error("FBOUNDS")
            x = 0.0
        else:
            x = math.cos(x)
        fr.data_push(x)


@instr("tan")
class InstTan(Instruction):
    def execute(self, fr):
        x = fr.data_pop(float)
        if math.isinf(x) or math.isnan(x):
            fr.set_error("FBOUNDS")
            x = 0.0
        else:
            x = math.tan(x)
        fr.data_push(x)


@instr("asin")
class InstASin(Instruction):
    def execute(self, fr):
        x = fr.data_pop(float)
        if x < -1.0 or x > 1.0:
            fr.set_error("FBOUNDS")
            x = 0.0
        else:
            x = math.asin(x)
        fr.data_push(x)


@instr("acos")
class InstACos(Instruction):
    def execute(self, fr):
        x = fr.data_pop(float)
        if x < -1.0 or x > 1.0:
            fr.set_error("FBOUNDS")
            x = 0.0
        else:
            x = math.acos(x)
        fr.data_push(x)


@instr("atan")
class InstATan(Instruction):
    def execute(self, fr):
        x = fr.data_pop(float)
        try:
            x = math.atan(x)
        except:
            fr.set_error("FBOUNDS")
            x = 0.0
        fr.data_push(x)


@instr("atan2")
class InstATan2(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        x = fr.data_pop(float)
        y = fr.data_pop(float)
        try:
            out = math.atan2(y, x)
        except:
            raise MufRuntimeError("Math domain error.")
        fr.data_push(out)


@instr("pow")
class InstPow(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        y = fr.data_pop(float)
        x = fr.data_pop(float)
        try:
            x = x ** y
        except:
            fr.set_error("FBOUNDS")
            x = 0.0
        fr.data_push(x)


@instr("exp")
class InstExp(Instruction):
    def execute(self, fr):
        x = fr.data_pop(float)
        try:
            x = math.exp(x)
        except:
            fr.set_error("FBOUNDS")
            x = 0.0
        fr.data_push(x)


@instr("log")
class InstLog(Instruction):
    def execute(self, fr):
        x = fr.data_pop(float)
        try:
            x = math.log(x)
        except:
            fr.set_error("FBOUNDS")
            x = 0.0
        fr.data_push(x)


@instr("log10")
class InstLog10(Instruction):
    def execute(self, fr):
        x = fr.data_pop(float)
        try:
            x = math.log10(x)
        except:
            fr.set_error("FBOUNDS")
            x = 0.0
        fr.data_push(x)


@instr("diff3")
class InstDiff3(Instruction):
    def execute(self, fr):
        fr.check_underflow(6)
        z2 = fr.data_pop(float)
        y2 = fr.data_pop(float)
        x2 = fr.data_pop(float)
        z1 = fr.data_pop(float)
        y1 = fr.data_pop(float)
        x1 = fr.data_pop(float)
        if math.isinf(x1) or math.isinf(y1) or math.isinf(z1):
            fr.set_error("FBOUNDS")
        if math.isinf(x2) or math.isinf(y2) or math.isinf(z2):
            fr.set_error("FBOUNDS")
        fr.data_push(x1 - x2)
        fr.data_push(y1 - y2)
        fr.data_push(z1 - z2)


@instr("dist3d")
class InstDist3D(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        z = fr.data_pop(float)
        y = fr.data_pop(float)
        x = fr.data_pop(float)
        if math.isinf(x) or math.isinf(y) or math.isinf(z):
            fr.set_error("FBOUNDS")
        fr.data_push(math.sqrt(x * x + y * y + z * z))


@instr("xyz_to_polar")
class InstXyzToPolar(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        z = fr.data_pop(float)
        y = fr.data_pop(float)
        x = fr.data_pop(float)
        if math.isinf(x) or math.isinf(y) or math.isinf(z):
            fr.set_error("FBOUNDS")
        xy = math.sqrt(x * x + y * y)
        t = math.atan2(y, x)
        p = math.atan2(z, xy)
        r = math.sqrt(x * x + y * y + z * z)
        fr.data_push(r)
        fr.data_push(t)
        fr.data_push(p)


@instr("polar_to_xyz")
class InstPolarToXyz(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        p = fr.data_pop(float)
        t = fr.data_pop(float)
        r = fr.data_pop(float)
        if math.isinf(r) or math.isinf(p) or math.isinf(t):
            fr.set_error("FBOUNDS")
        x = r * math.cos(p) * math.cos(t)
        y = r * math.cos(p) * math.sin(t)
        z = r * math.sin(p)
        fr.data_push(x)
        fr.data_push(y)
        fr.data_push(z)


@instr("frand")
class InstFRand(Instruction):
    def execute(self, fr):
        fr.data_push(random.random())


@instr("gaussian")
class InstGaussian(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        m = fr.data_pop(float)
        s = fr.data_pop(float)
        if math.isinf(s) or math.isinf(m):
            fr.set_error("FBOUNDS")
        try:
            fr.data_push(random.gauss(m, s))
        except:
            fr.data_push(m)


@instr("clear")
class InstClear(Instruction):
    def execute(self, fr):
        fr.clear_errors()


@instr("clear_error")
class InstClearError(Instruction):
    def execute(self, fr):
        x = fr.data_pop(int, str)
        if isinstance(x, int):
            x = fr.fp_error_names[x]
        fr.clear_error(x)


@instr("error?")
class InstErrorP(Instruction):
    def execute(self, fr):
        fr.data_push(1 if fr.has_errors() else 0)


@instr("error_bit")
class InstErrorBit(Instruction):
    def execute(self, fr):
        errname = fr.data_pop(str)
        errnum = -1
        if errname in fr.fp_error_names:
            errnum = fr.fp_error_names.index(errname)
        fr.data_push(errnum)


@instr("error_name")
class InstErrorName(Instruction):
    def execute(self, fr):
        errnum = fr.data_pop(int)
        try:
            fr.data_push(fr.fp_error_names[errnum])
        except:
            fr.data_push("")


@instr("error_num")
class InstErrorNum(Instruction):
    def execute(self, fr):
        fr.data_push(len(fr.fp_error_names))


@instr("error_str")
class InstErrorStr(Instruction):
    def execute(self, fr):
        x = fr.data_pop(int, str)
        if isinstance(x, str):
            if x in fr.fp_error_names:
                x = fr.fp_error_names.index(x)
            else:
                x = -1
        if x >= 0:
            try:
                x = fr.fp_error_descrs[x]
            except:
                x = ""
        else:
            x = ""
        fr.data_push(x)


@instr("is_set?")
class InstIsSetP(Instruction):
    def execute(self, fr):
        x = fr.data_pop(int, str)
        if isinstance(x, int):
            x = fr.fp_error_names[x]
        fr.data_push(1 if fr.has_error(x) else 0)


@instr("set_error")
class InstSetError(Instruction):
    def execute(self, fr):
        x = fr.data_pop(int, str)
        if isinstance(x, int):
            x = fr.fp_error_names[x]
        fr.set_error(x)


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
