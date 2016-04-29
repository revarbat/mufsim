#!/usr/bin/env python

import os
from subprocess import call
from Tkinter import *
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


class ReadOnlyText(Text):
    def __init__(self, *args, **kwargs):
        if 'insertontime' not in kwargs:
            kwargs['insertontime'] = 0
        if 'borderwidth' not in kwargs:
            kwargs['borderwidth'] = 1
        if 'highlightthickness' not in kwargs:
            kwargs['highlightthickness'] = 0
        Text.__init__(self, *args, **kwargs)
        self.bind("<Key>", lambda e: "break")
        self.bind("<<Paste>>", lambda e: "break")


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
        self.program_list = ["cmd-test(#5)", "lib-test(#8)", "lib-zany(#9)"]
        # TODO: get real command
        self.command = "me=test"
        self.fr = None
        self.current_program = None
        self.open_file('/Volumes/ThumbDrive/mufsim/tests/lsedit.muv')
        self.setup_gui()

    def setup_gui(self):
        root = Tk()
        self.root = root

        self.current_program = StringVar()
        self.current_program.set(self.program_list[0])
        self.current_function = StringVar()
        self.current_function.set("foobar")

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

        callfr = LabelFrame(panes2, text="Call Stack", relief="flat")
        self.call_disp = ListDisplay(callfr)
        self.call_disp.pack(side=TOP, fill=BOTH, expand=1)

        varsfr = LabelFrame(panes2, text="Variables", relief="flat")
        self.vars_disp = ListDisplay(varsfr)
        self.vars_disp.pack(side=TOP, fill=BOTH, expand=1)

        panes2.add(datafr, minsize=100, height=200)
        panes2.add(callfr, minsize=100, height=200)
        panes2.add(varsfr, minsize=100, height=200)

        srcfr = Frame(panes3)

        srcselfr = Frame(srcfr)
        self.src_lbl = Label(srcselfr, text="Program:")
        self.src_sel = Menubutton(
            srcselfr,
            textvariable=self.current_program,
        )
        self.src_sel.menu = Menu(self.src_sel)
        self.src_sel['menu'] = self.src_sel.menu
        self.fun_lbl = Label(srcselfr, text="    Function:")
        self.fun_sel = Menubutton(
            srcselfr,
            textvariable=self.current_function,
        )
        self.fun_sel.menu = Menu(self.fun_sel)
        self.fun_sel['menu'] = self.fun_sel.menu
        self.src_lbl.pack(side=LEFT, fill=NONE, expand=0)
        self.src_sel.pack(side=LEFT, fill=NONE, expand=0)
        self.fun_lbl.pack(side=LEFT, fill=NONE, expand=0)
        self.fun_sel.pack(side=LEFT, fill=NONE, expand=0)

        self.srcs_disp = ListDisplay(srcfr, font="Courier")

        srcbtnsfr = Frame(srcfr)
        self.step_btn = Button(
            srcbtnsfr, text="Step", command=self.handle_step)
        self.next_btn = Button(
            srcbtnsfr, text="Next", command=self.handle_next)
        self.finish_btn = Button(
            srcbtnsfr, text="Finish", command=self.handle_finish)
        self.cont_btn = Button(
            srcbtnsfr, text="Continue", command=self.handle_continue)
        self.rerun_btn = Button(
            srcbtnsfr, text="Restart", command=self.handle_rerun)
        self.step_btn.pack(side=LEFT, fill=NONE, expand=0)
        self.next_btn.pack(side=LEFT, fill=NONE, expand=0)
        self.finish_btn.pack(side=LEFT, fill=NONE, expand=0)
        self.cont_btn.pack(side=LEFT, fill=NONE, expand=0)
        self.rerun_btn.pack(side=LEFT, fill=NONE, expand=0)

        srcselfr.pack(side=TOP, fill=X, expand=0)
        srcbtnsfr.pack(side=BOTTOM, fill=X, expand=0)
        self.srcs_disp.pack(side=BOTTOM, fill=BOTH, expand=1)

        consfr = Frame(panes3)
        self.cons_disp = ListDisplay(consfr, height=1)
        self.cons_in = Entry(consfr, relief=SUNKEN)
        self.cons_disp.pack(side=TOP, fill=BOTH, expand=1)
        self.cons_in.pack(side=TOP, fill=X, expand=0)

        panes3.add(srcfr, minsize=100, height=450)
        panes3.add(consfr, minsize=50, height=100)
        self.update_displays()

    def update_program_selector(self):
        self.src_sel.menu.delete(0, END)
        for item in self.program_list:
            self.src_sel.menu.add_radiobutton(
                label=item,
                value=item,
                variable=self.current_program,
                foreground="black",
            )

    def update_call_stack_display(self):
        fmt = "{progname}({prog}), {func}, L{line}\n"
        self.call_disp.delete('0.0', END)
        for callinfo in self.fr.get_call_stack():
            callinfo['progname'] = db.getobj(callinfo['prog']).name
            line = fmt.format(**callinfo)
            self.call_disp.insert('0.0', line)
        self.call_disp.delete('end-1c', END)
        self.call_disp.see('0.0')

    def update_data_stack_display(self):
        self.data_disp.delete('0.0', END)
        self.data_disp.tag_config(
            'empty', foreground="gray50", font="Helvetica 12 italic"
        )
        self.data_disp.tag_config(
            'gutter', background="gray75",
            foreground="black", font="Courier",
        )
        if not self.fr.data_stack:
            self.data_disp.insert('0.0', ' - EMPTY STACK - ', 'empty')
        for i, val in enumerate(self.fr.data_stack):
            self.data_disp.insert('0.0', ' %s\n' % si.item_repr(val))
            self.data_disp.insert('0.0', '%4d' % i, 'gutter')
        self.data_disp.delete('end-1c', END)
        self.data_disp.see('0.0')

    def update_variables_display(self):
        addr = self.fr.curr_addr()
        gvars = self.fr.program_global_vars(addr.prog)
        self.vars_disp.delete('0.0', END)
        self.vars_disp.tag_config(
            'gvar', foreground="#00f", font="Times"
        )
        self.vars_disp.tag_config(
            'fvar', foreground="#090", font="Times"
        )
        self.vars_disp.tag_config('gname', foreground="black")
        self.vars_disp.tag_config('fname', foreground="black")
        self.vars_disp.tag_config('eq', foreground="#777")
        self.vars_disp.tag_config('val', foreground="#070")
        cnt = 0
        for vnum, vname in enumerate(gvars):
            val = self.fr.globalvar_get(vnum)
            val = si.item_repr(val)
            self.vars_disp.insert(END, "G", 'gvar')
            self.vars_disp.insert(END, " ")
            self.vars_disp.insert(END, vname, 'gname')
            self.vars_disp.insert(END, " = ", 'eq')
            self.vars_disp.insert(END, val, 'val')
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
            self.vars_disp.insert(END, val, 'val')
            self.vars_disp.insert(END, "\n")
            cnt += 1
        self.vars_disp.delete('end-1c', END)
        self.vars_disp.see("%d.0" % cnt)

    def update_sourcecode_display(self):
        addr = self.fr.curr_addr()
        inst = self.fr.curr_inst()
        currprog = self.current_program.get()
        currprog = currprog.split('(#', 1)[1]
        currprog = currprog.split(')', 1)[0]
        currprog = int(currprog)
        if addr.prog != currprog:
            srcs = self.fr.program_source_lines(addr.prog)
            self.srcs_disp.delete('0.0', END)
            self.srcs_disp.tag_config(
                'gutter', background="gray75", foreground="black")
            self.srcs_disp.tag_config(
                'currline', background="#77f", foreground="white")
            for i, srcline in enumerate(srcs):
                line = " % 4d" % (i + 1)
                self.srcs_disp.insert(END, line, "gutter")
                line = " %s\n" % srcline
                if inst.line == i + 1:
                    self.srcs_disp.insert(END, line, "currline")
                else:
                    self.srcs_disp.insert(END, line)
            self.srcs_disp.delete('end-1c', END)
        self.srcs_disp.see('%d.0' % inst.line)

    def update_console_display(self):
        if log_updated():
            for line in get_log():
                self.cons_disp.insert(END, "\n")
                self.cons_disp.insert(END, line)
            clear_log()
            self.cons_disp.see('end linestart')

    def update_displays(self):
        if not self.fr:
            return
        self.update_program_selector()
        self.update_call_stack_display()
        self.update_data_stack_display()
        self.update_variables_display()
        self.update_sourcecode_display()
        self.update_console_display()

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

    def handle_step(self):
        self.fr.set_break_steps(1)
        self.fr.set_break_lines(0)
        self.fr.set_break_on_finish(False)
        self.resume_execution()

    def handle_next(self):
        self.fr.set_break_steps(0)
        self.fr.set_break_lines(1)
        self.fr.set_break_on_finish(False)
        self.resume_execution()

    def handle_finish(self):
        self.fr.set_break_steps(0)
        self.fr.set_break_lines(0)
        self.fr.set_break_on_finish(True)
        self.resume_execution()

    def handle_continue(self):
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
        return tmpfile

    def open_file(self, filename):
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
        progobj = db.get_registered_obj(userobj, "$cmd/test")
        progobj.sources = srcs
        success = MufCompiler().compile_source(progobj.dbref)
        if not success:
            log("MUF tokenization failed!")
            return None
        log("MUF tokenization successful.")
        log("------------------------------------------------------------")
        self.reset_execution()

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
