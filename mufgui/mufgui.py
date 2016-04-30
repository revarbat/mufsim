#!/usr/bin/env python

import os
from subprocess import call
import Tkinter
from Tkinter import *
import tkFileDialog
import tkSimpleDialog
from ScrolledText import ScrolledText

import mufsim.stackitems as si
import mufsim.gamedb as db
from mufsim.logger import log, get_log, log_updated, clear_log
from mufsim.compiler import MufCompiler
from mufsim.stackframe import MufStackFrame

"""
Menus:
    App:
        Preferences
        Quit
    File:
        Open File
        Import Library
    Edit:
        Cut
        Copy
        Paste
        Undo
"""


class ReadOnlyText(ScrolledText):
    def __init__(self, *args, **kwargs):
        if 'insertontime' not in kwargs:
            kwargs['insertontime'] = 0
        if 'borderwidth' not in kwargs:
            kwargs['borderwidth'] = 1
        if 'highlightthickness' not in kwargs:
            kwargs['highlightthickness'] = 0
        ScrolledText.__init__(self, *args, **kwargs)
        self.bind("<Key>", lambda e: "break")
        self.bind("<<Cut>>", lambda e: "break")
        self.bind("<<Clear>>", lambda e: "break")
        self.bind("<<Paste>>", lambda e: "break")
        self.bind("<<PasteSelection>>", lambda e: "break")
        self.bind('<Double-Button-1>', lambda e: "break")
        self.tag_config("sel", foreground="black")


class ListDisplay(ReadOnlyText):
    def __init__(self, master, **kwargs):
        if 'font' not in kwargs:
            kwargs['font'] = "Helvetica"
        ReadOnlyText.__init__(
            self,
            master,
            relief=SUNKEN,
            cursor='arrow',
            takefocus=0,
            wrap=NONE,
            **kwargs
        )


