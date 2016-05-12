import time
import mufsim.gamedb as db
import mufsim.stackitems as si
from mufsim.logger import log
from mufsim.errors import MufCompileError, MufRuntimeError
from mufsim.insts.stack import InstFuncVar, InstBang
from mufsim.insts.base import Instruction, instr


@instr("jmp")
class InstJmp(Instruction):
    value = 0

    def __init__(self, line, val=0):
        self.value = val
        super(InstJmp, self).__init__(line)

    def execute(self, fr):
        addr = fr.curr_addr()
        addr = si.Address(self.value - 1, addr.prog)
        fr.pc_set(addr)

    def __str__(self):
        return "JMP: %d" % self.value


class InstJmpIfFalse(Instruction):
    value = 0

    def __init__(self, line, val):
        self.value = val
        super(InstJmpIfFalse, self).__init__(line)

    def execute(self, fr):
        val = fr.data_pop()
        if not val:
            addr = fr.curr_addr()
            addr = si.Address(self.value - 1, addr.prog)
            fr.pc_set(addr)

    def __str__(self):
        return "JmpIfFalse: %d" % self.value


@instr(":")
class InstFunc(Instruction):
    funcname = "Unknown"
    varcount = 0

    def __init__(self, line, funcname=None, varcount=0):
        self.funcname = funcname
        self.varcount = varcount
        super(InstFunc, self).__init__(line)

    def execute(self, fr):
        fr.check_underflow(self.varcount)
        for i in reversed(list(range(self.varcount))):
            fr.funcvar_set(i, fr.data_pop())

    def get_header_vars(self, cmplr, src):
        funcvars = []
        while True:
            v, src = cmplr.get_word(src)
            if v == ']':
                break
            if v == '--':
                if ']' not in src:
                    raise MufCompileError("Function header incomplete.")
                src = src.split(']', 1)[1]
                src = cmplr.lstrip(src)
                break
            if v in funcvars:
                raise MufCompileError("Variable already declared.")
            funcvars.append(v)
            if not src:
                raise MufCompileError("Function header incomplete.")
        return (funcvars, src)

    def compile(self, cmplr, code, src):
        if cmplr.funcname:
            raise MufCompileError(
                "Function definition incomplete: %s" % cmplr.funcname)
        funcname, src = cmplr.get_word(src)
        comp = cmplr.compiled
        funcvars = []
        if funcname[-1] == '[':
            funcname = funcname[:-1]
            funcvars, src = self.get_header_vars(cmplr, src)
        if comp.get_function_addr(funcname) is not None:
            raise MufCompileError("Function already declared: %s" % funcname)
        comp.add_function(funcname, len(code))
        for v in funcvars:
            comp.add_func_var(funcname, v)
        cmplr.funcname = funcname
        code.append(InstFunc(cmplr.word_line, funcname, len(funcvars)))
        fcode, src = cmplr.compile_r(src)
        for inst in fcode:
            code.append(inst)
        cmplr.stmt_stack = []
        return (False, src)

    def __str__(self):
        return "Function: %s (%d vars)" % (self.funcname, self.varcount)


@instr(";")
class InstEndFunc(Instruction):
    def compile(self, cmplr, code, src):
        code.append(InstExit(self.line))
        cmplr.funcname = None
        cmplr.check_for_incomplete_block()
        return (True, src)


@instr("public")
class InstPublic(Instruction):
    def compile(self, cmplr, code, src):
        nam, src = cmplr.get_word(src)
        comp = cmplr.compiled
        if not comp.publicize_function(nam):
            raise MufCompileError("Unrecognized identifier: %s" % nam)
        log("EXPOSED '%s' AS PUBLIC" % nam)
        return (False, src)


@instr("wizcall")
class InstWizCall(Instruction):
    def compile(self, cmplr, code, src):
        # TODO: Check wizbit on call!
        nam, src = cmplr.get_word(src)
        comp = cmplr.compiled
        if not comp.publicize_function(nam):
            raise MufCompileError("Unrecognized identifier: %s" % nam)
        log("EXPOSED '%s' AS WIZCALL" % nam)
        return (False, src)


@instr("execute")
class InstExecute(Instruction):
    def execute(self, fr):
        addr = fr.data_pop_address()
        fr.call_push(addr, fr.caller_get())
        fr.pc_advance(-1)


