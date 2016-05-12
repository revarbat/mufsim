#!/usr/bin/env python3

from __future__ import print_function

import os
import sys
import time
import argparse
from subprocess import call

try:
    import readline
except:
    pass

import mufsim.stackitems as si
import mufsim.gamedb as db
import mufsim.utils as util
from mufsim.logger import log, set_output_command
from mufsim.compiler import MufCompiler
from mufsim.stackframe import MufStackFrame
import mufsim.configs as confs


def log_print(msgtype, msg):
    if msgtype in ['warning', 'error']:
        print(msg, file=sys.stderr)
        sys.stderr.flush()
    else:
        print(msg)
        sys.stdout.flush()


class ConsoleMufDebugger(object):
    def __init__(self, fr):
        self.fr = fr
        self.matches = []

    def handle_reads(self):
        readline = input("READ>")
        if readline is None or readline == "@Q":
            while self.fr.call_stack:
                self.fr.call_pop()
            while self.fr.catch_stack:
                self.fr.catch_pop()
            log("Aborting program.")
            return False
        if not readline and not self.fr.read_wants_blanks:
            log("Blank line ignored.")
            return True
        self.fr.pc_advance(1)
        if self.fr.wait_state == self.fr.WAIT_READ:
            self.fr.data_push(readline)
        elif readline == "@T":
            log("Faking time-out.")
            self.fr.data_push("")
            self.fr.data_push(1)
        else:
            self.fr.data_push(readline)
            self.fr.data_push(0)
        return True

    def resume_execution(self):
        while True:
            self.fr.execute_code()
            if not self.fr.get_call_stack():
                log("Program exited.")
                break
            if self.fr.wait_state in [
                self.fr.WAIT_READ, self.fr.WAIT_TREAD
            ] and self.handle_reads():
                continue
            break

    def complete(self, text, state):
        cmds = [
            'list ', 'quit', 'run', 'show ', 'next', 'step', 'break ',
            'continue', 'finish', 'stack', 'trace', 'notrace', 'delete ',
            'print ', 'pop', 'push ', 'rot', 'dup', 'swap', 'help'
        ]
        response = None
        origline = readline.get_line_buffer()
        begin = readline.get_begidx()
        end = readline.get_endidx()
        text = origline[begin:end]
        words = origline.split(' ')
        if state == 0:
            addr = self.fr.curr_addr()
            # This is the first time for this text, so build a match list.
            if begin == 0:
                self.matches = [s for s in cmds if s and s.startswith(text)]
            elif words[0] in ['l', 'list', 'b', 'break']:
                self.matches = [
                    x
                    for x in self.fr.program_functions(addr.prog)
                    if x.startswith(text)
                ]
            elif words[0] == 'show':
                showcmds = ['breakpoints', 'functions', 'globals', 'vars']
                self.matches = [x for x in showcmds if x.startswith(text)]
            elif words[0] in ['p', 'print']:
                fun = self.fr.program_find_func(addr)
                fvars = self.fr.program_func_vars(addr.prog, fun)
                gvars = self.fr.program_global_vars(addr.prog)
                self.matches = [
                    x for x in (fvars + gvars) if x.startswith(text)
                ]
            else:
                self.matches = cmds[:]
        # Return the state'th item from the match list,
        # if we have that many.
        try:
            response = self.matches[state]
        except IndexError:
            response = None
        return response

    def show_compiled_tokens(self, prog):
        alltokens = self.fr.program_tokens(prog)
        for inum, tokeninfo in enumerate(alltokens):
            rep = tokeninfo['repr']
            if inum > 0 and rep.startswith("Function:"):
                log("")
            log("% 5d: %s" % (inum, rep))

    def show_addr_line(self, addr):
        if not addr:
            return
        inst = self.fr.get_inst(addr)
        src = self.fr.program_source_line(addr.prog, inst.line)
        curraddr = self.fr.curr_addr()
        mark = ' '
        if addr == curraddr:
            mark = '>'
        log("%s% 5d: %s" % (mark, inst.line, src))

    def debug_cmd_step(self, args):
        if not args:
            args = "1"
        if not util.is_int(args):
            log("Usage: step [COUNT]")
            return
        self.fr.set_break_steps(int(args))
        self.resume_execution()
        self.show_addr_line(self.fr.curr_addr())
        self.fr.nextline = -1

    def debug_cmd_next(self, args):
        if not args:
            args = "1"
        if not util.is_int(args):
            log("Usage: next [COUNT]")
            return
        self.fr.set_break_lines(int(args))
        self.resume_execution()
        self.show_addr_line(self.fr.curr_addr())
        self.fr.nextline = -1

    def debug_cmd_continue(self, args):
        self.fr.reset_breaks()
        self.resume_execution()
        self.show_addr_line(self.fr.curr_addr())
        self.fr.nextline = -1

    def debug_cmd_finish(self, args):
        self.fr.set_break_on_finish()
        self.resume_execution()
        self.show_addr_line(self.fr.curr_addr())
        self.fr.nextline = -1

    def debug_cmd_break(self, args):
        addr = self.fr.curr_addr()
        prog = addr.prog
        if ' ' in args:
            prg, args = args.split(' ', 1)
            prg = prg.strip()
            args = args.strip()
            obj = db.match_dbref(prg)
            if obj == -1:
                obj = db.match_registered(db.getobj(0), prg)
            obj = db.getobj(obj)
            if not db.validobj(obj):
                log("Invalid program!")
                return
            if db.getobj(obj).objtype != "program":
                log("Invalid program!")
                return
            prog = obj
        addr = self.fr.program_function_addr(prog, args)
        if addr:
            line = self.fr.get_inst_line(addr)
            bpnum = self.fr.add_breakpoint(prog, line)
            log("Added breakpoint %d at #%d line %d." % (bpnum, prog, line))
        elif util.is_int(args):
            line = int(args)
            bpnum = self.fr.add_breakpoint(prog, line)
            log("Added breakpoint %d at #%d line %d." % (bpnum, prog, line))
        else:
            log("Usage: break [PROG] LINE")
            log("   or: break [PROG] FUNCNAME")

    def debug_cmd_delete(self, args):
        bps = self.fr.get_breakpoints()
        if not util.is_int(args) or int(args) - 1 not in list(range(len(bps))):
            log("Usage: delete BREAKPOINTNUM")
        else:
            self.fr.del_breakpoint(int(args) - 1)
            log("Deleted breakpoint %d." % int(args))

    def debug_cmd_list(self, args):
        addr = self.fr.curr_addr()
        inst = self.fr.get_inst(addr)
        prog = addr.prog
        if self.fr.program_function_addr(prog, args):
            addr = self.fr.program_function_addr(prog, args)
            start = self.fr.get_inst_line(addr)
            end = start + 10
        elif ',' in args:
            start, end = args.split(',', 1)
            start = start.strip()
            end = end.strip()
        elif args:
            start = end = args
        elif self.fr.nextline < 0:
            start = str(inst.line - 5)
            end = str(inst.line + 5)
        else:
            start = self.fr.nextline
            end = self.fr.nextline + 10
        if not util.is_int(start) or not util.is_int(end):
            log("Usage: list [LINE[,LINE]]")
            log("   or: list FUNCNAME")
        else:
            srcs = self.fr.program_source_lines(prog)
            start = max(1, min(int(start), len(srcs)))
            end = max(1, min(int(end), len(srcs)))
            self.fr.nextline = end + 1
            for i in range(start, end + 1):
                src = srcs[i - 1]
                if i == inst.line:
                    log(">% 5d: %s" % (i, src))
                else:
                    log(" % 5d: %s" % (i, src))

    def debug_cmd_print(self, args):
        addr = self.fr.curr_addr()
        fun = self.fr.program_find_func(addr)
        if self.fr.program_func_var(addr.prog, fun, args):
            v = self.fr.program_func_var(addr.prog, fun, args)
            val = self.fr.funcvar_get(v)
        elif self.fr.program_global_var(addr.prog, args):
            v = self.fr.program_global_var(addr.prog, args)
            val = self.fr.globalvar_get(v)
        else:
            log("Variable not found: %s" % args)
            val = None
        if val is not None:
            val = si.item_repr(val)
            log("%s = %s" % (args, val))

    def debug_cmd_show_breakpoints(self):
        log("Breakpoints")
        cnt = 0
        bps = self.fr.get_breakpoints()
        for i, bp in enumerate(bps):
            prog, line = bp
            if prog and line:
                log("  %d: Program #%d Line %d" % (i + 1, prog, line))
                cnt += 1
        if not cnt:
            log("  - None -")

    def debug_cmd_show_functions(self):
        log("Declared Functions")
        addr = self.fr.curr_addr()
        funcs = self.fr.program_functions(addr.prog)
        if funcs:
            for func in funcs:
                log("  %s" % func)
        else:
            log("  - None -")

    def debug_cmd_show_globals(self):
        log("Global Variables")
        addr = self.fr.curr_addr()
        gvars = self.fr.program_global_vars(addr.prog)
        if gvars:
            for vnum, vname in enumerate(gvars):
                val = self.fr.globalvar_get(vnum)
                val = si.item_repr(val)
                log("  LV%-3d %s = %s" % (vnum, vname, val))
        else:
            log("  - None -")

    def debug_cmd_show_vars(self):
        log("Function Variables")
        addr = self.fr.curr_addr()
        fun = self.fr.program_find_func(addr)
        fvars = self.fr.program_func_vars(addr.prog, fun)
        if fvars:
            for vnum, vname in enumerate(fvars):
                val = self.fr.funcvar_get(vnum)
                val = si.item_repr(val)
                log("  SV%-3d %s = %s" % (vnum, vname, val))
        else:
            log("  - None -")

    def debug_cmd_show(self, args):
        if args == "breakpoints":
            self.debug_cmd_show_breakpoints()
        elif args == "functions":
            self.debug_cmd_show_functions()
        elif args == "globals":
            self.debug_cmd_show_globals()
        elif args == "vars":
            self.debug_cmd_show_vars()
        else:
            log("Usage: show breakpoints")
            log("   or: show functions")
            log("   or: show globals")
            log("   or: show vars")

    def debug_cmd_stack(self, args):
        if not args:
            args = "999999"
        if not util.is_int(args):
            log("Usage: stack [DEPTH]")
        else:
            depth = self.fr.data_depth()
            args = int(args)
            if args > depth:
                args = depth
            for i in range(args):
                val = self.fr.data_pick(i + 1)
                val = si.item_repr(val)
                log("Stack %d: %s" % (depth - i, val))
            if not depth:
                log("- Empty Stack -")

    def debug_cmd_trace(self, args):
        self.fr.set_trace(True)
        log("Turning on Trace mode.")

    def debug_cmd_notrace(self, args):
        self.fr.set_trace(False)
        log("Turning off Trace mode.")

    def debug_cmd_pop(self, args):
        self.fr.data_pop()
        log("Stack item POPed.")

    def debug_cmd_dup(self, args):
        a = self.fr.data_pick(1)
        self.fr.data_push(a)
        log("Stack item DUPed.")

    def debug_cmd_swap(self, args):
        a = self.fr.data_pop()
        b = self.fr.data_pop()
        self.fr.data_push(a)
        self.fr.data_push(b)
        log("Stack items SWAPed.")

    def debug_cmd_rot(self, args):
        a = self.fr.data_pop()
        b = self.fr.data_pop()
        c = self.fr.data_pop()
        self.fr.data_push(b)
        self.fr.data_push(a)
        self.fr.data_push(c)
        log("Stack items ROTed.")

    def debug_cmd_push(self, args):
        if util.is_int(args):
            self.fr.data_push(int(args))
        elif util.is_float(args):
            self.fr.data_push(float(args))
        elif util.is_dbref(args):
            self.fr.data_push(si.DBRef(int(args[1:])))
        elif util.is_strlit(args):
            self.fr.data_push(args[1:-1])
        log("Stack item pushed.")

    def debug_cmd_where(self, args):
        fmt = "{level:-3d}: In prog {prog}, func '{func}', line {line}: {inst}"
        fmt += "\n    {src}"
        for callinfo in self.fr.get_call_stack():
            log(fmt.format(**callinfo))

    def debug_cmd_run(self, args):
        userobj = db.get_player_obj("John_Doe")
        progobj = db.get_registered_obj(userobj, "$cmd/test")
        trigobj = db.get_registered_obj(userobj, "$testaction")
        self.fr = MufStackFrame()
        self.fr.setup(progobj, userobj, trigobj, self.opts.command)
        log("Restarting program.")
        self.debug_cmd_list("")

    def debug_cmd_help(self, args):
        log("help               Show this message.")
        log("where              Display the call stack.")
        log("stack [DEPTH]      Show top N data stack items.")
        log("list               List next few source code lines.")
        log("list LINE          List source code LINE.")
        log("list START,END     List source code from START to END.")
        log("list FUNC          List source code at start of FUNC.")
        log("break LINE         Set breakpoint at given line.")
        log("break FUNC         Set breakpoint at start of FUNC.")
        log("delete BREAKNUM    Delete a breakpoint.")
        log("show breakpoints   Show current breakpoints.")
        log("show functions     List all declared functions.")
        log("show globals       List all global vars.")
        log("show vars          List all vars in the current func.")
        log("step [COUNT]       Step 1 or COUNT lines, enters calls.")
        log("next [COUNT]       Step 1 or COUNT lines, skips calls.")
        log("finish             Finish the current function.")
        log("cont               Continue until next breakpoint.")
        log("pop                Pop top data stack item.")
        log("dup                Duplicate top data stack item.")
        log("swap               Swap top two data stack items.")
        log("rot                Rot top three data stack items.")
        log("push VALUE         Push VALUE onto top of data stack.")
        log("print VARIABLE     Print the value of the variable.")
        log("trace              Turn on tracing of each instr.")
        log("notrace            Turn off tracing if each instr.")
        log("run COMMANDARG     Re-run program, with COMMANDARG.")
        log("quit               Exits the debugger.")

    def debug_code(self):
        prevcmd = ""
        self.fr.nextline = -1
        try:
            readline.set_completer(self.complete)
            readline.set_completer_delims(" ")
            readline.parse_and_bind("tab: complete")
        except:
            pass
        while True:
            if prevcmd:
                cmd = input("DEBUG>")
                if not cmd:
                    cmd = prevcmd
            else:
                cmd = "list"
            prevcmd = cmd
            args = ""
            if " " in cmd:
                cmd, args = cmd.split(" ", 1)
                cmd = cmd.strip()
                args = args.strip()
            if cmd == "q" or cmd == "quit":
                log("Exiting.")
                return
            commands = {
                "break": self.debug_cmd_break,
                "c": self.debug_cmd_continue,
                "cont": self.debug_cmd_continue,
                "delete": self.debug_cmd_delete,
                "dup": self.debug_cmd_dup,
                "f": self.debug_cmd_finish,
                "finish": self.debug_cmd_finish,
                "help": self.debug_cmd_help,
                "l": self.debug_cmd_list,
                "list": self.debug_cmd_list,
                "n": self.debug_cmd_next,
                "next": self.debug_cmd_next,
                "notrace": self.debug_cmd_notrace,
                "pop": self.debug_cmd_pop,
                "p": self.debug_cmd_print,
                "print": self.debug_cmd_print,
                "push": self.debug_cmd_push,
                "rot": self.debug_cmd_rot,
                "run": self.debug_cmd_run,
                "show": self.debug_cmd_show,
                "stack": self.debug_cmd_stack,
                "s": self.debug_cmd_step,
                "step": self.debug_cmd_step,
                "swap": self.debug_cmd_swap,
                "t": self.debug_cmd_trace,
                "trace": self.debug_cmd_trace,
                "w": self.debug_cmd_where,
                "where": self.debug_cmd_where,
            }
            if cmd in commands:
                commands[cmd](args)
            else:
                self.debug_cmd_help(args)
            if not self.fr.call_stack:
                break


