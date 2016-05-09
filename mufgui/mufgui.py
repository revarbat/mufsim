#!/usr/bin/env python3

import os
import platform
from subprocess import Popen, PIPE

try:  # Python 2
    from Tkinter import *  # noqa
    from tkFont import Font
    from tkSimpleDialog import askstring
    from tkFileDialog import askopenfilename
    from tkMessageBox import showinfo
    from ScrolledText import ScrolledText
except ImportError:  # Python 3
    from tkinter import *  # noqa
    from tkinter.simpledialog import askstring
    from tkinter.filedialog import askopenfilename
    from tkinter.messagebox import showinfo
    from tkinter.scrolledtext import ScrolledText
    from tkinter.font import Font

import mufsim.stackitems as si
import mufsim.gamedb as db
from mufsim.logger import log, warnlog, errlog, set_output_command
from mufsim.compiler import MufCompiler
from mufsim.stackframe import MufStackFrame

mufsim_version = None


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
        self.fr = None
        self.current_program = None
        self.call_level = 0
        self.prev_prog = -1
        self.setup_gui()

    def setup_gui(self):
        root = Tk()
        self.root = root

        self.current_program = StringVar()
        self.current_program.set("- Load a Program -")
        self.current_function = StringVar()
        self.current_function.set("")
        self.dotrace = StringVar()
        self.dotrace.set('0')

        root.title("MUF Debugger")
        root.protocol("WM_DELETE_WINDOW", self.destroy)
        root.option_add("*Menu.foreground", "black")
        root.option_add("*Menu.disabledForeground", "#bbb")
        root.option_add("*Panedwindow.sashWidth", "6")
        root.option_add("*Panedwindow.sashRelief", "raised")
        root.option_add("*Panedwindow.borderWidth", "1")
        root.option_add("*Background", "gray75")
        root.option_add("*Button.highlightBackground", "gray75")
        root.option_add("*Text.background", "white")
        root.option_add("*Text.highlightBackground", "white")
        root.option_add("*Entry.background", "white")
        root.option_add("*Entry.highlightBackground", "gray75")
        if platform.system() == 'Windows':
            root.option_add("*Menubutton.relief", "raised")
            monospace = Font(family="Menlo", size=10)
            monospace_b = Font(family="Menlo", size=10, weight="bold")
            seriffont = Font(family="Times", size=10)
            sansserif = Font(family="Arial", size=10)
            sansserif_i = Font(family="Arial", size=10, slant="italic")
        if platform.system() == 'Darwin':
            monospace = Font(family="Monaco", size=12)
            monospace_b = Font(family="Monaco", size=12, weight="bold")
            seriffont = Font(family="Times", size=12)
            sansserif = Font(family="Tahoma", size=12)
            sansserif_i = Font(family="Tahoma", size=12, slant="italic")
        else:
            monospace = Font(family="Courier", size=10)
            monospace_b = Font(family="Courier", size=10, weight="bold")
            seriffont = Font(family="Times", size=10)
            sansserif = Font(family="Helvetica", size=10)
            sansserif_i = Font(family="Helvetica", size=10, slant="italic")
        root.option_add("*Text.font", sansserif)

        self.menubar = Menu(self.root, name="mb", tearoff=0)

        cmd = "Control"
        if platform.system() == 'Darwin':
            cmd = "Command"
        self.filemenu = Menu(self.menubar, tearoff=0)
        self.filemenu.add_command(
            label="Load Program...",
            accel="%s-O" % cmd,
            command=self.handle_load_program,
        )
        self.filemenu.add_command(
            label="Load Library...",
            accel="%s-L" % cmd,
            command=self.handle_load_library,
        )
        if platform.system() == 'Windows':
            self.filemenu.add_separator()
            self.filemenu.add_command(
                label="Exit",
                accel="Alt-F4",
                command=self.destroy,
            )
        elif platform.system() == 'Linux':
            self.filemenu.add_separator()
            self.filemenu.add_command(
                label="Quit",
                accel="Control-Q",
                command=self.destroy,
            )
        self.menubar.add_cascade(label="File", menu=self.filemenu)

        self.editmenu = Menu(self.menubar, tearoff=0)
        self.editmenu.add_command(
            label="Cut",
            accel="%s-X" % cmd,
            command="event generate [focus] <<Cut>>"
        )
        self.editmenu.add_command(
            label="Copy",
            accel="%s-C" % cmd,
            command="event generate [focus] <<Copy>>"
        )
        self.editmenu.add_command(
            label="Paste",
            accel="%s-V" % cmd,
            command="event generate [focus] <<Paste>>"
        )
        self.editmenu.add_command(
            label="Clear",
            command="event generate [focus] <<Clear>>"
        )
        self.menubar.add_cascade(label="Edit", menu=self.editmenu)

        self.dbugmenu = Menu(self.menubar, tearoff=0)
        if platform.system() == 'Darwin':
            self.dbugmenu.add_command(
                label="Run...",
                accel="Control-r",
                state=DISABLED,
                command=self.handle_run,
            )
            self.dbugmenu.add_command(
                label="Step Instruction",
                accel="Control-i",
                state=DISABLED,
                command=self.handle_step_inst,
            )
            self.dbugmenu.add_command(
                label="Step Line",
                accel="Control-s",
                state=DISABLED,
                command=self.handle_step_line,
            )
            self.dbugmenu.add_command(
                label="Next Line",
                accel="Control-n",
                state=DISABLED,
                command=self.handle_next_line,
            )
            self.dbugmenu.add_command(
                label="Finish Function",
                accel="Control-f",
                state=DISABLED,
                command=self.handle_finish,
            )
            self.dbugmenu.add_command(
                label="Continue",
                accel="Control-c",
                state=DISABLED,
                command=self.handle_continue,
            )
        else:
            self.dbugmenu.add_command(
                label="Run...",
                accel="Control-Shift-R",
                state=DISABLED,
                command=self.handle_run,
            )
            self.dbugmenu.add_command(
                label="Step Instruction",
                accel="Control-Shift-I",
                state=DISABLED,
                command=self.handle_step_inst,
            )
            self.dbugmenu.add_command(
                label="Step Line",
                accel="Control-Shift-S",
                state=DISABLED,
                command=self.handle_step_line,
            )
            self.dbugmenu.add_command(
                label="Next Line",
                accel="Control-Shift-N",
                state=DISABLED,
                command=self.handle_next_line,
            )
            self.dbugmenu.add_command(
                label="Finish Function",
                accel="Control-Shift-F",
                state=DISABLED,
                command=self.handle_finish,
            )
            self.dbugmenu.add_command(
                label="Continue",
                accel="Control-Shift-C",
                state=DISABLED,
                command=self.handle_continue,
            )
        self.menubar.add_cascade(label="Debug", menu=self.dbugmenu)

        self.helpmenu = Menu(self.menubar, name="help", tearoff=0)
        self.menubar.add_cascade(label="Help", menu=self.helpmenu)

        self.root['menu'] = self.menubar

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
            'empty', foreground="gray50", font=sansserif_i)
        self.data_disp.tag_config(
            'gutter', background="gray75",
            foreground="black", font=monospace,
        )
        self.data_disp.tag_bind(
            'sitem', '<Double-Button-1>', self.handle_stack_item_dblclick)

        callfr = LabelFrame(panes2, text="Call Stack", relief="flat")
        self.call_disp = ListDisplay(callfr)
        self.call_disp.pack(side=TOP, fill=BOTH, expand=1)
        self.call_disp.tag_config(
            'empty', foreground="gray50", font=sansserif_i)
        self.call_disp.tag_config(
            'gutter', background="gray75",
            foreground="black", font=monospace,
        )
        self.call_disp.tag_bind(
            'callfr', '<Button-1>', self.handle_call_stack_click)
        self.call_disp.tag_config(
            'currline', background="#77f", foreground="white")

        varsfr = LabelFrame(panes2, text="Variables", relief="flat")
        self.vars_disp = ListDisplay(varsfr)
        self.vars_disp.pack(side=TOP, fill=BOTH, expand=1)
        self.vars_disp.tag_config(
            'gvar', foreground="#00f", font=seriffont)
        self.vars_disp.tag_config(
            'fvar', foreground="#090", font=seriffont)
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
        self.src_sel.menu = Menu(self.src_sel, tearoff=0)
        self.src_sel['menu'] = self.src_sel.menu
        self.fun_lbl = Label(srcselfr, text="  Func")
        self.fun_sel = Menubutton(
            srcselfr, width=20,
            textvariable=self.current_function,
        )
        self.fun_sel.menu = Menu(self.fun_sel, tearoff=0)
        self.fun_sel['menu'] = self.fun_sel.menu
        self.src_lbl.pack(side=LEFT, fill=NONE, expand=0)
        self.src_sel.pack(side=LEFT, fill=NONE, expand=0)
        self.fun_lbl.pack(side=LEFT, fill=NONE, expand=0)
        self.fun_sel.pack(side=LEFT, fill=NONE, expand=0)

        self.srcs_disp = ListDisplay(srcfr, font=monospace)
        self.srcs_disp.tag_config(
            'breakpt', background="#f77", foreground="black")
        self.srcs_disp.tag_config(
            'gutter', background="gray75", foreground="black")
        self.srcs_disp.tag_raise('breakpt', aboveThis='gutter')
        self.srcs_disp.tag_bind(
            'gutter', '<Button-1>', self.handle_sources_breakpoint_toggle)
        self.srcs_disp.tag_config(
            'currline', background="#77f", foreground="white")

        srcselfr.pack(side=TOP, fill=X, expand=0)
        self.srcs_disp.pack(side=BOTTOM, fill=BOTH, expand=1)

        tokfr = LabelFrame(panes3, text="Tokens", relief="flat")
        self.tokn_disp = ListDisplay(tokfr, font=monospace)
        self.tokn_disp.tag_config(
            'gutter', background="gray75", foreground="black")
        self.tokn_disp.tag_config(
            'func', foreground="#00c", font=monospace_b)

        btnsfr = Frame(tokfr)
        self.run_btn = Button(
            btnsfr, text="Run", command=self.handle_run)
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
        self.trace_chk = Checkbutton(
            btnsfr, text="Trace",
            variable=self.dotrace,
            onvalue='1',
            offvalue='0',
            command=self.handle_trace,
        )
        self.run_btn.pack(side=LEFT, fill=NONE, expand=0)
        self.stepi_btn.pack(side=LEFT, fill=NONE, expand=0)
        self.stepl_btn.pack(side=LEFT, fill=NONE, expand=0)
        self.nextl_btn.pack(side=LEFT, fill=NONE, expand=0)
        self.finish_btn.pack(side=LEFT, fill=NONE, expand=0)
        self.cont_btn.pack(side=LEFT, fill=NONE, expand=0)
        self.trace_chk.pack(side=LEFT, fill=NONE, expand=0)

        btnsfr.pack(side=BOTTOM, fill=X, expand=0)
        self.tokn_disp.pack(side=BOTTOM, fill=BOTH, expand=1)
        self.tokn_disp.tag_config(
            'currline', background="#77f", foreground="white")

        consfr = Frame(panes3)
        self.cons_disp = ListDisplay(consfr, height=1, font=monospace)
        self.cons_in = Entry(consfr, relief=SUNKEN)
        self.cons_disp.pack(side=TOP, fill=BOTH, expand=1)
        self.cons_in.pack(side=TOP, fill=X, expand=0)
        self.cons_disp.tag_config('good', foreground="#0a0")
        self.cons_disp.tag_config('trace', foreground="#777")
        self.cons_disp.tag_config('warning', foreground="#880")
        self.cons_disp.tag_config('error', foreground="#c00")

        panes3.add(srcfr, minsize=100, height=350)
        panes3.add(tokfr, minsize=100, height=150)
        panes3.add(consfr, minsize=50, height=100)

        set_output_command(self.log_to_console)

        try:
            root.tk.call('console', 'hide')
        except TclError:
            # Some versions of the Tk framework don't have a console object
            pass

        if platform.system() == 'Darwin':
            # root.createcommand(
            #     '::tk::mac::ShowPreferences', self.handle_prefs_dlog)
            root.createcommand('tk::mac::ShowHelp', self.handle_help_dlog)
            root.createcommand('tkAboutDialog', self.handle_about_dlog)
            root.createcommand(
                "::tk::mac::OpenDocument", self.handle_open_files)
            if "MufSim.app/Contents/Resources" in os.getcwd():
                appname = "MufSim"
            else:
                appname = "Python"
            ascript = (
                'tell app "Finder" to set frontmost of process "%s" to true' %
                appname
            )
            os.system("/usr/bin/osascript -e '%s' " % ascript)
        else:
            root.lift()
            root.call('wm', 'attributes', '.', '-topmost', True)
            root.after_idle(
                root.call, 'wm', 'attributes', '.', '-topmost', False)

        if platform.system() == 'Darwin':
            self.root.bind_all('<Command-Key-o>', self.handle_load_program)
            self.root.bind_all('<Command-Key-l>', self.handle_load_library)
            self.root.bind_all('<Command-Key-x>', "event generate [focus] <<Cut>>")
            self.root.bind_all('<Command-Key-c>', "event generate [focus] <<Copy>>")
            self.root.bind_all('<Command-Key-v>', "event generate [focus] <<Paste>>")
            self.root.bind_all('<Control-Key-r>', lambda e: root.after(100, self.handle_run))
            self.root.bind_all('<Control-Key-i>', self.handle_step_inst)
            self.root.bind_all('<Control-Key-s>', self.handle_step_line)
            self.root.bind_all('<Control-Key-n>', self.handle_next_line)
            self.root.bind_all('<Control-Key-f>', self.handle_finish)
            self.root.bind_all('<Control-Key-c>', self.handle_continue)
        else:
            self.root.bind_all('<Control-Key-o>', self.handle_load_program)
            self.root.bind_all('<Control-Key-l>', self.handle_load_library)
            self.root.bind_all('<Control-Key-x>', "event generate [focus] <<Cut>>")
            self.root.bind_all('<Control-Key-c>', "event generate [focus] <<Copy>>")
            self.root.bind_all('<Control-Key-v>', "event generate [focus] <<Paste>>")
            self.root.bind_all('<Control-Key-r>', lambda e: root.after(100, self.handle_run))
            self.root.bind_all('<Shift-Control-Key-I>', self.handle_step_inst)
            self.root.bind_all('<Shift-Control-Key-S>', self.handle_step_line)
            self.root.bind_all('<Shift-Control-Key-N>', self.handle_next_line)
            self.root.bind_all('<Shift-Control-Key-F>', self.handle_finish)
            self.root.bind_all('<Shift-Control-Key-C>', self.handle_continue)

        self.update_displays()

        if len(sys.argv) > 1:
            root.after(100, self.handle_open_files, sys.argv[1])

    def handle_help_dlog(self):
        # TODO: implement!
        print("Display help dlog.")

    def handle_prefs_dlog(self):
        # TODO: implement!
        print("Display preferences dlog.")

    def handle_about_dlog(self):
        global mufsim_version
        if platform.system() == 'Darwin' and not mufsim_version:
            if "MufSim.app/Contents/Resources" in os.getcwd():
                from plistlib import Plist
                print(os.getcwd())
                plist = Plist.fromFile(os.path.join('..', 'Info.plist'))
                mufsim_version = plist['CFBundleShortVersionString']
        if mufsim_version is None:
            mufsim_version = ""
        showinfo(
            "About MufSimulator",
            "MufSimulator %s\nCopyright 2016\nRevar Desmera" % mufsim_version,
            parent=self.root,
        )

    def handle_open_files(self, *files):
        for file in files:
            self.load_program_from_file(file)

    def update_source_selectors(self):
        self.src_sel.menu.delete(0, END)
        currprog = -1
        progs = db.get_all_programs()
        if not progs:
            self.current_program.set("- Load a Program -")
        else:
            currprog = progs[0].value
        for prog in progs:
            name = "%s(%s)" % (db.getobj(prog).name, prog)
            self.src_sel.menu.add_radiobutton(
                label=name,
                value=name,
                variable=self.current_program,
                command=self.handle_source_selector_change,
            )
            if self.fr:
                addr = self.fr.call_addr(self.call_level)
                if addr and prog.value == addr.prog:
                    currprog = prog.value
                    self.current_program.set(name)
            elif prog == progs[0]:
                self.current_program.set(name)
        self.src_sel.menu.add_separator()
        self.src_sel.menu.add_command(
            label="Load Program...",
            command=self.handle_load_program,
        )
        self.src_sel.menu.add_command(
            label="Load Library...",
            command=self.handle_load_library,
        )
        self.fun_sel.menu.delete(0, END)
        funs = []
        comp = db.getobj(currprog).compiled
        currfun = ""
        if comp:
            funs = comp.get_functions()
            currfun = funs[0]
        if self.fr:
            addr = self.fr.call_addr(self.call_level)
            if addr:
                funs = self.fr.program_functions(addr.prog)
                currfun = self.fr.program_find_func(addr)
        if not funs:
            self.current_function.set("")
        else:
            self.current_function.set(currfun)
            for fun in funs:
                self.fun_sel.menu.add_radiobutton(
                    label=fun,
                    value=fun,
                    variable=self.current_function,
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
        self.call_disp.tag_remove('currline', '0.0', END)
        fmt = " {progname}({prog}), {func}, {line}\n"
        self.call_disp.delete('0.0', END)
        if not self.fr or not self.fr.get_call_stack():
            self.call_disp.insert('0.0', ' - NOT RUNNING - ', 'empty')
            return
        for callinfo in self.fr.get_call_stack():
            callinfo['progname'] = db.getobj(callinfo['prog']).name
            line = "%4d" % callinfo['level']
            self.call_disp.insert(END, line, 'gutter')
            line = fmt.format(**callinfo)
            self.call_disp.insert(END, line, 'callfr')
        self.call_disp.tag_add(
            'currline',
            '%d.4' % (self.call_level + 1),
            '%d.end+1c' % (self.call_level + 1),
        )
        self.call_disp.see('0.0')

    def update_variables_display(self):
        self.vars_disp.delete('0.0', END)
        if not self.fr:
            return
        addr = self.fr.call_addr(self.call_level)
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
            if not db.validobj(prog):
                return
            self.prev_prog = prog
            progobj = db.getobj(prog)
            srcs = []
            if progobj.sources:
                srcs = progobj.sources.split("\n")
            self.srcs_disp.delete('0.0', END)
            for i, srcline in enumerate(srcs):
                line = "%5d" % (i + 1)
                self.srcs_disp.insert(END, line, "gutter")
                line = " %s\n" % srcline
                self.srcs_disp.insert(END, line)
            self.srcs_disp.delete('end-1c', END)

            tokens = []
            if progobj.compiled:
                tokens = progobj.compiled.get_tokens_info()
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

    def handle_call_stack_click(self, event):
        w = event.widget
        index = w.index("@%s,%s" % (event.x, event.y))
        level = int(index.split('.')[0]) - 1
        self.update_displays(level=level)

    def handle_stack_item_dblclick(self, event):
        w = event.widget
        index = w.index("@%s,%s" % (event.x, event.y))
        rng = w.tag_prevrange('gutter', index)
        if rng and self.fr:
            item = int(w.get(*rng))
            val = self.fr.data_pick(item)
            val = si.item_repr_pretty(val)
            log("pick(%d) = %s" % (item, val))

    def handle_vars_gname_dblclick(self, event):
        w = event.widget
        index = w.index("@%s,%s" % (event.x, event.y))
        rng = w.tag_prevrange('gname', index + '+1c')
        if rng and self.fr:
            vname = w.get(*rng)
            addr = self.fr.call_addr(self.call_level)
            vnum = self.fr.program_global_var(addr.prog, vname)
            val = self.fr.globalvar_get(vnum)
            val = si.item_repr_pretty(val)
            log("%s = %s" % (vname, val))

    def handle_vars_fname_dblclick(self, event):
        w = event.widget
        index = w.index("@%s,%s" % (event.x, event.y))
        rng = w.tag_prevrange('fname', index + '+1c')
        if rng:
            vname = w.get(*rng)
            addr = self.fr.call_addr(self.call_level)
            fun = self.fr.program_find_func(addr)
            vnum = self.fr.program_func_var(addr.prog, fun, vname)
            val = self.fr.funcvar_get(vnum, self.call_level)
            val = si.item_repr_pretty(val)
            log("%s = %s" % (vname, val))

    def _get_prog_from_selector(self):
        if self.current_program.get().startswith('- '):
            return None
        prog = self.current_program.get()
        prog = prog.split('(#', 1)[1]
        prog = prog.split(')', 1)[0]
        return int(prog)

    def handle_source_selector_change(self):
        prog = self._get_prog_from_selector()
        if prog is not None:
            self.update_sourcecode_from_program(prog)

    def handle_function_selector_change(self):
        prog = self._get_prog_from_selector()
        if prog is None:
            return
        if not self.current_function.get():
            return
        fun = self.current_function.get()
        addr = self.fr.program_function_addr(prog, fun)
        line = self.fr.get_inst_line(addr)
        self.update_sourcecode_from_program(prog)
        self.srcs_disp.see('%d.0' % line)
        self.tokn_disp.see('%d.0' % (addr.value + 1))

    def handle_sources_breakpoint_toggle(self, event):
        w = event.widget
        index = w.index("@%s,%s" % (event.x, event.y))
        line = int(index.split('.')[0])
        prog = self._get_prog_from_selector()
        if prog is None:
            return
        bpnum = self.fr.find_breakpoint(prog, line)
        if bpnum is not None:
            self.fr.del_breakpoint(bpnum)
        else:
            self.fr.add_breakpoint(prog, line)
        self.update_sourcecode_breakpoints(prog)

    def update_sourcecode_breakpoints(self, prog):
        self.srcs_disp.tag_remove('breakpt', '0.0', END)
        for bpprog, line in self.fr.get_breakpoints():
            if bpprog == prog:
                self.srcs_disp.tag_add(
                    'breakpt',
                    '%d.0' % line,
                    '%d.5' % line
                )

    def update_sourcecode_display(self):
        self.srcs_disp.tag_remove('currline', '0.0', END)
        self.tokn_disp.tag_remove('currline', '0.0', END)
        selprog = self._get_prog_from_selector()
        addr = None
        if self.fr:
            addr = self.fr.call_addr(self.call_level)
            if addr:
                selprog = addr.prog
        if selprog is None:
            selprog = db.get_registered_obj(userobj, "$cmd/test")
        self.update_sourcecode_from_program(selprog)
        if not self.fr:
            return
        if not addr:
            return
        inst = self.fr.get_inst(addr)
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
        self.update_sourcecode_breakpoints(selprog)
        self.srcs_disp.see('%d.0 - 2l' % inst.line)
        self.srcs_disp.see('%d.0 + 2l' % inst.line)
        self.srcs_disp.see('%d.0' % inst.line)
        self.tokn_disp.see('%d.0 - 1l' % (addr.value + 1))
        self.tokn_disp.see('%d.0 + 1l' % (addr.value + 1))
        self.tokn_disp.see('%d.0' % (addr.value + 1))

    def update_buttonbar(self):
        livebtns = [
            self.stepi_btn,
            self.stepl_btn,
            self.nextl_btn,
            self.finish_btn,
            self.cont_btn,
        ]
        livestate = "disabled"
        if self.fr and self.fr.get_call_stack():
            livestate = "normal"
        runstate = "normal" if self.fr else "disabled"
        for btn in livebtns:
            btn.config(state=livestate)
        self.run_btn.config(state=runstate)
        self.dbugmenu.entryconfig(0, state=runstate)
        for i in range(1, 6):
            self.dbugmenu.entryconfig(i, state=livestate)

    def log_to_console(self, msgtype, msg):
        self.cons_disp.insert(END, msg + "\n", msgtype)
        self.cons_disp.see('end linestart')

    def update_displays(self, level=-1):
        if self.fr and level < 0:
            level = len(self.fr.get_call_stack()) + level
        self.call_level = level
        self.update_buttonbar()
        self.update_source_selectors()
        self.update_call_stack_display()
        self.update_data_stack_display()
        if not self.fr:
            return
        self.update_variables_display()
        self.update_sourcecode_display()

    def reset_execution(self, command=""):
        # db.init_object_db()
        userobj = db.get_player_obj("John_Doe")
        progobj = db.get_registered_obj(userobj, "$cmd/test")
        trigobj = db.get_registered_obj(userobj, "$testaction")
        breakpts = []
        if self.fr:
            breakpts = self.fr.breakpoints
        self.fr = MufStackFrame()
        self.fr.set_trace(self.dotrace.get() != '0')
        self.fr.breakpoints = breakpts
        self.fr.setup(progobj, userobj, trigobj, command)

    def handle_reads(self):
        self.update_displays()
        readline = askstring(
            "MUF Read Requested",
            "Enter text to satisfy the READ request.",
            initialvalue="",
            parent=self.root,
        )
        if readline is None or readline == "@Q":
            while self.fr.call_stack:
                self.fr.call_pop()
            while self.fr.catch_stack:
                self.fr.catch_pop()
            warnlog("Aborting program.")
            return False
        if not readline and not self.fr.read_wants_blanks:
            warnlog("Blank line ignored.")
            return True
        self.fr.pc_advance(1)
        if self.fr.wait_state == self.fr.WAIT_READ:
            self.fr.data_push(readline)
        elif readline == "@T":
            warnlog("Faking time-out.")
            self.fr.data_push("")
            self.fr.data_push(1)
        else:
            self.fr.data_push(readline)
            self.fr.data_push(0)
        return True

    def resume_execution(self):
        while True:
            self.fr.execute_code(self.call_level)
            if not self.fr.get_call_stack():
                warnlog("Program exited.")
                break
            if self.fr.wait_state in [
                self.fr.WAIT_READ, self.fr.WAIT_TREAD
            ] and self.handle_reads():
                continue
            break
        self.update_displays()

    def handle_step_inst(self, event=None):
        self.fr.set_break_insts(1)
        self.resume_execution()

    def handle_step_line(self, event=None):
        self.fr.set_break_steps(1)
        self.resume_execution()

    def handle_next_line(self, event=None):
        self.fr.set_break_lines(1)
        self.resume_execution()

    def handle_finish(self, event=None):
        self.fr.set_break_on_finish(True)
        self.resume_execution()

    def handle_continue(self, event=None):
        self.fr.reset_breaks()
        self.resume_execution()

    def handle_run(self, event=None):
        command = askstring(
            "Run program",
            "What argument string should the program be run with?",
            initialvalue="",
            parent=self.root,
        )
        if command is None:
            return
        self.reset_execution(command)
        self.update_displays()

    def handle_trace(self, event=None):
        if self.fr:
            self.fr.set_trace(self.dotrace.get() != '0')

    def process_muv(self, infile):
        tmpfile = infile
        if tmpfile[-4:] == ".muv":
            tmpfile = tmpfile[:-1] + 'f'
        else:
            tmpfile += ".muf"
        if "MufSim.app/Contents/Resources" in os.getcwd():
            muvdir = os.path.join(os.getcwd(), "muv")
            cmdarr = [
                os.path.join(muvdir, "muv"),
                "-I", os.path.join(muvdir, "incls"),
                "-o", tmpfile,
                infile
            ]
        else:
            cmdarr = ["muv", "-o", tmpfile, infile]
        p = Popen(cmdarr, stdout=PIPE, stderr=PIPE)
        outdata, errdata = p.communicate()
        for line in outdata.split("\n"):
            if line:
                log(line)
        for line in errdata.split("\n"):
            if line:
                errlog(line)
        if p.returncode != 0:
            errlog("MUV compilation failed!")
            return None
        log("MUV compilation successful.", msgtype="good")
        return tmpfile

    def load_program_from_file(self, filename, regname=None):
        self.cons_disp.delete('0.0', END)
        if regname:
            log("Loading library into $%s..." % regname)
        else:
            log("Loading program into $cmd/test...")
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
                name=os.path.basename(filename),
                objtype="program",
                flags="3",
                owner=userobj.dbref,
                location=userobj.dbref,
            )
            db.register_obj(globenv, regname, progobj)
            log("CREATED PROG %s, REGISTERED AS $%s\n" % (progobj, regname))
        else:
            progobj = db.get_registered_obj(userobj, "$cmd/test")
            progobj.name = os.path.basename(filename)
        progobj.sources = srcs
        success = MufCompiler().compile_source(progobj.dbref)
        self.prev_prog = -1
        self.fr = None
        self.update_sourcecode_from_program(progobj.dbref)
        if not success:
            errlog("MUF tokenization failed!")
            self.update_displays()
            return None
        log("MUF tokenization successful.", msgtype="good")
        self.reset_execution()
        self.update_displays()
        self.fr.call_stack = []
        self.update_displays()

    def handle_load_program(self, event=None):
        extras = {}
        if platform.system() == 'Darwin':
            extras = dict(
                message="Select a source file to load...",
            )
        filename = askopenfilename(
            parent=self.root,
            title="Load Program",
            defaultextension=".muf",
            filetypes=[
                ('all files', '.*'),
                ('MUF files', '.muf'),
                ('MUF files', '.m'),
                ('MUV files', '.muv'),
            ],
            **extras
        )
        if not filename:
            return
        self.load_program_from_file(filename)

    def handle_load_library(self, event=None):
        extras = {}
        if platform.system() == 'Darwin':
            extras = dict(
                message="Select a library file to load...",
            )
        filename = askopenfilename(
            parent=self.root,
            title="Load Library",
            defaultextension=".muf",
            filetypes=[
                ('all files', '.*'),
                ('MUF files', '.muf'),
                ('MUF files', '.m'),
                ('MUV files', '.muv'),
            ],
            **extras
        )
        if not filename:
            return
        regname = os.path.basename(filename)
        if regname.endswith('.muv') or regname.endswith('.muf'):
            regname = regname[:-4]
        regname = askstring(
            "Library Name",
            "What should the library be registered as?",
            initialvalue=regname,
            parent=self.root,
        )
        if not regname:
            return
        self.load_program_from_file(filename, regname=regname)

    def destroy(self):
        self.root.destroy()

    def main(self):
        self.root.mainloop()
        try:
            self.root.destroy()
        except:
            pass


def main():
    try:
        MufGui().main()
    except Exception as e:
        print(e)


if __name__ == "__main__":
    main()


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
