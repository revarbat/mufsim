import mufsim.stackitems as si
from mufsim.errors import MufRuntimeError
from mufsim.insts.base import Instruction, instr


class InstPushItem(Instruction):
    value = 0

    def __init__(self, line, val):
        self.value = val
        super(InstPushItem, self).__init__(line)

    def execute(self, fr):
        fr.data_push(self.value)

    def __str__(self):
        return si.item_repr(self.value)


class InstGlobalVar(Instruction):
    varnum = 0
    varname = 0

    def __init__(self, line, vnum, vname):
        self.varnum = vnum
        self.varname = vname
        super(InstGlobalVar, self).__init__(line)

    def execute(self, fr):
        fr.data_push(si.GlobalVar(self.varnum))

    def __str__(self):
        return "LV%d: %s" % (self.varnum, self.varname)


class InstFuncVar(Instruction):
    varnum = 0
    varname = 0

    def __init__(self, line, vnum, vname):
        self.varnum = vnum
        self.varname = vname
        super(InstFuncVar, self).__init__(line)

    def execute(self, fr):
        fr.data_push(si.FuncVar(self.varnum))

    def __str__(self):
        return "SV%d: %s" % (self.varnum, self.varname)


@instr("!")
class InstBang(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        v = fr.data_pop(si.GlobalVar, si.FuncVar)
        val = fr.data_pop()
        if type(v) is si.GlobalVar:
            fr.globalvar_set(v.value, val)
        elif type(v) is si.FuncVar:
            fr.funcvar_set(v.value, val)

    def __str__(self):
        return "!"


@instr("@")
class InstAt(Instruction):
    def execute(self, fr):
        v = fr.data_pop(si.GlobalVar, si.FuncVar)
        if type(v) is si.GlobalVar:
            val = fr.globalvar_get(v.value)
            fr.data_push(val)
        elif type(v) is si.FuncVar:
            val = fr.funcvar_get(v.value)
            fr.data_push(val)

    def __str__(self):
        return "@"


@instr("dup")
class InstDup(Instruction):
    def execute(self, fr):
        a = fr.data_pop()
        fr.data_push(a)
        fr.data_push(a)


@instr("dupn")
class InstDupN(Instruction):
    def execute(self, fr):
        n = fr.data_pop(int)
        fr.check_underflow(n)
        for i in xrange(n):
            fr.data_push(fr.data_pick(n))


@instr("ldup")
class InstLDup(Instruction):
    def execute(self, fr):
        n = fr.data_pick(1)
        if type(n) is not int:
            raise MufRuntimeError("Expected integer argument.")
        n += 1
        fr.check_underflow(n)
        for i in xrange(n):
            fr.data_push(fr.data_pick(n))


@instr("pop")
class InstPop(Instruction):
    def execute(self, fr):
        fr.data_pop()


@instr("popn")
class InstPopN(Instruction):
    def execute(self, fr):
        n = fr.data_pop(int)
        fr.check_underflow(n)
        for i in xrange(n):
            fr.data_pop()


@instr("swap")
class InstSwap(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop()
        a = fr.data_pop()
        fr.data_push(b)
        fr.data_push(a)


@instr("rot")
class InstRot(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        a = fr.data_pull(3)
        fr.data_push(a)


@instr("rotate")
class InstRotate(Instruction):
    def execute(self, fr):
        num = fr.data_pop(int)
        fr.check_underflow(num)
        if not num:
            return
        if num < 0:
            a = fr.data_pop()
            fr.data_insert((-num) - 1, a)
        else:
            a = fr.data_pull(num)
            fr.data_push(a)


@instr("pick")
class InstPick(Instruction):
    def execute(self, fr):
        num = fr.data_pop(int)
        fr.check_underflow(num)
        if not num:
            return
        if num < 0:
            raise MufRuntimeError("Expected positive integer.")
        else:
            a = fr.data_pick(num)
            fr.data_push(a)


@instr("over")
class InstOver(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        a = fr.data_pick(2)
        fr.data_push(a)


@instr("put")
class InstPut(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        num = fr.data_pop(int)
        val = fr.data_pop()
        fr.check_underflow(num)
        if not num:
            return
        if num < 0:
            raise MufRuntimeError("Value out of range")
        else:
            fr.data_put(num, val)


@instr("reverse")
class InstReverse(Instruction):
    def execute(self, fr):
        num = fr.data_pop(int)
        fr.check_underflow(num)
        if not num:
            return
        arr = [fr.data_pop() for i in xrange(num)]
        for val in arr:
            fr.data_push(val)


@instr("lreverse")
class InstLReverse(Instruction):
    def execute(self, fr):
        num = fr.data_pop(int)
        fr.check_underflow(num)
        if not num:
            return
        arr = [fr.data_pop() for i in xrange(num)]
        for val in arr:
            fr.data_push(val)
        fr.data_push(num)


@instr("{")
class InstMark(Instruction):
    def execute(self, fr):
        fr.data_push(si.Mark())


@instr("}")
class InstMarkCount(Instruction):
    def execute(self, fr):
        for i in xrange(fr.data_depth()):
            a = fr.data_pick(i + 1)
            if type(a) is si.Mark:
                fr.data_pull(i + 1)
                fr.data_push(i)
                return
        raise MufRuntimeError("StackUnderflow")


@instr("depth")
class InstDepth(Instruction):
    def execute(self, fr):
        fr.data_push(fr.data_depth())


@instr("fulldepth")
class InstFullDepth(Instruction):
    def execute(self, fr):
        fr.data_push(fr.data_depth())


@instr("variable")
class InstVariable(Instruction):
    def execute(self, fr):
        vnum = fr.data_pop(int)
        fr.data_push(si.GlobalVar(vnum))


@instr("localvar")
class InstLocalVar(Instruction):
    def execute(self, fr):
        vnum = fr.data_pop(int)
        fr.data_push(si.GlobalVar(vnum))


@instr("caller")
class InstCaller(Instruction):
    def execute(self, fr):
        fr.data_push(fr.caller_get())


@instr("prog")
class InstProg(Instruction):
    def execute(self, fr):
        fr.data_push(fr.program)


@instr("trig")
class InstTrig(Instruction):
    def execute(self, fr):
        fr.data_push(fr.trigger)


@instr("cmd")
class InstCmd(Instruction):
    def execute(self, fr):
        fr.data_push(fr.command)


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