class MufConsole(object):
    def header(self, header):
        out = '#### %s ' % header
        out += '#' * (55 - len(out))
        log(out)

    def process_cmdline(self):
        parser = argparse.ArgumentParser(prog='mufsim')
        parser.add_argument("-u", "--uncompile",
                            help="Show compiled MUF tokens.",
                            action="store_true")
        parser.add_argument("-r", "--run",
                            help="Run compiled MUF tokens.",
                            action="store_true")
        parser.add_argument("--timing",
                            help="Show run execution timing.",
                            action="store_true")
        parser.add_argument("-t", "--trace",
                            help="Show stacktrace for each instrution.",
                            action="store_true")
        parser.add_argument("-d", "--debug",
                            help="Run MUF program in interactive debugger.",
                            action="store_true")
        parser.add_argument("-c", "--command", type=str, default="",
                            help="Specify text to push onto the stack for run.")
        parser.add_argument("-e", "--textentry", action='append', default=[],
                            help="Specify text to enter on READs.")
        parser.add_argument("-f", "--textfile", type=str,
                            help="File to read from for READs.")
        parser.add_argument(
            "-p", "--program", action='append', default=[],
            nargs=2, metavar=('REGNAME', 'FILE'), dest='progs',
            help="Create extra program, registered as $NAME, from source FILE."
        )
        parser.add_argument('infile', help='Input MUF sourcecode filename.')
        opts = parser.parse_args()
        opts.progs.append(['', opts.infile])
        if opts.debug:
            opts.run = True
        if opts.textfile:
            with open(opts.textfile, "r") as f:
                for line in f.readlines():
                    opts.textentry.append(line.rstrip("\n"))
        self.opts = opts
        return opts

    def readline_setup(self):
        try:
            readline.read_history_file(confs.HISTORY_FILE)
            readline.set_history_length(1000)
        except:
            pass

    def readline_teardown(self):
        try:
            readline.write_history_file(confs.HISTORY_FILE)
        except:
            pass

    def process_muv(self, infile):
        tmpfile = infile
        if tmpfile[-4:] == ".muv":
            tmpfile = tmpfile[:-1] + 'f'
        else:
            tmpfile += ".muf"
        retcode = call(["muv", "-o", tmpfile, infile], stderr=sys.stderr)
        if retcode != 0:
            log("Aborting.")
            return None
        return tmpfile

    def run_code(self):
        self.readline_setup()
        userobj = db.get_player_obj("John_Doe")
        progobj = db.get_registered_obj(userobj, "$cmd/test")
        trigobj = db.get_registered_obj(userobj, "$testaction")
        fr = MufStackFrame()
        fr.setup(
            progobj,
            userobj,
            trigobj,
            self.opts.command
        )
        fr.set_trace(self.opts.trace)
        fr.set_text_entry(self.opts.textentry)
        dbg = ConsoleMufDebugger(fr)
        if self.opts.debug:
            dbg.debug_code()
        else:
            st = time.time()
            dbg.resume_execution()
            et = time.time()
            log("Execution completed in %d steps." % fr.cycles)
            if self.opts.timing:
                log("%g secs elapsed.  %g instructions/sec" %
                    (et-st, fr.cycles/(et-st)))
        self.readline_teardown()

    def show_compiled_tokens(self, prog):
        prog = db.getobj(prog)
        if not prog.compiled:
            return
        alltokens = prog.compiled.get_tokens_info()
        for inum, tokeninfo in enumerate(alltokens):
            rep = tokeninfo['repr']
            if inum > 0 and rep.startswith("Function:"):
                log("")
            log("% 5d: %s" % (inum, rep))

    def main(self):
        self.process_cmdline()
        for name, filename in self.opts.progs:
            origfile = filename
            if filename.endswith(".muv"):
                self.header("Compiling MUV Code to MUF")
                filename = self.process_muv(filename)
                log("")
            if not filename:
                return
            srcs = ""
            with open(filename, "r") as f:
                srcs = f.read()
            if origfile.endswith(".muv"):
                os.unlink(filename)
            userobj = db.get_player_obj("John_Doe")
            if name:
                globenv = db.get_registered_obj(userobj, "$globalenv")
                progobj = db.DBObject(
                    name=name,
                    objtype="program",
                    flags="3",
                    owner=userobj.dbref,
                    location=userobj.dbref,
                )
                db.register_obj(globenv, name, progobj)
                log("CREATED PROG %s, REGISTERED AS $%s\n" % (progobj, name))
            else:
                progobj = db.get_registered_obj(userobj, "$cmd/test")
            progobj.sources = srcs
            self.header("Compiling MUF Program %s" % progobj)
            success = MufCompiler().compile_source(progobj.dbref)
            log("")
            if not success:
                return
            if self.opts.uncompile:
                self.header("Showing Tokens for %s" % progobj)
                self.show_compiled_tokens(progobj)
                log("")
        if self.opts.run:
            self.header("Executing Tokens")
            self.run_code()
            log("")


def main():
    set_output_command(log_print)
    MufConsole().main()


if __name__ == "__main__":
    main()


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