class MufGui(object):
    def __init__(self):
        # TODO: get real command
        self.command = "me=test"
        self.fr = None
        self.current_program = None
        self.prev_prog = -1
        self.setup_gui()

    def setup_gui(self):
        root = Tk()
        self.root = root

        self.current_program = StringVar()
        self.current_program.set("- Load a Program -")
        self.current_function = StringVar()
        self.current_function.set("")

        root.title("MUF Debugger")
        root.protocol("WM_DELETE_WINDOW", self.destroy)
        root.option_add("*Panedwindow.sashWidth", "6")
        root.option_add("*Panedwindow.sashRelief", "raised")
        root.option_add("*Panedwindow.borderWidth", "1")
        root.option_add("*Background", "gray75")
        root.option_add("*Button.highlightBackground", "gray75")
        root.option_add("*Text.background", "white")
        root.option_add("*Text.highlightBackground", "white")
        root.option_add("*Entry.background", "white")
        root.option_add("*Entry.highlightBackground", "gray75")

        panes1 = PanedWindow(root)
        panes1.pack(fill=BOTH, expand=1)

        panes2 = PanedWindow(panes1, orient=VERTICAL)
        panes3 = PanedWindow(panes1, orient=VERTICAL)
        panes1.add(panes2, minsize=150, width=250)
        panes1.add(panes3, minsize=300)

        datafr = LabelFrame(panes2, text="Data Stack", relief="flat")
        self.data_disp = ListDisplay(datafr)
        self.data_disp.pack(side=TOP, fill=BOTH, expand=1)
        self.data_disp.tag_config(
            'empty', foreground="gray50", font="Helvetica 12 italic")
        self.data_disp.tag_config(
            'gutter', background="gray75",
            foreground="black", font="Courier 12",
        )
        self.data_disp.tag_bind(
            'sitem', '<Double-Button-1>', self.handle_stack_item_dblclick)

        callfr = LabelFrame(panes2, text="Call Stack", relief="flat")
        self.call_disp = ListDisplay(callfr)
        self.call_disp.pack(side=TOP, fill=BOTH, expand=1)
        self.call_disp.tag_config(
            'empty', foreground="gray50", font="Helvetica 12 italic")

        varsfr = LabelFrame(panes2, text="Variables", relief="flat")
        self.vars_disp = ListDisplay(varsfr)
        self.vars_disp.pack(side=TOP, fill=BOTH, expand=1)
        self.vars_disp.tag_config(
            'gvar', foreground="#00f", font="Times")
        self.vars_disp.tag_config(
            'fvar', foreground="#090", font="Times")
        self.vars_disp.tag_config('gname', foreground="black")
        self.vars_disp.tag_config('fname', foreground="black")
        self.vars_disp.tag_config('eq', foreground="#777")
        self.vars_disp.tag_config('gval', foreground="#070")
        self.vars_disp.tag_config('fval', foreground="#070")
        self.vars_disp.tag_bind(
            'gname', '<Double-Button-1>', self.handle_vars_gname_dblclick)
        self.vars_disp.tag_bind(
            'fname', '<Double-Button-1>', self.handle_vars_fname_dblclick)
        self.vars_disp.tag_bind(
            'gval', '<Double-Button-1>', self.handle_vars_gname_dblclick)
        self.vars_disp.tag_bind(
            'fval', '<Double-Button-1>', self.handle_vars_fname_dblclick)

        panes2.add(datafr, minsize=100, height=200)
        panes2.add(callfr, minsize=100, height=200)
        panes2.add(varsfr, minsize=100, height=200)

        srcfr = Frame(panes3)

        srcselfr = Frame(srcfr)
        self.src_lbl = Label(srcselfr, text="Prog")
        self.src_sel = Menubutton(
            srcselfr, width=20,
            textvariable=self.current_program,
        )
        self.src_sel.menu = Menu(self.src_sel)
        self.src_sel['menu'] = self.src_sel.menu
        self.fun_lbl = Label(srcselfr, text="  Func")
        self.fun_sel = Menubutton(
            srcselfr, width=20,
            textvariable=self.current_function,
        )
        self.fun_sel.menu = Menu(self.fun_sel)
        self.fun_sel['menu'] = self.fun_sel.menu
        self.src_lbl.pack(side=LEFT, fill=NONE, expand=0)
        self.src_sel.pack(side=LEFT, fill=NONE, expand=0)
        self.fun_lbl.pack(side=LEFT, fill=NONE, expand=0)
        self.fun_sel.pack(side=LEFT, fill=NONE, expand=0)

        self.srcs_disp = ListDisplay(srcfr, font="Courier 12")
        self.srcs_disp.tag_config(
            'gutter', background="gray75", foreground="black")
        self.srcs_disp.tag_config(
            'currline', background="#77f", foreground="white")

        srcselfr.pack(side=TOP, fill=X, expand=0)
        self.srcs_disp.pack(side=BOTTOM, fill=BOTH, expand=1)

        tokfr = LabelFrame(panes3, text="Tokens", relief="flat")
        self.tokn_disp = ListDisplay(tokfr, font="Courier 12")
        self.tokn_disp.tag_config(
            'gutter', background="gray75", foreground="black")
        self.tokn_disp.tag_config(
            'func', foreground="#00c", font="Courier 12 bold")

        btnsfr = Frame(tokfr)
        self.stepi_btn = Button(
            btnsfr, text="Step Inst", command=self.handle_step_inst)
        self.stepl_btn = Button(
            btnsfr, text="Step Line", command=self.handle_step_line)
        self.nextl_btn = Button(
            btnsfr, text="Next Line", command=self.handle_next_line)
        self.finish_btn = Button(
            btnsfr, text="Finish", command=self.handle_finish)
        self.cont_btn = Button(
            btnsfr, text="Continue", command=self.handle_continue)
        self.rerun_btn = Button(
            btnsfr, text="Restart", command=self.handle_rerun)
        self.stepi_btn.pack(side=LEFT, fill=NONE, expand=0)
        self.stepl_btn.pack(side=LEFT, fill=NONE, expand=0)
        self.nextl_btn.pack(side=LEFT, fill=NONE, expand=0)
        self.finish_btn.pack(side=LEFT, fill=NONE, expand=0)
        self.cont_btn.pack(side=LEFT, fill=NONE, expand=0)
        self.rerun_btn.pack(side=LEFT, fill=NONE, expand=0)

        btnsfr.pack(side=BOTTOM, fill=X, expand=0)
        self.tokn_disp.pack(side=BOTTOM, fill=BOTH, expand=1)
        self.tokn_disp.tag_config(
            'currline', background="#77f", foreground="white")

        consfr = Frame(panes3)
        self.cons_disp = ListDisplay(consfr, height=1, font="Courier 12")
        self.cons_in = Entry(consfr, relief=SUNKEN)
        self.cons_disp.pack(side=TOP, fill=BOTH, expand=1)
        self.cons_in.pack(side=TOP, fill=X, expand=0)

        panes3.add(srcfr, minsize=100, height=350)
        panes3.add(tokfr, minsize=100, height=150)
        panes3.add(consfr, minsize=50, height=100)
        self.update_displays()

    def update_source_selectors(self):
        self.src_sel.menu.delete(0, END)
        if self.fr:
            addr = self.fr.curr_addr()
            progs = self.fr.get_programs()
            if not progs:
                self.current_program.set("- Load a Program -")
            for prog in progs:
                name = "%s(%s)" % (db.getobj(prog).name, prog)
                if addr and prog.value == addr.prog:
                    self.current_program.set(name)
                self.src_sel.menu.add_radiobutton(
                    label=name,
                    value=name,
                    variable=self.current_program,
                    foreground="black",
                    command=self.handle_source_selector_change,
                )
        self.src_sel.menu.add_separator()
        self.src_sel.menu.add_command(
            label="Load Program...",
            command=self.handle_load_program,
            foreground="black",
        )
        self.src_sel.menu.add_command(
            label="Load Library...",
            command=self.handle_load_library,
            foreground="black",
        )
        self.fun_sel.menu.delete(0, END)
        if self.fr:
            addr = self.fr.curr_addr()
            if not addr:
                return
            funs = self.fr.program_functions(addr.prog)
            if not funs:
                self.current_function.set("")
            else:
                currfun = self.fr.program_find_func(addr)
                self.current_function.set(currfun)
                for fun in funs:
                    self.fun_sel.menu.add_radiobutton(
                        label=fun,
                        value=fun,
                        variable=self.current_function,
                        foreground="black",
                        command=self.handle_function_selector_change,
                    )

    def update_data_stack_display(self):
        self.data_disp.delete('0.0', END)
        if not self.fr or not self.fr.data_stack:
            self.data_disp.insert('0.0', ' - EMPTY STACK - ', 'empty')
            return
        for i, val in enumerate(reversed(self.fr.data_stack)):
            repr = si.item_repr(val)
            line = '%4d' % (i+1,)
            self.data_disp.insert(END, line, 'gutter')
            line = ' %s\n' % repr
            self.data_disp.insert(END, line, 'sitem')
        self.data_disp.delete('end-1c', END)
        self.data_disp.see('0.0')

    def update_call_stack_display(self):
        fmt = "{progname}({prog}), {func}, L{line}\n"
        self.call_disp.delete('0.0', END)
        if not self.fr or not self.fr.get_call_stack():
            self.call_disp.insert('0.0', ' - NOT RUNNING - ', 'empty')
            return
        for callinfo in self.fr.get_call_stack():
            callinfo['progname'] = db.getobj(callinfo['prog']).name
            line = fmt.format(**callinfo)
            self.call_disp.insert(END, line)
        self.call_disp.delete('end-1c', END)
        self.call_disp.see('0.0')

    def update_variables_display(self):
        self.vars_disp.delete('0.0', END)
        addr = self.fr.curr_addr()
        if not addr:
            return
        gvars = self.fr.program_global_vars(addr.prog)
        cnt = 0
        for vnum, vname in enumerate(gvars):
            val = self.fr.globalvar_get(vnum)
            val = si.item_repr(val)
            self.vars_disp.insert(END, "G", 'gvar')
            self.vars_disp.insert(END, " ")
            self.vars_disp.insert(END, vname, 'gname')
            self.vars_disp.insert(END, " = ", 'eq')
            self.vars_disp.insert(END, val, 'gval')
            self.vars_disp.insert(END, "\n")
            cnt += 1
        fun = self.fr.program_find_func(addr)
        fvars = self.fr.program_func_vars(addr.prog, fun)
        for vnum, vname in enumerate(fvars):
            val = self.fr.funcvar_get(vnum)
            val = si.item_repr(val)
            self.vars_disp.insert(END, "F", 'fvar')
            self.vars_disp.insert(END, " ")
            self.vars_disp.insert(END, vname, 'fname')
            self.vars_disp.insert(END, " = ", 'eq')
            self.vars_disp.insert(END, val, 'fval')
            self.vars_disp.insert(END, "\n")
            cnt += 1
        self.vars_disp.delete('end-1c', END)
        self.vars_disp.see("%d.0" % cnt)

    def update_sourcecode_from_program(self, prog):
        if prog != self.prev_prog:
            srcs = self.fr.program_source_lines(prog)
            self.srcs_disp.delete('0.0', END)
            for i, srcline in enumerate(srcs):
                line = "%5d" % (i + 1)
                self.srcs_disp.insert(END, line, "gutter")
                line = " %s\n" % srcline
                self.srcs_disp.insert(END, line)
            self.srcs_disp.delete('end-1c', END)

            tokens = self.fr.program_tokens(prog)
            self.tokn_disp.delete('0.0', END)
            for i, token in enumerate(tokens):
                line = "%5d" % i
                self.tokn_disp.insert(END, line, "gutter")
                repr = token['repr']
                line = " %s\n" % repr
                if repr.startswith('Function:'):
                    self.tokn_disp.insert(END, line, "func")
                else:
                    self.tokn_disp.insert(END, line)
            self.tokn_disp.delete('end-1c', END)
            self.prev_prog = prog

    def handle_stack_item_dblclick(self, event):
        w = event.widget
        index = w.index("@%s,%s" % (event.x, event.y))
        rng = w.tag_prevrange('gutter', index)
        if rng and self.fr:
            item = int(w.get(*rng))
            val = self.fr.data_pick(item)
            val = si.item_repr_pretty(val)
            log("pick(%d) = %s" % (item, val))
            self.update_console_display()
            

    def handle_vars_gname_dblclick(self, event):
        w = event.widget
        index = w.index("@%s,%s" % (event.x, event.y))
        rng = w.tag_prevrange('gname', index + '+1c')
        if rng and self.fr:
            vname = w.get(*rng)
            # TODO: use addr from current selected call level
            addr = self.fr.curr_addr()
            vnum = self.fr.program_global_var(addr.prog, vname)
            val = self.fr.globalvar_get(vnum)
            val = si.item_repr_pretty(val)
            log("%s = %s" % (vname, val))
            self.update_console_display()

    def handle_vars_fname_dblclick(self, event):
        w = event.widget
        index = w.index("@%s,%s" % (event.x, event.y))
        rng = w.tag_prevrange('fname', index + '+1c')
        if rng:
            vname = w.get(*rng)
            # TODO: use addr from current selected call level
            addr = self.fr.curr_addr()
            fun = self.fr.program_find_func(addr)
            vnum = self.fr.program_func_var(addr.prog, fun, vname)
            # TODO: get var val from current selected call level
            val = self.fr.funcvar_get(vnum)
            val = si.item_repr_pretty(val)
            log("%s = %s" % (vname, val))
            self.update_console_display()

    def handle_source_selector_change(self):
        if not self.current_program.get().startswith('- '):
            prog = self.current_program.get()
            prog = prog.split('(#', 1)[1]
            prog = prog.split(')', 1)[0]
            prog = int(prog)
            self.update_sourcecode_from_program(prog)

    def handle_function_selector_change(self):
        if self.current_program.get().startswith('- '):
            return
        prog = self.current_program.get()
        prog = prog.split('(#', 1)[1]
        prog = prog.split(')', 1)[0]
        prog = int(prog)
        if not self.current_function.get():
            return
        fun = self.current_function.get()
        addr = self.fr.program_function_addr(prog, fun)
        line = self.fr.get_inst_line(addr)
        self.update_sourcecode_from_program(prog)
        self.srcs_disp.see('%d.0' % line)

    def update_sourcecode_display(self):
        if self.fr:
            self.srcs_disp.tag_remove('currline', '0.0', END)
            self.tokn_disp.tag_remove('currline', '0.0', END)
            addr = self.fr.curr_addr()
            if not addr:
                return
            inst = self.fr.curr_inst()
            self.update_sourcecode_from_program(addr.prog)
            self.srcs_disp.tag_add(
                'currline',
                '%d.5' % inst.line,
                '%d.end+1c' % inst.line,
            )
            self.tokn_disp.tag_add(
                'currline',
                '%d.5' % (addr.value + 1),
                '%d.end+1c' % (addr.value + 1),
            )
            self.srcs_disp.see('%d.0 - 2l' % inst.line)
            self.srcs_disp.see('%d.0 + 3l' % inst.line)
            self.srcs_disp.see('%d.0' % inst.line)
            self.tokn_disp.see('%d.0 - 2l' % (addr.value + 1))
            self.tokn_disp.see('%d.0 + 3l' % (addr.value + 1))
            self.tokn_disp.see('%d.0' % (addr.value + 1))

    def update_console_display(self):
        if log_updated():
            for line in get_log():
                self.cons_disp.insert(END, "\n")
                self.cons_disp.insert(END, line)
            clear_log()
            self.cons_disp.see('end linestart')

    def update_displays(self):
        self.update_source_selectors()
        self.update_console_display()
        self.update_call_stack_display()
        self.update_data_stack_display()
        if not self.fr:
            return
        self.update_variables_display()
        self.update_sourcecode_display()

    def reset_execution(self):
        userobj = db.get_player_obj("John_Doe")
        progobj = db.get_registered_obj(userobj, "$cmd/test")
        trigobj = db.get_registered_obj(userobj, "$testaction")
        self.fr = MufStackFrame()
        self.fr.setup(
            progobj,
            userobj,
            trigobj,
            self.command
        )

    def resume_execution(self):
        self.fr.execute_code()
        self.update_displays()

    def handle_step_inst(self):
        self.fr.set_break_insts(1)
        self.fr.set_break_steps(0)
        self.fr.set_break_lines(0)
        self.fr.set_break_on_finish(False)
        self.resume_execution()

    def handle_step_line(self):
        self.fr.set_break_insts(0)
        self.fr.set_break_steps(1)
        self.fr.set_break_lines(0)
        self.fr.set_break_on_finish(False)
        self.resume_execution()

    def handle_next_line(self):
        self.fr.set_break_insts(0)
        self.fr.set_break_steps(0)
        self.fr.set_break_lines(1)
        self.fr.set_break_on_finish(False)
        self.resume_execution()

    def handle_finish(self):
        self.fr.set_break_insts(0)
        self.fr.set_break_steps(0)
        self.fr.set_break_lines(0)
        self.fr.set_break_on_finish(True)
        self.resume_execution()

    def handle_continue(self):
        self.fr.set_break_insts(0)
        self.fr.set_break_steps(0)
        self.fr.set_break_lines(0)
        self.fr.set_break_on_finish(False)
        self.resume_execution()

    def handle_rerun(self):
        self.reset_execution()
        self.update_displays()

    def process_muv(self, infile):
        tmpfile = infile
        if tmpfile[-4:] == ".muv":
            tmpfile = tmpfile[:-1] + 'f'
        else:
            tmpfile += ".muf"
        retcode = call(["muv", "-o", tmpfile, infile], stderr=sys.stderr)
        if retcode != 0:
            log("MUV compilation failed!")
            return None
        log("MUV compilation successful.")
        log("------------------------------------------------------------")
        self.update_displays()
        return tmpfile

    def load_program_from_file(self, filename, regname=None):
        origfile = filename
        if filename.endswith(".muv"):
            filename = self.process_muv(filename)
        if not filename:
            return
        srcs = ""
        with open(filename, "r") as f:
            srcs = f.read()
        if origfile.endswith(".muv"):
            os.unlink(filename)
        userobj = db.get_player_obj("John_Doe")
        if regname:
            globenv = db.get_registered_obj(userobj, "$globalenv")
            progobj = db.DBObject(
                name=regname,
                objtype="program",
                flags="3",
                owner=userobj.dbref,
                location=userobj.dbref,
            )
            db.register_obj(globenv, regname, progobj)
            log("CREATED PROG %s, REGISTERED AS $%s\n" % (progobj, regname))
        else:
            progobj = db.get_registered_obj(userobj, "$cmd/test")
        progobj.sources = srcs
        success = MufCompiler().compile_source(progobj.dbref)
        if not success:
            log("MUF tokenization failed!")
            return None
        log("MUF tokenization successful.")
        log("------------------------------------------------------------")
        self.update_displays()
        self.reset_execution()

    def handle_load_program(self):
        filename = tkFileDialog.askopenfilename(
            parent=self.root,
            title="Load Program",
            message="Select a source file to load...",
            defaultextension=".muf",
            filetypes=[
                ('all files', '.*'),
                ('MUF files', '.muf'),
                ('MUF files', '.m'),
                ('MUV files', '.muv'),
            ],
        )
        if not filename:
            return
        self.prev_prog = -1
        self.fr = None
        self.update_displays()
        log("Loading program into cmd-test...")
        self.load_program_from_file(filename)
        self.update_displays()

    def handle_load_library(self):
        filename = tkFileDialog.askopenfilename(
            parent=self.root,
            title="Load Library",
            message="Select a library file to load...",
            defaultextension=".muf",
            filetypes=[
                ('all files', '.*'),
                ('MUF files', '.muf'),
                ('MUF files', '.m'),
                ('MUV files', '.muv'),
            ],
        )
        if not filename:
            return
        regname = os.path.basename(filename)
        if regname.endswith('.muv') or regname.endswith('.muf'):
            regname = regname[:-4]
        regname = tkSimpleDialog.askstring(
            "Library Name",
            "What should the library be registered as?",
            initialvalue=regname,
            parent=self.root,
        )
        if not regname:
            return
        self.prev_prog = -1
        self.fr = None
        self.update_displays()
        log("Loading library into $%s..." % regname)
        self.load_program_from_file(filename, regname=regname)
        self.update_displays()

    def destroy(self):
        self.root.destroy()

    def main(self):
        self.root.mainloop()
        try:
            self.root.destroy()
        except:
            pass


def main():
    MufGui().main()


if __name__ == "__main__":
    main()


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
