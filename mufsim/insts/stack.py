import mufsim.utils as util
import mufsim.gamedb as db
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
        if isinstance(v, si.GlobalVar):
            fr.globalvar_set(v.value, val)
        elif isinstance(v, si.FuncVar):
            fr.funcvar_set(v.value, val)

    def __str__(self):
        return "!"


@instr("@")
class InstAt(Instruction):
    def execute(self, fr):
        v = fr.data_pop(si.GlobalVar, si.FuncVar)
        if isinstance(v, si.GlobalVar):
            val = fr.globalvar_get(v.value)
            fr.data_push(val)
        elif isinstance(v, si.FuncVar):
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
        for i in range(n):
            fr.data_push(fr.data_pick(n))


@instr("ldup")
class InstLDup(Instruction):
    def execute(self, fr):
        n = fr.data_pick(1)
        if not isinstance(n, int):
            raise MufRuntimeError("Expected integer argument.")
        n += 1
        fr.check_underflow(n)
        for i in range(n):
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
        for i in range(n):
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
        elif num > 0:
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
        arr = [fr.data_pop() for i in range(num)]
        for val in arr:
            fr.data_push(val)


@instr("lreverse")
class InstLReverse(Instruction):
    def execute(self, fr):
        num = fr.data_pop(int)
        fr.check_underflow(num)
        if not num:
            return
        arr = [fr.data_pop() for i in range(num)]
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
        for i in range(fr.data_depth()):
            a = fr.data_pick(i + 1)
            if isinstance(a, si.Mark):
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


@instr("checkargs")
class InstCheckArgs(Instruction):
    itemtypes = {
        'a': ([si.Address], "address"),
        'd': ([si.DBRef], "dbref"),
        'D': ([si.DBRef], "valid object dbref"),
        'e': ([si.DBRef], "exit dbref"),
        'E': ([si.DBRef], "valid exit dbref"),
        'f': ([si.DBRef], "program dbref"),
        'F': ([si.DBRef], "valid program dbref"),
        'i': ([int], "integer"),
        'l': ([si.Lock], "lock"),
        'p': ([si.DBRef], "player dbref"),
        'P': ([si.DBRef], "valid player dbref"),
        'r': ([si.DBRef], "room dbref"),
        'R': ([si.DBRef], "valid room dbref"),
        's': ([str], "string"),
        'S': ([str], "non-null string"),
        't': ([si.DBRef], "thing dbref"),
        'T': ([si.DBRef], "valid thing dbref"),
        'v': ([si.GlobalVar, si.FuncVar], "variable"),
        '?': ([], "any"),
    }
    objtypes = {
        'D': "",
        'P': "player",
        'R': "room",
        'T': "thing",
        'E': "exit",
        'F': "program",
    }

    def checkargs_part(self, fr, fmt, depth=1):
        count = ""
        pos = len(fmt) - 1
        while pos >= 0:
            ch = fmt[pos]
            pos -= 1
            if ch == " ":
                continue
            elif util.is_int(ch):
                count = ch + count
                continue
            elif ch == "}":
                newpos = pos
                cnt = 1 if not count else int(count)
                for i in range(cnt):
                    val = fr.data_pick(depth)
                    depth += 1
                    fr.check_type(val, [int])
                    for j in range(val):
                        newpos, depth = self.checkargs_part(
                            fr, fmt[:pos + 1], depth)
                pos = newpos
                count = ""
            elif ch == "{":
                return (pos, depth)
            elif ch in self.itemtypes:
                cnt = 1 if not count else int(count)
                count = ""
                for i in range(cnt):
                    val = fr.data_pick(depth)
                    depth += 1
                    types, label = self.itemtypes[ch]
                    fr.check_type(val, types)
                    if ch == "S" and val == "":
                        raise MufRuntimeError(
                            "Expected %s at depth %d" % (label, depth))
                    if si.DBRef in types:
                        typ = self.objtypes[ch.upper()]
                        if (
                            not db.validobj(val) and
                            ch.isupper()
                        ) or (
                            db.validobj(val) and typ and
                            db.getobj(val).objtype != typ
                        ):
                            raise MufRuntimeError(
                                "Expected %s at depth %d" % (label, depth))

    def execute(self, fr):
        argexp = fr.data_pop(str)
        self.checkargs_part(fr, argexp)


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
