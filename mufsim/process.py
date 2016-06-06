import copy
import time

import mufsim.stackitems as si
import mufsim.gamedb as db
from mufsim.compiler import MufCompiler
from mufsim.logger import log, warnlog, errlog
from mufsim.errors import MufRuntimeError, MufBreakExecution
from mufsim.callframe import MufCallFrame
from mufsim.events import MufEventQueue


class MufProcess(object):
    MAX_STACK = 1024
    FP_ERRORS_LIST = [
        ("DIV_ZERO", "Division by zero attempted."),
        ("NAN", "Result was not a number."),
        ("IMAGINARY", "Result was imaginary."),
        ("FBOUNDS", "Floating-point inputs were infinite or out of range."),
        ("IBOUNDS", "Calculation resulted in an integer overflow."),
    ]
    BREAK_NONE = ''
    BREAK_INST = 'INST'
    BREAK_STEP = 'STEP'
    BREAK_NEXT = 'NEXT'
    BREAK_FINISH = 'FINISH'

    MODE_PREEMPT = 0
    MODE_FOREGROUND = 1
    MODE_BACKGROUND = 2

    def __init__(self, proclist):
        self.proclist = proclist
        self.user = si.DBRef(-1)
        self.program = si.DBRef(-1)
        self.trigger = si.DBRef(-1)
        self.command = ""
        self.catch_stack = []
        self.call_stack = []
        self.data_stack = []
        self.globalvars = {}
        self.fp_errors = 0
        self.events = MufEventQueue()
        self.watchers = []
        self.read_wants_blanks = False
        self.execution_mode = self.MODE_FOREGROUND
        self.wait_state = ''
        self.trace = False
        self.cycles = 0
        self.runtime = 0.0
        self.breakpoints = []
        self.break_on_error = False
        self.break_type = None
        self.break_count = -1
        self.prev_call_level = -1
        self.prevline = (-1, -1)
        self.text_entry = []
        self.start_time = time.time()
        self.fp_error_names = [v[0] for v in self.FP_ERRORS_LIST]
        self.fp_error_descrs = [v[1] for v in self.FP_ERRORS_LIST]
        self.fp_error_bits = [
            (1 << k) for k, v in enumerate(self.FP_ERRORS_LIST)
        ]

    ###############################################################

    def lookup_process(self, pid):
        return self.proclist.get(pid)

    def get_pids(self):
        self.proclist.get_pids()

    def timer_start(self, secs, name):
        self.proclist.timer_add(secs, self.pid, name)

    def timer_stop(self, name):
        self.proclist.timer_del(self.pid, name)

    def watch_pid(self, pid):
        self.proclist.watch_pid(self.pid, pid)

    def kill_pid(self, pid):
        self.proclist.kill_process(self.pid)

    def end_process(self):
        self.proclist.process_complete(self.pid)

    def fork_process(self):
        newproc = self.proclist.new_process()
        newproc.program = copy.deepcopy(self.program)
        newproc.user = copy.deepcopy(self.user)
        newproc.trigger = copy.deepcopy(self.trigger)
        newproc.command = self.command
        newproc.globalvar_set(0, copy.deepcopy(self.user))
        newproc.globalvar_set(1, si.DBRef(db.getobj(self.user).location))
        newproc.globalvar_set(2, copy.deepcopy(self.trigger))
        newproc.globalvar_set(3, self.command)
        newproc.catch_stack = copy.deepcopy(self.catch_stack)
        newproc.call_stack = copy.deepcopy(self.call_stack)
        newproc.data_stack = copy.deepcopy(self.data_stack)
        newproc.globalvars = copy.deepcopy(self.globalvars)
        newproc.fp_errors = self.fp_errors
        newproc.breakpoints = self.breakpoints
        newproc.break_on_error = self.break_on_error
        newproc.read_wants_blanks = self.read_wants_blanks
        newproc.execution_mode = self.MODE_BACKGROUND
        newproc.proclist.sleep(0.0, newproc.pid)
        newproc.pc_advance(1)
        return newproc

    ###############################################################

    def wait_for_read(self):
        self.proclist.wait_for_read(self.user.value, self.pid)
        raise MufBreakExecution()

    def sleep(self, secs):
        self.proclist.sleep(secs, self.pid)
        raise MufBreakExecution()

    def wait_for_events(self, pats):
        self.proclist.wait_for_events(self.pid, pats)
        raise MufBreakExecution()

    ###############################################################

    def setup(self, prog, user, trig, cmd):
        # Reset program state.
        self.catch_stack = []
        self.call_stack = []
        self.data_stack = []
        self.globalvars = {}
        self.fp_errors = 0
        self.read_wants_blanks = False
        self.cycles = 0
        self.runtime = 0.0
        # Set call info
        self.program = si.DBRef(prog.dbref)
        self.user = si.DBRef(user.dbref)
        self.trigger = si.DBRef(trig.dbref)
        self.command = cmd
        # Set globals
        self.globalvar_set(0, si.DBRef(user.dbref))
        self.globalvar_set(1, si.DBRef(user.location))
        self.globalvar_set(2, si.DBRef(trig.dbref))
        self.globalvar_set(3, cmd)
        # Setup call and data stacks
        comp = self.get_compiled(prog)
        self.call_push(comp.lastfunction, trig.dbref)
        self.data_push(cmd)

    def uses_prog(self, prog):
        prog = db.normobj(prog)
        for lev in range(len(self.call_stack)):
            addr = self.call_addr(level=lev)
            if addr and addr.prog == prog:
                return True
        return False

    def get_compiled(self, prog=-1):
        prog = db.normobj(prog)
        if prog < 0:
            addr = self.curr_addr()
            prog = addr.prog
        progobj = db.getobj(prog)
        return progobj.compiled

    def set_trace(self, on_off):
        self.trace = on_off

    def set_text_entry(self, text):
        if isinstance(text, list):
            self.text_entry = text
        else:
            self.text_entry = text.split('\n')

    def call_addr(self, level=-1):
        if not self.call_stack:
            return None
        return self.call_stack[level].pc

    def curr_addr(self):
        return self.call_addr()

    def get_inst(self, addr):
        comp = self.get_compiled(addr.prog)
        return comp.get_inst(addr)

    def get_inst_line(self, addr):
        comp = self.get_compiled(addr.prog)
        inst = comp.get_inst(addr)
        return inst.line

    def pc_advance(self, delta):
        if self.call_stack:
            return self.call_stack[-1].pc_advance(delta)
        return None

    def pc_set(self, addr):
        if not isinstance(addr, si.Address):
            raise MufRuntimeError("Expected an address!")
        return self.call_stack[-1].pc_set(addr)

    def call_push(self, addr, caller):
        self.call_stack.append(
            MufCallFrame(copy.deepcopy(addr), caller)
        )

    def call_pop(self):
        self.call_stack.pop()

    def caller_get(self, level=-1):
        return self.call_stack[level].caller

    def funcvar_get(self, v, level=-1):
        if isinstance(v, si.FuncVar):
            v = v.value
        return self.call_stack[level].variable_get(v)

    def funcvar_set(self, v, val, level=-1):
        if isinstance(v, si.FuncVar):
            v = v.value
        return self.call_stack[level].variable_set(v, val)

    def globalvar_get(self, v):
        if isinstance(v, si.GlobalVar):
            v = v.value
        if v in self.globalvars:
            return self.globalvars[v]
        return 0

    def globalvar_set(self, v, val):
        if isinstance(v, si.GlobalVar):
            v = v.value
        self.globalvars[v] = val

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
        addr = self.curr_addr()
        inst = self.get_inst(addr)
        caddr = self.catch_addr()
        if not caddr:
            errlog("Error in #%d line %d (%s): %s" %
                   (addr.prog, inst.line, str(inst), e))
            if self.break_on_error:
                self.break_count = -1
                self.break_type = None
            else:
                self.call_stack = []
            return False
        if not isinstance(caddr, si.Address):
            raise MufRuntimeError("Expected an address!")
        if self.trace:
            warnlog("Caught error in #%d line %d (%s): %s" %
                    (addr.prog, inst.line, str(inst), e))
        # Clear stack down to stacklock
        while self.data_depth() > self.catch_locklevel():
            self.data_pop()
        if self.catch_is_detailed():
            # Push detailed exception info.
            self.data_push(
                {
                    "error": str(e),
                    "instr": inst.prim_name.upper(),
                    "line": inst.line,
                    "program": si.DBRef(addr.prog),
                }
            )
        else:
            # Push error message.
            self.data_push(str(e))
        self.catch_pop()
        self.pc_set(caddr)
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
            self.data_stack.insert(-n, val)

    def loop_iter_push(self, typ, it):
        return self.call_stack[-1].loop_iter_push(typ, it)

    def loop_iter_pop(self):
        return self.call_stack[-1].loop_iter_pop()

    def loop_iter_top(self):
        return self.call_stack[-1].loop_iter_top()

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

    def _trigger_breakpoint(self):
        self.break_count = -1
        self.break_type = None
        raise MufBreakExecution()

    def _check_inst_based_breakpoints(self):
        if self.break_type == self.BREAK_INST:
            if self.break_count > 0:
                self.break_count -= 1
                if not self.break_count:
                    self._trigger_breakpoint()
        elif self.break_type == self.BREAK_FINISH:
            if len(self.call_stack) < self.prev_call_level:
                self._trigger_breakpoint()

    def _check_line_based_breakpoints(self):
        addr = self.curr_addr()
        line = self.get_inst_line(addr)
        currline = (addr.prog, line)
        if currline != self.prevline:
            # line changed.
            if self.breakpoints:
                if currline in self.breakpoints:
                    bpnum = self.breakpoints.index(currline)
                    warnlog("Stopped at breakpoint %d." % bpnum)
                    self._trigger_breakpoint()
            if self.break_type == self.BREAK_NEXT:
                if len(self.call_stack) > self.prev_call_level:
                    return
            self.prevline = currline
            if self.break_type in [self.BREAK_STEP, self.BREAK_NEXT]:
                if self.break_count > 0:
                    self.break_count -= 1
                    if not self.break_count:
                        self._trigger_breakpoint()

    def check_breakpoints(self):
        if not self.call_stack:
            self.end_process()
            self._trigger_breakpoint()
        if not self.break_type and not self.breakpoints:
            return
        self._check_inst_based_breakpoints()
        self._check_line_based_breakpoints()

    def execute_code(self, level=-1):
        maxcycles = {
            self.MODE_PREEMPT: 999999999,
            self.MODE_FOREGROUND: 10000,
            self.MODE_BACKGROUND: 10000,
        }
        level += len(self.call_stack) if level < 0 else 0
        starttime = time.time()
        self.prev_call_level = level + 1
        addr = self.curr_addr()
        inst = self.get_inst(addr)
        self.prevline = (addr.prog, inst.line)
        slice_cycles = 0
        while self.call_stack:
            addr = self.curr_addr()
            inst = self.get_inst(addr)
            if self.trace:
                log(self.get_trace_line(), msgtype='trace')
            try:
                try:
                    self.cycles += 1
                    slice_cycles += 1
                    inst.execute(self)
                    self.pc_advance(1)
                    if slice_cycles >= maxcycles[self.execution_mode]:
                        self.sleep(0.0)
                    self.check_breakpoints()
                except (MufRuntimeError, db.InvalidObjectError) as e:
                    if not self.catch_trigger(e):
                        self.runtime += time.time() - starttime
                        return
                    self.check_breakpoints()
            except MufBreakExecution as e:
                self.runtime += time.time() - starttime
                return

    ###############################################################

    def get_programs(self):
        return db.get_all_programs()

    def program_compile(self, prog):
        progobj = db.getobj(prog)
        progobj.compiled = None
        res = False
        if progobj.sources:
            res = MufCompiler().compile_source(progobj.dbref)
        return res

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

    def get_breakpoints(self):
        return [(p, l) for p, l in self.breakpoints if p is not None]

    def find_breakpoint(self, prog, line):
        bp = (prog, line)
        if bp not in self.breakpoints:
            return None
        return self.breakpoints.index(bp)

    def add_breakpoint(self, prog, line):
        bp = (prog, line)
        self.breakpoints.append(bp)
        return len(self.breakpoints)

    def del_breakpoint(self, bpnum):
        self.breakpoints[bpnum] = (None, None)

    def reset_breaks(self):
        self.break_type = None
        self.break_count = -1

    def set_break_insts(self, insts):
        self.reset_breaks()
        self.break_type = self.BREAK_INST
        self.break_count = insts

    def set_break_steps(self, steps):
        self.reset_breaks()
        self.break_type = self.BREAK_STEP
        self.break_count = steps

    def set_break_lines(self, lines):
        self.reset_breaks()
        self.break_type = self.BREAK_NEXT
        self.break_count = lines

    def set_break_on_finish(self, val=True):
        if val:
            self.reset_breaks()
            self.break_type = self.BREAK_FINISH
            self.break_count = val

    def set_break_on_error(self, val=True):
        self.break_on_error = val

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
        for i in range(-depth, 0):
            if out:
                out += ', '
            out += si.item_repr(self.data_stack[i])
        return out

    def get_trace_line(self):
        addr = self.curr_addr()
        inst = self.get_inst(addr)
        line = inst.line
        return(
            "% 5d: #%d line %d (%s) %s" % (
                addr.value, addr.prog, line,
                self._get_stack_repr(20), inst
            )
        )


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