@instr("call")
class InstCall(Instruction):
    def execute(self, fr):
        saddr = fr.curr_addr()
        x = fr.data_pop(si.DBRef, str)
        if isinstance(x, str):
            pub = x
            obj = fr.data_pop_dbref()
        else:
            pub = None
            obj = x
        obj = db.getobj(obj)
        if obj.objtype != "program":
            raise MufRuntimeError("Expected program object!")
        if pub:
            if pub not in obj.compiled.publics:
                raise MufRuntimeError("Unrecognized public call.")
            addr = obj.compiled.publics[pub]
        else:
            addr = obj.compiled.lastfunction
        fr.call_push(addr, saddr.prog)
        fr.pc_advance(-1)


@instr("cancall?")
class InstCanCallP(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        pub = fr.data_pop(str)
        obj = fr.data_pop_object()
        if obj.compiled and obj.compiled.publics:
            if pub in obj.compiled.publics:
                fr.data_push(1)
                return
        fr.data_push(0)


@instr("exit")
class InstExit(Instruction):
    def execute(self, fr):
        fr.call_pop()


@instr("try")
class InstTry(Instruction):
    def __init__(self, line):
        self.value = 0
        self.trycode = []
        self.detailed = False
        super(InstTry, self).__init__(line)

    def execute(self, fr):
        cnt = fr.data_pop(int)
        stacklock = fr.data_depth() - cnt
        addr = fr.curr_addr()
        addr = si.Address(self.value, addr.prog)
        fr.catch_push(self.detailed, addr, stacklock)

    def compile(self, cmplr, code, src):
        inst = InstTry(self.line)
        cmplr.stmt_stack.append(inst)
        subcode, src = cmplr.compile_r(src)
        inst = cmplr.stmt_stack.pop()
        trycode = inst.trycode
        if not trycode:
            raise MufCompileError("Incomplete try-catch block.")
        inst.trycode = None
        inst.value = len(trycode) + 1
        code.append(inst)
        for prim in trycode:
            code.append(prim)
        for prim in subcode:
            code.append(prim)
        return (False, src)

    def __str__(self):
        return "Try: %d" % self.value


class InstTryPop(Instruction):
    def execute(self, fr):
        fr.catch_pop()


@instr("catch")
class InstCatch(Instruction):
    def compile(self, cmplr, code, src):
        if not cmplr.stmt_stack:
            raise MufCompileError("Must be inside try block. (catch)")
        inst = cmplr.stmt_stack[-1]
        if not isinstance(inst, InstTry):
            raise MufCompileError("Must be inside try block. (catch)")
        inst.trycode = code[:]
        inst.detailed = False
        del code[:]
        return (False, src)


@instr("catch_detailed")
class InstCatchDetailed(Instruction):
    def compile(self, cmplr, code, src):
        if not cmplr.stmt_stack:
            raise MufCompileError("Must be inside try block. (catch_detailed)")
        inst = cmplr.stmt_stack[-1]
        if not isinstance(inst, InstTry):
            raise MufCompileError("Must be inside try block. (catch_detailed)")
        inst.trycode = code[:]
        inst.detailed = True
        del code[:]
        return (False, src)


@instr("endcatch")
class InstEndCatch(Instruction):
    def compile(self, cmplr, code, src):
        if not cmplr.stmt_stack:
            raise MufCompileError("Must be inside try block. (endcatch)")
        inst = cmplr.stmt_stack[-1]
        if not isinstance(inst, InstTry):
            raise MufCompileError("Must be inside try block. (endcatch)")
        if not inst.trycode:
            raise MufCompileError("Incomplete try-catch block.")
        lastline = inst.trycode[-1].line
        inst.trycode.append(InstTryPop(lastline))
        inst.trycode.append(InstJmp(lastline, len(code) + 1))
        return (True, src)


@instr("abort")
class InstAbort(Instruction):
    def execute(self, fr):
        msg = fr.data_pop(str)
        raise MufRuntimeError(msg)


@instr("if")
class InstIf(Instruction):
    def compile(self, cmplr, code, src):
        inst = InstIf(self.line)
        cmplr.stmt_stack.append(inst)
        subcode, src = cmplr.compile_r(src)
        cmplr.stmt_stack.pop()
        bodylen = len(subcode)
        brinst = InstJmpIfFalse(self.line, len(subcode)+1)
        code.append(brinst)
        for instnum, inst in enumerate(subcode):
            if isinstance(inst, InstElse):
                inst = InstJmp(inst.line, bodylen - instnum)
                brinst.value = instnum + 2
            code.append(inst)
        return (False, src)


@instr("else")
class InstElse(Instruction):
    def compile(self, cmplr, code, src):
        if not cmplr.stmt_stack:
            raise MufCompileError("ELSE must be inside if block.")
        inst = cmplr.stmt_stack[-1]
        if not isinstance(inst, InstIf):
            raise MufCompileError("ELSE must be inside if block.")
        code.append(InstElse(self.line))
        return (False, src)


@instr("then")
class InstThen(Instruction):
    def compile(self, cmplr, code, src):
        if not cmplr.stmt_stack:
            raise MufCompileError("THEN must end an if block.")
        inst = cmplr.stmt_stack[-1]
        if not isinstance(inst, InstIf):
            raise MufCompileError("THEN must end an if block.")
        return (True, src)


@instr("begin")
class InstBegin(Instruction):
    def compile(self, cmplr, code, src):
        inst = InstBegin(self.line)
        cmplr.stmt_stack.append(inst)
        subcode, src = cmplr.compile_r(src)
        cmplr.stmt_stack.pop()
        bodylen = len(subcode)
        for instnum, inst in enumerate(subcode):
            if isinstance(inst, InstWhile):
                inst = InstJmpIfFalse(inst.line, bodylen - instnum)
            elif isinstance(inst, InstBreak):
                inst = InstJmp(inst.line, bodylen - instnum)
            elif isinstance(inst, InstContinue):
                inst = InstJmp(inst.line, -instnum)
            code.append(inst)
        return (False, src)


@instr("for")
class InstFor(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        inc = fr.data_pop(int)
        end = fr.data_pop(int)
        start = fr.data_pop(int)
        fr.loop_iter_push("for", iter(range(start, end + inc, inc)))

    def compile(self, cmplr, code, src):
        inst = InstFor(self.line)
        code.append(inst)
        cmplr.stmt_stack.append(inst)
        src = "__foriter__ while " + src
        subcode, src = cmplr.compile_r(src)
        cmplr.stmt_stack.pop()
        bodylen = len(subcode)
        for instnum, inst in enumerate(subcode):
            if isinstance(inst, InstWhile):
                inst = InstJmpIfFalse(inst.line, bodylen - instnum)
            elif isinstance(inst, InstBreak):
                inst = InstJmp(inst.line, bodylen - instnum)
            elif isinstance(inst, InstContinue):
                inst = InstJmp(inst.line, -instnum)
            code.append(inst)
        code.append(InstForPop(inst.line))
        return (False, src)


@instr("foreach")
class InstForeach(Instruction):
    def execute(self, fr):
        arr = fr.data_pop(list, dict)
        if isinstance(arr, list):
            arr = {k: v for k, v in enumerate(arr)}
        fr.loop_iter_push("foreach", iter(arr.items()))

    def compile(self, cmplr, code, src):
        inst = InstForeach(self.line)
        code.append(inst)
        cmplr.stmt_stack.append(inst)
        src = "__foriter__ while " + src
        subcode, src = cmplr.compile_r(src)
        cmplr.stmt_stack.pop()
        bodylen = len(subcode)
        for instnum, inst in enumerate(subcode):
            if isinstance(inst, InstWhile):
                inst = InstJmpIfFalse(inst.line, bodylen - instnum)
            elif isinstance(inst, InstBreak):
                inst = InstJmp(inst.line, bodylen - instnum)
            elif isinstance(inst, InstContinue):
                inst = InstJmp(inst.line, -instnum)
            code.append(inst)
        code.append(InstForPop(inst.line))
        return (False, src)


@instr("__foriter__")
class InstForIter(Instruction):
    def execute(self, fr):
        typ, topiter = fr.loop_iter_top()
        try:
            if typ == "for":
                v = next(topiter)
                fr.data_push(v)
                fr.data_push(1)
            elif typ == "foreach":
                k, v = next(topiter)
                fr.data_push(k)
                fr.data_push(v)
                fr.data_push(1)
            else:
                fr.data_push(1)
        except StopIteration:
            fr.data_push(0)


@instr(" __forpop__")
class InstForPop(Instruction):
    def execute(self, fr):
        fr.loop_iter_pop()


@instr("while")
class InstWhile(Instruction):
    def compile(self, cmplr, code, src):
        loopinst = cmplr.in_loop_inst()
        if not loopinst:
            raise MufCompileError("WHILE must be inside loop.")
        code.append(InstWhile(self.line))
        return (False, src)


@instr("break")
class InstBreak(Instruction):
    def compile(self, cmplr, code, src):
        loopinst = cmplr.in_loop_inst()
        if not loopinst:
            raise MufCompileError("BREAK must be inside loop.")
        code.append(InstBreak(self.line))
        return (False, src)


@instr("continue")
class InstContinue(Instruction):
    def compile(self, cmplr, code, src):
        loopinst = cmplr.in_loop_inst()
        if not loopinst:
            raise MufCompileError("CONTINUE must be inside loop.")
        code.append(InstContinue(self.line))
        return (False, src)


@instr("repeat")
class InstRepeat(Instruction):
    def compile(self, cmplr, code, src):
        loopinst = cmplr.in_loop_inst()
        if not loopinst:
            raise MufCompileError("REPEAT must end a loop.")
        if isinstance(cmplr.stmt_stack[-1], InstIf):
            raise MufCompileError("REPEAT must end a loop.")
        code.append(InstJmp(self.line, -len(code)))
        return (True, src)


@instr("until")
class InstUntil(Instruction):
    def compile(self, cmplr, code, src):
        loopinst = cmplr.in_loop_inst()
        if not loopinst:
            raise MufCompileError("UNTIL must end a loop.")
        if isinstance(cmplr.stmt_stack[-1], InstIf):
            raise MufCompileError("UNTIL must end a loop.")
        code.append(InstJmpIfFalse(self.line, -len(code)))
        return (True, src)


@instr("lvar")
class InstLVar(Instruction):
    def compile(self, cmplr, code, src):
        vname, src = cmplr.get_word(src)
        comp = cmplr.compiled
        if not vname:
            raise MufCompileError("Variable declaration incomplete.")
        if comp.get_global_var(vname):
            raise MufCompileError("Variable already declared.")
        comp.add_global_var(vname)
        return (False, src)


@instr("var")
class InstVar(Instruction):
    def compile(self, cmplr, code, src):
        vname, src = cmplr.get_word(src)
        comp = cmplr.compiled
        if not vname:
            raise MufCompileError("Variable declaration incomplete.")
        if cmplr.funcname:
            # Function scoped var
            if comp.get_func_var(cmplr.funcname, vname):
                raise MufCompileError("Variable already declared.")
            comp.add_func_var(cmplr.funcname, vname)
        else:
            # Global vars
            if comp.get_global_var(vname):
                raise MufCompileError("Variable already declared.")
            comp.add_global_var(vname)
        return (False, src)


@instr("var!")
class InstVarBang(Instruction):
    def compile(self, cmplr, code, src):
        vname, src = cmplr.get_word(src)
        comp = cmplr.compiled
        if not vname:
            raise MufCompileError("Variable declaration incomplete.")
        if comp.get_func_var(cmplr.funcname, vname):
            raise MufCompileError("Variable already declared.")
        vnum = comp.add_func_var(cmplr.funcname, vname)
        code.append(InstFuncVar(cmplr.word_line, vnum, vname))
        code.append(InstBang(cmplr.word_line))
        return (False, src)


@instr("mode")
class InstMode(Instruction):
    def execute(self, fr):
        fr.data_push(fr.execution_mode)


@instr("setmode")
class InstSetMode(Instruction):
    def execute(self, fr):
        mod = fr.data_pop(int)
        fr.execution_mode = mod


@instr("sleep")
class InstSleep(Instruction):
    def execute(self, fr):
        secs = fr.data_pop(int)
        # TODO: use proper timequeue timeslicing.
        time.sleep(secs)


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
