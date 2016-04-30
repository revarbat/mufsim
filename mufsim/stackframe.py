import sys
import copy

import mufsim.stackitems as si
import mufsim.gamedb as db
from mufsim.logger import log
from mufsim.errors import MufRuntimeError, MufBreakExecution
from mufsim.callframe import MufCallFrame


class MufStackFrame(object):
    MAX_STACK = 1024
    FP_ERRORS_LIST = [
        ("DIV_ZERO", "Division by zero attempted."),
        ("NAN", "Result was not a number."),
        ("IMAGINARY", "Result was imaginary."),
        ("FBOUNDS", "Floating-point inputs were infinite or out of range."),
        ("IBOUNDS", "Calculation resulted in an integer overflow."),
    ]

    def __init__(self):
        self.user = si.DBRef(-1)
        self.program = si.DBRef(-1)
        self.trigger = si.DBRef(-1)
        self.command = ""
        self.catch_stack = []
        self.call_stack = []
        self.data_stack = []
        self.globalvars = {}
        self.fp_errors = 0
        self.read_wants_blanks = False
        self.execution_mode = 1
        self.trace = False
        self.cycles = 0
        self.breakpoints = []
        self.break_after_insts = -1
        self.break_after_steps = -1
        self.break_after_lines = -1
        self.break_on_finish = False
        self.prevaddr = si.Address(-1, self.program)
        self.prevline = -1
        self.nextline = -1
        self.text_entry = []
        self.fp_error_names = [v[0] for v in self.FP_ERRORS_LIST]
        self.fp_error_descrs = [v[1] for v in self.FP_ERRORS_LIST]
        self.fp_error_bits = [
            (1 << k) for k, v in enumerate(self.FP_ERRORS_LIST)
        ]

    def setup(self, prog, user, trig, cmd):
        # Reset program state.
        self.catch_stack = []
        self.call_stack = []
        self.data_stack = []
        self.globalvars = {}
        self.fp_errors = 0
        self.read_wants_blanks = False
        self.cycles = 0
        # Set call info
        self.user = si.DBRef(user.dbref)
        self.trigger = si.DBRef(trig.dbref)
        self.command = cmd
        self.program = si.DBRef(prog.dbref)
        # Set globals
        self.globalvar_set(0, si.DBRef(user.dbref))
        self.globalvar_set(1, si.DBRef(user.location))
        self.globalvar_set(2, si.DBRef(trig.dbref))
        self.globalvar_set(3, cmd)
        # Setup call and data stacks
        comp = self.get_compiled(prog)
        self.call_push(comp.lastfunction, trig.dbref)
        self.data_push(cmd)

    def get_compiled(self, prog=-1):
        if prog < 0:
            addr = self.curr_addr()
            prog = addr.prog
        return db.getobj(prog).compiled

    def set_trace(self, on_off):
        self.trace = on_off

    def set_text_entry(self, text):
        if type(text) is list:
            self.text_entry = text
        else:
            self.text_entry = text.split('\n')

    def curr_inst(self):
        if not self.call_stack:
            return None
        addr = self.curr_addr()
        comp = self.get_compiled()
        return comp.get_inst(addr)

    def curr_addr(self):
        if not self.call_stack:
            return None
        return self.call_stack[-1].pc

    def pc_advance(self, delta):
        if self.call_stack:
            return self.call_stack[-1].pc_advance(delta)
        return None

    def pc_set(self, addr):
        if type(addr) is not si.Address:
            raise MufRuntimeError("Expected an address!")
        return self.call_stack[-1].pc_set(addr)

    def catch_push(self, detailed, addr, lockdepth):
        self.catch_stack.append((detailed, addr, lockdepth))

    def catch_pop(self):
        return self.catch_stack.pop()

    def catch_is_detailed(self):
        if not self.catch_stack:
            return False
        return self.catch_stack[-1][0]

    def catch_addr(self):
        if not self.catch_stack:
            return None
        return self.catch_stack[-1][1]

    def catch_locklevel(self):
        if not self.catch_stack:
            return 0
        return self.catch_stack[-1][2]

    def catch_trigger(self, e):
        addr = self.catch_addr()
        if not addr:
            return False
        if type(addr) is not si.Address:
            raise MufRuntimeError("Expected an address!")
        # Clear stack down to stacklock
        while self.data_depth() > self.catch_locklevel():
            self.data_pop()
        if self.catch_is_detailed():
            # Push detailed exception info.
            inst = self.curr_inst()
            self.data_push({
                "error": str(e),
                "instr": inst.prim_name.upper(),
                "line": inst.line,
                "program": self.program,
            })
        else:
            # Push error message.
            self.data_push(str(e))
        self.catch_pop()
        self.pc_set(addr)
        return True

    def check_type(self, val, types):
        if types and type(val) not in types:
            self.raise_expected_type_error(types)

    def raise_expected_type_error(self, types):
        types = list(types)
        type_names = [
            ("number", [int, float]),
            ("integer", [int]),
            ("float", [float]),
            ("string", [str]),
            ("array", [list, dict]),
            ("list array", [list]),
            ("dictionary array", [dict]),
            ("dbref", [si.DBRef]),
            ("address", [si.Address]),
            ("lock", [si.Lock]),
            ("variable", [si.GlobalVar, si.FuncVar]),
            ("variable", [si.GlobalVar]),
            ("variable", [si.FuncVar]),
        ]
        expected = []
        for name, extypes in type_names:
            found = True
            for extype in extypes:
                if extype not in types:
                    found = False
                    break
            if found:
                for extype in extypes:
                    types.remove(extype)
                expected.append(name)
        expected = " or ".join(expected)
        raise MufRuntimeError("Expected %s argument." % expected)

    def check_underflow(self, cnt):
        if self.data_depth() < cnt:
            raise MufRuntimeError("Stack underflow.")

    def data_depth(self):
        return len(self.data_stack)

    def data_push(self, x):
        self.data_stack.append(x)
        if len(self.data_stack) > self.MAX_STACK:
            raise MufRuntimeError("Stack overflow.")

    def data_pop(self, *types):
        if len(self.data_stack) - self.catch_locklevel() < 1:
            raise MufRuntimeError("Stack underflow.")
        self.check_type(self.data_stack[-1], types)
        return self.data_stack.pop()

    def data_pop_dbref(self):
        return self.data_pop(si.DBRef)

    def data_pop_object(self):
        return db.getobj(self.data_pop(si.DBRef))

    def data_pop_address(self):
        return self.data_pop(si.Address)

    def data_pop_lock(self):
        return self.data_pop(si.Lock)

    def data_pick(self, n):
        if len(self.data_stack) < n:
            raise MufRuntimeError("Stack underflow.")
        return self.data_stack[-n]

    def data_pull(self, n):
        if len(self.data_stack) - self.catch_locklevel() < n:
            raise MufRuntimeError("Stack underflow.")
        a = self.data_stack[-n]
        del self.data_stack[-n]
        return a

    def data_put(self, n, val):
        if len(self.data_stack) - self.catch_locklevel() < n:
            raise MufRuntimeError("Stack underflow.")
        self.data_stack[-n] = val

    def data_insert(self, n, val):
        if len(self.data_stack) - self.catch_locklevel() < n:
            raise MufRuntimeError("StackUnderflow")
        if n < 1:
            self.data_stack.append(val)
        else:
            self.data_stack.insert(1 - n, val)

    def loop_iter_push(self, typ, it):
        return self.call_stack[-1].loop_iter_push(typ, it)

    def loop_iter_pop(self):
        return self.call_stack[-1].loop_iter_pop()

    def loop_iter_top(self):
        return self.call_stack[-1].loop_iter_top()

    def call_push(self, addr, caller):
        self.call_stack.append(
            MufCallFrame(copy.deepcopy(addr), caller)
        )

    def call_pop(self):
        self.call_stack.pop()

    def caller_get(self):
        return self.call_stack[-1].caller

    def funcvar_get(self, v):
        if type(v) is si.FuncVar:
            v = v.value
        return self.call_stack[-1].variable_get(v)

    def funcvar_set(self, v, val):
        if type(v) is si.FuncVar:
            v = v.value
        return self.call_stack[-1].variable_set(v, val)

    def globalvar_get(self, v):
        if type(v) is si.GlobalVar:
            v = v.value
        if v in self.globalvars:
            return self.globalvars[v]
        return 0

    def globalvar_set(self, v, val):
        if type(v) is si.GlobalVar:
            v = v.value
        self.globalvars[v] = val

    def has_errors(self):
        return self.fp_errors != 0

    def has_error(self, errname):
        errname = errname.upper()
        errnum = self.fp_error_names.index(errname)
        errbit = self.fp_error_bits[errnum]
        return (self.fp_errors & errbit) != 0

    def set_error(self, errname):
        errname = errname.upper()
        errnum = self.fp_error_names.index(errname)
        errbit = self.fp_error_bits[errnum]
        self.fp_errors |= errbit

    def clear_error(self, errname):
        errname = errname.upper()
        errnum = self.fp_error_names.index(errname)
        errbit = self.fp_error_bits[errnum]
        self.fp_errors &= ~errbit

    def clear_errors(self):
        self.fp_errors = 0

    def check_break_on_finish(self):
        if self.break_on_finish:
            if len(self.call_stack) < self.prev_call_level:
                inst = self.curr_inst()
                addr = self.curr_addr()
                log(
                    "Stopped on call return at instruction %d in #%d." %
                    (addr.value, addr.prog)
                )
                self.prevline = inst.line
                self.prevaddr = addr
                self.break_on_finish = False
                raise MufBreakExecution()

    def check_break_after_insts(self):
        if self.break_after_insts > 0:
            inst = self.curr_inst()
            self.prevline = inst.line
            self.break_after_insts -= 1
            if not self.break_after_insts:
                addr = self.curr_addr()
                self.prevaddr = addr
                self.break_after_insts = -1
                raise MufBreakExecution()

    def check_break_after_steps(self):
        if self.break_after_steps > 0:
            inst = self.curr_inst()
            if inst.line != self.prevline:
                self.prevline = inst.line
                self.break_after_steps -= 1
                if not self.break_after_steps:
                    addr = self.curr_addr()
                    self.prevaddr = addr
                    self.break_after_steps = -1
                    raise MufBreakExecution()

    def check_break_after_lines(self):
        if self.break_after_lines > 0:
            if len(self.call_stack) <= self.prev_call_level:
                inst = self.curr_inst()
                addr = self.curr_addr()
                if inst.line != self.prevline:
                    self.prevline = inst.line
                    self.break_after_lines -= 1
                    if not self.break_after_lines:
                        self.prevaddr = addr
                        self.break_after_lines = -1
                        raise MufBreakExecution()

    def check_breakpoints(self):
        if not self.call_stack:
            raise MufBreakExecution()
        if self.breakpoints:
            inst = self.curr_inst()
            addr = self.curr_addr()
            if inst.line != self.prevline or addr.prog != self.prevaddr.prog:
                bp = (addr.prog, inst.line)
                if bp in self.breakpoints:
                    bpnum = self.breakpoints.index(bp)
                    log("Stopped at breakpoint %d." % bpnum)
                    self.prevline = inst.line
                    self.prevaddr = addr
                    raise MufBreakExecution()
        self.check_break_on_finish()
        self.check_break_after_insts()
        self.check_break_after_steps()
        self.check_break_after_lines()

    def execute_code(self):
        self.prev_call_level = len(self.call_stack)
        while self.call_stack:
            inst = self.curr_inst()
            addr = self.curr_addr()
            line = inst.line
            if self.trace:
                log(self.get_trace_line())
                sys.stdout.flush()
            try:
                self.cycles += 1
                inst.execute(self)
                self.pc_advance(1)
                self.check_breakpoints()
            except MufBreakExecution as e:
                return
            except MufRuntimeError as e:
                if not self.catch_stack:
                    log(
                        "Error in #%d line %d (%s): %s" % (
                            addr.prog, line, str(inst), e
                        )
                    )
                    return
                elif self.trace:
                    log(
                        "Caught error in #%d line %d (%s): %s" % (
                            addr.prog, line, str(inst), e
                        )
                    )
                self.catch_trigger(e)
                try:
                    self.check_breakpoints()
                except MufBreakExecution as e:
                    return

    ###############################################################
    def get_programs(self):
        return db.get_all_compiled_programs()

    def program_tokens(self, prog):
        comp = self.get_compiled(prog)
        return comp.get_tokens_info()

    def program_source_lines(self, prog):
        comp = self.get_compiled(prog)
        return comp.srclines

    def program_source_line(self, prog, line):
        comp = self.get_compiled(prog)
        return comp.srclines[line - 1]

    def get_addr_source_line(self, addr):
        comp = self.get_compiled(addr.prog)
        inst = comp.get_inst(addr)
        return comp.srclines[inst.line - 1]

    def program_functions(self, prog):
        comp = self.get_compiled(prog)
        return comp.get_functions()

    def program_function_addr(self, prog, fun):
        comp = self.get_compiled(prog)
        return comp.get_function_addr(fun)

    def get_function_addr(self, fun):
        comp = self.get_compiled()
        return comp.get_function_addr(fun)

    def get_inst(self, addr):
        comp = self.get_compiled(addr.prog)
        return comp.get_inst(addr)

    def get_inst_line(self, addr):
        comp = self.get_compiled(addr.prog)
        inst = comp.get_inst(addr)
        return inst.line

    def get_breakpoints(self):
        return self.breakpoints

    def add_breakpoint(self, prog, line):
        bp = (prog, line)
        self.breakpoints.append(bp)
        return len(self.breakpoints)

    def del_breakpoint(self, bpnum):
        self.breakpoints[bpnum] = (None, None)

    def set_break_insts(self, insts):
        self.break_after_insts = insts

    def set_break_steps(self, steps):
        self.break_after_steps = steps

    def set_break_lines(self, lines):
        self.break_after_lines = lines

    def set_break_on_finish(self, val=True):
        self.break_on_finish = val

    def get_data_stack(self):
        return self.data_stack

    def program_find_func(self, addr):
        comp = self.get_compiled(addr.prog)
        return comp.find_func(addr)

    def program_func_vars(self, prog, fun):
        comp = self.get_compiled(prog)
        return comp.get_func_vars(fun)

    def program_global_vars(self, prog):
        comp = self.get_compiled(prog)
        return comp.get_global_vars()

    def program_func_var(self, prog, fun, vname):
        comp = self.get_compiled(prog)
        return comp.get_func_var(fun, vname)

    def program_global_var(self, prog, vname):
        comp = self.get_compiled(prog)
        return comp.get_global_var(vname)

    def get_call_stack(self):
        out = []
        for lev, callfr in enumerate(self.call_stack):
            addr = callfr.pc
            inst = self.get_inst(addr)
            out.append(
                {
                    'level': lev,
                    'func': self.program_find_func(addr),
                    'prog': si.DBRef(addr.prog),
                    'line': inst.line,
                    'addr': addr.value,
                    'inst': str(inst),
                    'src': self.get_addr_source_line(addr),
                }
            )
        return out

    def _get_stack_repr(self, maxcnt):
        out = ''
        depth = self.data_depth()
        if maxcnt > depth:
            maxcnt = depth
        else:
            out += '...'
        for i in xrange(-depth, 0):
            if out:
                out += ', '
            out += si.item_repr(self.data_stack[i])
        return out

    def get_trace_line(self):
        inst = self.curr_inst()
        addr = self.curr_addr()
        line = inst.line
        return(
            "% 5d: #%d line %d (%s) %s" % (
                addr.value, addr.prog, line,
                self._get_stack_repr(20), inst
            )
        )


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
