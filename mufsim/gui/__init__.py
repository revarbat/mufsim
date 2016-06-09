#!/usr/bin/env python3

import os
import platform
from subprocess import Popen, PIPE

try:  # Python 2
    from Tkinter import *  # noqa
    from tkFont import Font
    from tkSimpleDialog import askstring
    from tkFileDialog import askopenfilename
    from tkMessageBox import showinfo, askyesnocancel
    from ttk import Combobox
except ImportError:  # Python 3
    from tkinter import *  # noqa
    from tkinter.font import Font
    from tkinter.simpledialog import askstring
    from tkinter.filedialog import askopenfilename
    from tkinter.messagebox import showinfo, askyesnocancel
    from tkinter.ttk import Combobox

from mufsim.gui.tooltip import CreateToolTip
from mufsim.gui.listdisplay import ListDisplay
from mufsim.gui.mufeditor import MufEditor
from mufsim.gui.menudecorators import (
    menu_cmd, menu_check, separator, accels, enable_test,
    process_enablers, create_menus,
)

import mufsim.stackitems as si
import mufsim.gamedb as db
import mufsim.utils as util
from mufsim.logger import log, warnlog, errlog, set_output_command
from mufsim.compiler import MufCompiler
from mufsim.interface import network_interface as netifc
from mufsim.processlist import process_list
from belfrywidgets.tabbednotebook import TabbedNoteBook


mufsim_version = None

command_handlers = {}


def debugger_command(words=[], usage=None, desc=None):
    def cmd_wrapper(func):
        global command_handlers
        func.usage_mesg = usage
        func.help_mesg = desc
        for word in words:
            command_handlers[word] = func.__name__
        return func
    return cmd_wrapper


class MufGui(object):
    def __init__(self):
        self.call_level = 0
        self.prev_prog = -1
        self.history = []
        self.history_line = 0
        self.prev_command = ''
        self.curr_command = ''
        self.source_displays = {}
        self.token_displays = {}
        self.function_selectors = {}
        self.setup_gui()
        set_output_command(self.update_console)
        if len(sys.argv) > 1:
            self.root.after(10, self.handle_open_files, sys.argv[1])

    def _current_pid(self):
        pid = self.current_process.get().strip()
        if pid.startswith('- '):
            return None
        if pid.startswith('PID: '):
            pid = pid[5:]
        if ' ' in pid:
            pid = pid.split(' ', 1)[0]
        try:
            return int(pid)
        except:
            return None

    def _current_prog(self):
        if self.srcs_nb.selected_pane:
            return self.srcs_nb.selected_pane
        return None

    def _selected_process(self):
        pid = self._current_pid()
        proc = process_list.get(pid)
        return proc

    def setup_gui(self):
        self.root = Tk()
        self.root.title("MUF Debugger")
        self.root.protocol("WM_DELETE_WINDOW", self.filemenu_quit)
        if platform.system() == "Darwin":
            self.root.wm_attributes("-modified", 0)

        self.current_function = {}
        self.dotrace = StringVar()
        self.dotrace.set('0')

        self.setup_gui_fonts()
        self.setup_gui_optiondb()
        self.root['menu'] = self.setup_gui_menus()

        panes1 = PanedWindow(self.root)
        panes1.pack(fill=BOTH, expand=1)

        panes2 = PanedWindow(panes1, orient=VERTICAL)
        panes3 = PanedWindow(panes1, orient=VERTICAL)
        panes1.add(panes2, minsize=150, width=250)
        panes1.add(panes3, minsize=300)

        panes2.add(self.setup_gui_data_frame(panes2), minsize=100, height=150)
        panes2.add(self.setup_gui_call_frame(panes2), minsize=100, height=150)
        panes2.add(self.setup_gui_vars_frame(panes2), minsize=100, height=300)

        panes3.add(
            self.setup_gui_source_frame(panes3),
            minsize=200, height=400, stretch='always'
        )
        panes3.add(
            self.setup_gui_console_frame(panes3),
            minsize=90, height=100
        )

        self.gui_raise_window()
        self.update_displays()
        self.root.after(100, self.update_modified)
        self.root.after(100, self.handle_processes)
        process_list.watch_process_change(self.handle_process_change)
        process_list.set_read_handler(self.handle_read)

    def setup_gui_fonts(self):
        if platform.system() == 'Windows':
            self.monospace = Font(family="Menlo", size=10)
            self.monospace_b = Font(family="Menlo", size=10, weight="bold")
            self.seriffont = Font(family="Times", size=10)
            self.sansserif = Font(family="Arial", size=10)
            self.sansserif_i = Font(family="Arial", size=10, slant="italic")
        if platform.system() == 'Darwin':
            self.monospace = Font(family="Monaco", size=12)
            self.monospace_b = Font(family="Monaco", size=12, weight="bold")
            self.seriffont = Font(family="Times", size=12)
            self.sansserif = Font(family="Tahoma", size=12)
            self.sansserif_i = Font(family="Tahoma", size=12, slant="italic")
        else:
            self.monospace = Font(family="Courier", size=10)
            self.monospace_b = Font(family="Courier", size=10, weight="bold")
            self.seriffont = Font(family="Times", size=10)
            self.sansserif = Font(family="Helvetica", size=10)
            self.sansserif_i = Font(family="Helvetica", size=10, slant="italic")

    def setup_gui_optiondb(self):
        root = self.root
        if platform.system() == 'Darwin':
            root.option_add("*background", "gray90")
            root.option_add("*Button.highlightBackground", "gray90")
            root.option_add("*Entry.highlightBackground", "gray90")
            root.option_add("*Menu.foreground", "black")
            root.option_add("*disabledForeground", "#ccc")
        elif platform.system() == 'Windows':
            root.option_add("*Button.relief", RAISED)
            root.option_add("*Button.borderWidth", "2")
            root.option_add("*background", "white")
            root.option_add("*disabledForeground", "#aaa")
        root.option_add("*Panedwindow.sashRelief", RAISED)
        root.option_add("*Panedwindow.borderWidth", "1")
        root.option_add("*Panedwindow.sashWidth", "6")
        root.option_add("*Entry.background", "white")
        root.option_add("*Text.background", "white")
        root.option_add("*Text.highlightBackground", "white")
        root.option_add("*Text.font", self.sansserif)

    def setup_gui_menus(self):
        self.menubar = Menu(self.root, name="mb", tearoff=0)
        if platform.system() == 'Darwin':
            # self.root.createcommand(
            #     '::tk::mac::ShowPreferences',
            #     self.appmenu_prefs_dlog
            # )
            self.root.createcommand(
                'tkAboutDialog',
                self.handle_about_dlog
            )
            self.root.createcommand(
                "::tk::mac::OpenDocument",
                self.handle_open_files
            )
        # Make menus from methods marked with @menu_cmd decorator.
        # Will appear in menus in order declared.
        self.menus = create_menus(self, self.root, self.menubar)
        if platform.system() == 'Darwin':
            self.helpmenu = Menu(self.menubar, name="help", tearoff=0)
            # self.root.createcommand(
            #     'tk::mac::ShowHelp', self.helpmenu_help_dlog)
            self.menubar.add_cascade(label="Help", menu=self.helpmenu)
        return self.menubar

    def setup_gui_data_frame(self, master):
        self.current_process = StringVar()
        self.current_process.set("- No Processes -")
        datafr = Frame(master, relief=FLAT, borderwidth=0)
        selfr = Frame(datafr, relief=FLAT, borderwidth=0)
        pid_lbl = Label(selfr, text="Process")
        self.pid_sel = Combobox(
            selfr,
            width=15,
            justify="left",
            state="readonly",
            textvariable=self.current_process,
            values=[]
        )
        self.pid_sel.bind(
            "<<ComboboxSelected>>",
            self.handle_process_selector_change
        )
        pid_lbl.pack(side=LEFT, fill=NONE, expand=0)
        self.pid_sel.pack(side=LEFT, fill=Y, expand=0, padx=5, pady=2)
        datalblfr = LabelFrame(
            datafr, text="Data Stack", relief="flat", borderwidth=0)
        self.data_disp = ListDisplay(
            datalblfr,
            readonly=True,
            font=self.monospace,
            gutter=4,
            gutterfont=self.monospace,
        )
        selfr.pack(side=TOP, fill=X, expand=0)
        datalblfr.pack(side=TOP, fill=BOTH, expand=1)
        self.data_disp.pack(side=TOP, fill=BOTH, expand=1)
        self.data_disp.tag_config(
            'empty', foreground="gray50", font=self.sansserif_i)
        self.data_disp.tag_bind(
            'sitem', '<Double-Button-1>', self.handle_stack_item_dblclick)
        CreateToolTip(
            self.data_disp,
            'Double-Click to pretty-print value.',
            tag='sitem',
        )
        return datafr

    def setup_gui_call_frame(self, master):
        callfr = LabelFrame(
            master, text="Call Stack", relief="flat", borderwidth=0)
        self.call_disp = ListDisplay(
            callfr,
            readonly=True,
            font=self.monospace,
            gutter=4,
            gutterfont=self.monospace,
        )
        self.call_disp.pack(side=TOP, fill=BOTH, expand=1)
        self.call_disp.tag_config(
            'empty', foreground="gray50", font=self.sansserif_i)
        self.call_disp.tag_bind(
            'callfr', '<Button-1>', self.handle_call_stack_click)
        self.call_disp.tag_config(
            'currline', background="#77f", foreground="white")
        CreateToolTip(
            self.call_disp,
            'Click to view call level.',
            tag='callfr',
        )
        return callfr

    def setup_gui_vars_frame(self, master):
        varsfr = LabelFrame(
            master, text="Variables", relief="flat", borderwidth=0)
        self.vars_disp = ListDisplay(varsfr, readonly=True)
        self.vars_disp.pack(side=TOP, fill=BOTH, expand=1)
        self.vars_disp.tag_config(
            'gvar', foreground="#00f", font=self.seriffont)
        self.vars_disp.tag_config(
            'fvar', foreground="#090", font=self.seriffont)
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
        for tag in ['gname', 'fname', 'gval', 'fval']:
            CreateToolTip(
                self.vars_disp,
                'Double-Click to pretty-print value.',
                tag=tag,
            )
        return varsfr

    def setup_gui_source_frame(self, master):
        self.srcs_nb = TabbedNoteBook(master)
        self.setup_program_source_frame(4, "Untitled.muf", "")
        return self.srcs_nb

    def setup_program_source_frame(self, prog, filename, sources):
        if prog in self.source_displays:
            lbl = self.srcs_nb.pane_label(prog)
            lbl.config(text="%s(#%d)" % (filename, prog))
        else:
            nbfr = self.srcs_nb.add_pane(
                prog,
                "%s(#%d)" % (filename, prog),
                closecommand=lambda p=prog: self.handle_close_tab(p)
            )
            nbfr.program = prog
            selfr = self.setup_gui_source_selectors_frame(nbfr, prog)
            panes = PanedWindow(nbfr, orient=VERTICAL)
            panes.add(
                self.setup_gui_source_display_frame(panes, prog),
                minsize=100, height=400, stretch='always'
            )
            panes.add(
                self.setup_gui_tokens_frame(panes, prog),
                minsize=55, height=100
            )
            selfr.pack(side=TOP, fill=X, expand=0)
            panes.pack(side=TOP, fill=BOTH, expand=1)
        self.root.update_idletasks()
        self.populate_source_display(prog)
        self.populate_token_display(prog)
        self.source_displays[prog].focus()

    def setup_gui_source_selectors_frame(self, master, prog):
        srcselfr = Frame(master)
        fun_lbl = Label(srcselfr, text="Function")
        self.current_function[prog] = StringVar()
        self.current_function[prog].set("")
        fun_sel = Combobox(
            srcselfr,
            width=20,
            justify="left",
            state="readonly",
            textvariable=self.current_function[prog],
            values=[]
        )
        fun_sel.bind(
            "<<ComboboxSelected>>",
            self.handle_function_selector_change
        )
        comp_btn = Button(
            srcselfr, text="Compile", command=self.progmenu_compile)
        fun_lbl.pack(side=LEFT, fill=NONE, expand=0)
        fun_sel.pack(side=LEFT, fill=Y, expand=0, padx=5, pady=2)
        comp_btn.pack(side=LEFT, fill=Y, expand=0, padx=10, pady=2)
        self.function_selectors[prog] = fun_sel
        return srcselfr

    def setup_gui_source_display_frame(self, master, prog):
        srcdispfr = Frame(master)
        disp = MufEditor(
            srcdispfr,
            font=self.monospace,
        )
        disp.gutter.bind(
            '<Button-1>', self.handle_sources_breakpoint_toggle)
        disp.tag_config(
            'error', background="#faa", foreground="black")
        disp.tag_config(
            'warning', background="#ffa", foreground="black")
        disp.tag_config(
            'hilite', background="#aff", foreground="black")
        disp.tag_config(
            'currline', background="#77f", foreground="white")
        disp.gutter.tag_config(
            'breakpt', background="#447", foreground="white")
        disp.pack(side=BOTTOM, fill=BOTH, expand=1)
        disp.bind("<Tab>", self.handle_editor_tabs)
        disp.bind("<<Modified>>", self.handle_editor_modify)
        CreateToolTip(
            disp.gutter,
            'Click on line number to toggle breakpoint.',
        )
        self.source_displays[prog] = disp
        return srcdispfr

    def setup_gui_tokens_display_frame(self, master, prog):
        tokfr = LabelFrame(master, text="Tokens", relief="flat", borderwidth=0)
        disp = ListDisplay(
            tokfr,
            font=self.monospace,
            readonly=True,
            gutter=5,
            basecount=0,
        )
        disp.tag_config(
            'func', foreground="#00c", font=self.monospace_b)
        disp.tag_config(
            'hilite', background="#aff", foreground="black")
        disp.tag_config(
            'currline', background="#77f", foreground="white")
        disp.pack(side=TOP, fill=BOTH, expand=1)
        self.token_displays[prog] = disp
        return tokfr

    def setup_gui_debug_buttons_frame(self, master):
        btnsfr = Frame(master)
        self.run_btn = Button(
            btnsfr, text="Run", width=5, command=self.progmenu_run)
        self.stepi_btn = Button(
            btnsfr, text="Inst", width=5, command=self.progmenu_step_inst)
        self.stepl_btn = Button(
            btnsfr, text="Step", width=5, command=self.progmenu_step_line)
        self.nextl_btn = Button(
            btnsfr, text="Next", width=5, command=self.progmenu_next_line)
        self.finish_btn = Button(
            btnsfr, text="Finish", width=5, command=self.progmenu_finish)
        self.cont_btn = Button(
            btnsfr, text="Cont", width=5, command=self.progmenu_continue)
        self.trace_chk = Checkbutton(
            btnsfr, text="Trace",
            variable=self.dotrace,
            onvalue='1',
            offvalue='0',
            command=self.progmenu_trace,
        )
        self.run_btn.pack(side=LEFT, fill=NONE, expand=0)
        self.stepi_btn.pack(side=LEFT, fill=NONE, expand=0)
        self.stepl_btn.pack(side=LEFT, fill=NONE, expand=0)
        self.nextl_btn.pack(side=LEFT, fill=NONE, expand=0)
        self.finish_btn.pack(side=LEFT, fill=NONE, expand=0)
        self.cont_btn.pack(side=LEFT, fill=NONE, expand=0)
        self.trace_chk.pack(side=LEFT, fill=NONE, expand=0)
        CreateToolTip(self.run_btn, 'Run program from the start.')
        CreateToolTip(self.stepi_btn, 'Execute one instruction.')
        CreateToolTip(self.stepl_btn, 'Step one line, following calls.')
        CreateToolTip(self.nextl_btn, 'Next line, stepping over calls.')
        CreateToolTip(self.finish_btn, 'Finish the current function.')
        CreateToolTip(self.cont_btn, 'Continue execution.')
        CreateToolTip(self.trace_chk, 'Show stack trace for each instruction.')
        return btnsfr

    def setup_gui_tokens_frame(self, master, prog):
        tokfr = Frame(master)
        tokdispfr = self.setup_gui_tokens_display_frame(tokfr, prog)
        tokdispfr.pack(side=BOTTOM, fill=BOTH, expand=1)
        return tokfr

    def setup_gui_console_frame(self, master):
        consfr = Frame(master)
        self.cons_disp = ListDisplay(
            consfr,
            height=1,
            wrap=WORD,
            readonly=True,
            font=self.monospace
        )
        self.cons_disp.tag_config('good', foreground="#0a0")
        self.cons_disp.tag_config('trace', foreground="#777")
        self.cons_disp.tag_config('warning', foreground="#880")
        self.cons_disp.tag_config('error', foreground="#c00")
        self.cons_in = Entry(consfr, relief=SUNKEN)
        btnsfr = self.setup_gui_debug_buttons_frame(consfr)

        btnsfr.pack(side=TOP, fill=X, expand=0)
        self.cons_disp.pack(side=TOP, fill=BOTH, expand=1)
        self.cons_in.pack(side=TOP, fill=X, expand=0)

        self.cons_in.bind("<Key-Up>", self.handle_command_history_prev)
        self.cons_in.bind("<Key-Down>", self.handle_command_history_next)
        self.cons_in.bind("<Key-Tab>", self.handle_command_completion)
        self.cons_in.bind("<Key-Return>", self.handle_command)
        return consfr

    def gui_raise_window(self):
        try:
            self.root.tk.call('console', 'hide')
        except TclError:
            # Some versions of the Tk framework don't have a console object
            pass
        if platform.system() == 'Darwin':
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
            self.root.lift()
            self.root.call('wm', 'attributes', '.', '-topmost', True)
            self.root.after_idle(
                self.root.call, 'wm', 'attributes', '.', '-topmost', False)

    def handle_processes(self):
        netifc.poll(0.0)
        process_list.process(self.call_level)
        self.root.after(250, self.handle_processes)

    def handle_close_tab(self, prog):
        progobj = db.getobj(prog)
        srcs_disp = self.source_displays[prog]
        if srcs_disp.edit_modified():
            dosave = askyesnocancel(
                "Unsaved Changes",
                "Save changes to %s?" % progobj.name,
                parent=self.root,
            )
            if dosave is None:
                return False
            if dosave:
                self.save_program_to_file(prog)
        process_list.killall(prog)
        db.recycle_object(prog)
        self.update_displays()
        return True

    def handle_about_dlog(self):
        global mufsim_version
        if platform.system() == 'Darwin' and not mufsim_version:
            if "MufSim.app/Contents/Resources" in os.getcwd():
                from plistlib import Plist
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

    def handle_call_stack_click(self, event):
        w = event.widget
        index = w.index("@%s,%s" % (event.x, event.y))
        level = int(index.split('.')[0]) - 1
        self.update_displays(level=level)
        self.cons_in.focus()

    def handle_stack_item_dblclick(self, event):
        w = event.widget
        index = w.index("@%s,%s" % (event.x, event.y))
        currproc = self._selected_process()
        if index and currproc:
            item = int(float(index))
            val = currproc.data_pick(item)
            val = si.item_repr_pretty(val)
            log("pick(%d) = %s" % (item, val))
        self.cons_in.focus()

    def handle_vars_gname_dblclick(self, event):
        w = event.widget
        index = w.index("@%s,%s" % (event.x, event.y))
        rng = w.tag_prevrange('gname', index + '+1c')
        currproc = self._selected_process()
        if rng and currproc:
            vname = w.get(*rng)
            addr = currproc.call_addr(self.call_level)
            vnum = currproc.program_global_var(addr.prog, vname)
            val = currproc.globalvar_get(vnum)
            val = si.item_repr_pretty(val)
            log("%s = %s" % (vname, val))
        self.cons_in.focus()

    def handle_vars_fname_dblclick(self, event):
        w = event.widget
        index = w.index("@%s,%s" % (event.x, event.y))
        rng = w.tag_prevrange('fname', index + '+1c')
        currproc = self._selected_process()
        if rng and currproc:
            vname = w.get(*rng)
            addr = currproc.call_addr(self.call_level)
            fun = currproc.program_find_func(addr)
            vnum = currproc.program_func_var(addr.prog, fun, vname)
            val = currproc.funcvar_get(vnum, self.call_level)
            val = si.item_repr_pretty(val)
            log("%s = %s" % (vname, val))
        self.cons_in.focus()

    def handle_process_selector_change(self, event=None):
        self.update_process_selected()
        self.update_displays()

    def handle_function_selector_change(self, event=None):
        prog = self._current_prog()
        if prog is None:
            return
        srcs_disp = self.source_displays[prog]
        tokn_disp = self.token_displays[prog]
        srcs_disp.tag_remove('hilite', '0.0', END)
        tokn_disp.tag_remove('hilite', '0.0', END)
        fun = self.current_function[prog].get()
        if not fun:
            return
        currproc = self._selected_process()
        if not currproc:
            return
        addr = currproc.program_function_addr(prog, fun)
        line = currproc.get_inst_line(addr)
        srcs_disp.tag_add(
            'hilite',
            '%d.0' % line,
            '%d.end+1c' % line,
        )
        tokn_disp.tag_add(
            'hilite',
            '%d.0' % (addr.value + 1),
            '%d.end+1c' % (addr.value + 1),
        )
        srcs_disp.mark_set(INSERT, '%d.end' % line)
        srcs_disp.see('%d.0' % line)
        tokn_disp.see('%d.0' % (addr.value + 1))
        self.root.after_idle(srcs_disp.focus)

    def handle_sources_breakpoint_toggle(self, event):
        currproc = self._selected_process()
        if not currproc:
            return
        w = event.widget
        index = w.index("@%s,%s" % (event.x, event.y))
        line = int(float(index))
        prog = self._current_prog()
        if prog is None:
            return
        bpnum = currproc.find_breakpoint(prog, line)
        if bpnum is not None:
            currproc.del_breakpoint(bpnum)
        else:
            currproc.add_breakpoint(prog, line)
        self.update_sourcecode_breakpoints(prog)

    def handle_read(self):
        while True:
            self.update_displays()
            readline = askstring(
                "MUF Read Requested",
                "Enter text to satisfy the READ request.",
                initialvalue="",
                parent=self.root,
            )
            self.cons_in.focus()
            return readline

    def handle_command_completion(self, event=None):
        global command_handlers
        cmd = self.cons_in.get()
        idx = self.cons_in.index(INSERT)
        if ' ' not in cmd[:idx]:
            cmds = [
                x for x in sorted(list(command_handlers.keys()))
                if len(x) > 1
            ]
            found = []
            for word in cmds:
                if word.startswith(cmd[:idx]):
                    found.append(word)
            if len(found) == 0:
                self.root.bell()
                warnlog("No match.")
                return 'break'
            elif len(found) == 1:
                word = found[0]
            else:
                self.root.bell()
                word = os.path.commonprefix(found)
                warnlog("Ambiguous: %s" % " ".join(found))
            cmd = word + cmd[idx:]
            idx = len(word)
            self.cons_in.delete(0, END)
            self.cons_in.insert(0, cmd)
            self.cons_in.icursor(idx)
        return 'break'

    def handle_command_history_prev(self, event=None):
        if self.history_line > 0:
            if self.history_line == len(self.history):
                self.curr_command = self.cons_in.get()
            self.history_line -= 1
            self.cons_in.delete(0, END)
            self.cons_in.insert(0, self.history[self.history_line])
            self.cons_in.icursor(END)
        return 'break'

    def handle_command_history_next(self, event=None):
        if self.history_line < len(self.history) - 1:
            self.history_line += 1
            self.cons_in.delete(0, END)
            self.cons_in.insert(0, self.history[self.history_line])
            self.cons_in.icursor(END)
        elif self.history_line == len(self.history) - 1:
            self.history_line += 1
            self.cons_in.delete(0, END)
            self.cons_in.insert(0, self.curr_command)
            self.cons_in.icursor(END)
        return 'break'

    def handle_command(self, event=None):
        global command_handlers
        cmd = self.cons_in.get()
        self.cons_in.delete(0, END)
        if cmd and self.history and cmd != self.history[-1]:
            self.history.append(cmd)
        while len(self.history) > 1000:
            self.history.pop(0)
        self.history_line = len(self.history)
        if cmd:
            self.prev_command = cmd
        else:
            cmd = self.prev_command
        args = ''
        if ' ' in cmd:
            cmd, args = cmd.split(' ', 1)
            args = args.strip()
        if cmd in command_handlers:
            meth = command_handlers[cmd]
            getattr(self, meth)(args)
            self.update_displays(level=self.call_level)
        else:
            errlog("Unrecognized command.")
        return 'break'

    def handle_editor_tabs(self, event):
        event.widget.insert(INSERT, "    ")
        return 'break'

    def handle_editor_modify(self, event):
        self.update_modified()

    def _pid_text(self, pid):
        proc = process_list.get(pid)
        if not proc:
            return None
        return "PID: %d %s" % (proc.pid, proc.wait_state)

    def handle_process_change(self):
        txt = self._pid_text(process_list.current_process.pid)
        self.current_process.set(txt)
        self.update_displays()
        self.root.update()

    def clear_errors(self):
        self.errors_queue = []

    def update_errors(self):
        prog = self._current_prog()
        if not prog:
            return False
        first = True
        srcs_disp = self.source_displays[prog]
        srcs_disp.tag_remove('error', '0.0', END)
        srcs_disp.tag_remove('warning', '0.0', END)
        for line, typ, msg in self.errors_queue:
            srcs_disp.tag_add(typ, '%d.0' % line, '%d.end+1c' % line)
            if first:
                first = False
                srcs_disp.see('%d.0' % line)

    def update_console(self, msgtype, msg):
        m = re.match(r'^(Warning|Error) in line (\d+): (.*)$', msg)
        if m:
            errtype = m.group(1).lower()
            errline = int(m.group(2))
            errmsg = m.group(3)
            self.errors_queue.append((errline, errtype, errmsg))
        self.cons_disp.insert(END, "\n")
        self.cons_disp.insert(END, msg, msgtype)
        self.cons_disp.see('end linestart')

    def update_modified(self):
        if platform.system() != "Darwin":
            return
        self.root.after(1000, self.update_modified)
        prog = self._current_prog()
        if prog is None:
            self.root.wm_attributes("-modified", 0)
            return
        srcs_disp = self.source_displays[prog]
        if srcs_disp.edit_modified():
            self.root.wm_attributes("-modified", 1)
        else:
            self.root.wm_attributes("-modified", 0)

    def update_process_selected(self):
        if not process_list.get_pids():
            self.current_process.set("- No Processes -")
        elif not process_list.current_process:
            self.current_process.set("- Select Process -")
        else:
            currproc = process_list.current_process
            self.current_process.set(self._pid_text(currproc.pid))

    def update_process_selector(self):
        funs = [
            self._pid_text(pid)
            for pid in process_list.get_pids()
        ]
        self.pid_sel.config(values=funs)

    def update_function_selector(self):
        prog = self._current_prog()
        if prog is None:
            return
        currproc = self._selected_process()
        if currproc:
            addr = currproc.call_addr(self.call_level)
            if addr:
                prog = addr.prog
        if not db.validobj(prog):
            self.current_function[prog].set("")
            return
        funs = []
        comp = db.getobj(prog).compiled
        currfun = ""
        if comp:
            funs = comp.get_functions()
            currfun = funs[0]
        if currproc:
            addr = currproc.call_addr(self.call_level)
            if addr:
                funs = currproc.program_functions(addr.prog)
                currfun = currproc.program_find_func(addr)
        if not funs:
            self.current_function[prog].set("")
        else:
            fun_sel = self.function_selectors[prog]
            fun_sel.config(values=funs)
            self.current_function[prog].set(currfun)

    def update_data_stack_display(self):
        self.data_disp.delete('0.0', END)
        currproc = self._selected_process()
        if not currproc or not currproc.data_stack:
            self.data_disp.insert('0.0', ' - EMPTY STACK - ', 'empty')
            return
        for i, val in enumerate(reversed(currproc.data_stack)):
            line = '%s\n' % si.item_repr(val)
            self.data_disp.insert(END, line, 'sitem')
        self.data_disp.delete('end-1c', END)
        self.data_disp.see('0.0')

    def update_call_stack_display(self):
        self.call_disp.tag_remove('currline', '0.0', END)
        fmt = "{progname}({prog}), {func}, {line}\n"
        self.call_disp.delete('0.0', END)
        currproc = self._selected_process()
        if not currproc or not currproc.get_call_stack():
            self.call_disp.insert('0.0', ' - NOT RUNNING - ', 'empty')
            return
        for callinfo in currproc.get_call_stack():
            callinfo['progname'] = db.getobj(callinfo['prog']).name
            line = fmt.format(**callinfo)
            self.call_disp.insert(END, line, 'callfr')
        self.call_disp.tag_add(
            'currline',
            '%d.0' % (self.call_level + 1),
            '%d.end+1c' % (self.call_level + 1),
        )
        self.call_disp.delete('end-1c', END)
        self.call_disp.see('0.0')

    def update_variables_display(self):
        self.vars_disp.delete('0.0', END)
        currproc = self._selected_process()
        if not currproc:
            return
        addr = currproc.call_addr(self.call_level)
        if not addr:
            return
        gvars = currproc.program_global_vars(addr.prog)
        cnt = 0
        for vnum, vname in enumerate(gvars):
            val = currproc.globalvar_get(vnum)
            val = si.item_repr(val)
            self.vars_disp.insert(END, "G", 'gvar')
            self.vars_disp.insert(END, " ")
            self.vars_disp.insert(END, vname, 'gname')
            self.vars_disp.insert(END, " = ", 'eq')
            self.vars_disp.insert(END, val, 'gval')
            self.vars_disp.insert(END, "\n")
            cnt += 1
        fun = currproc.program_find_func(addr)
        fvars = currproc.program_func_vars(addr.prog, fun)
        for vnum, vname in enumerate(fvars):
            val = currproc.funcvar_get(vnum)
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

    def update_sourcecode_from_program(self, prog, force=False):
        if prog != self.prev_prog or force:
            if not db.validobj(prog):
                return
            self.prev_prog = prog
            self.srcs_nb.showpane(prog)

    def update_sourcecode_breakpoints(self, prog):
        srcs_disp = self.source_displays[prog]
        srcs_disp.gutter.tag_remove('breakpt', '0.0', END)
        currproc = self._selected_process()
        if not currproc:
            return
        for bpprog, line in currproc.get_breakpoints():
            if bpprog == prog:
                srcs_disp.gutter.tag_add(
                    'breakpt',
                    '%d.0' % line,
                    '%d.5' % line
                )

    def update_sourcecode_display(self):
        prog = self._current_prog()
        if prog is None:
            return
        addr = None
        currproc = self._selected_process()
        if currproc:
            addr = currproc.call_addr(self.call_level)
            if addr:
                prog = addr.prog
        srcs_disp = self.source_displays[prog]
        srcs_disp.tag_remove('hilite', '0.0', END)
        srcs_disp.tag_remove('currline', '0.0', END)
        self.update_sourcecode_from_program(prog)
        if not currproc:
            return
        if not addr:
            return
        inst = currproc.get_inst(addr)
        srcs_disp.tag_add(
            'currline',
            '%d.0' % inst.line,
            '%d.end+1c' % inst.line,
        )
        self.update_sourcecode_breakpoints(prog)
        srcs_disp.see('%d.0 - 2l' % inst.line)
        srcs_disp.see('%d.0 + 2l' % inst.line)
        srcs_disp.see('%d.0' % inst.line)

        tokn_disp = self.token_displays[prog]
        tokn_disp.tag_remove('hilite', '0.0', END)
        tokn_disp.tag_remove('currline', '0.0', END)
        tokn_disp.tag_add(
            'currline',
            '%d.0' % (addr.value + 1),
            '%d.end+1c' % (addr.value + 1),
        )
        tokn_disp.see('%d.0 - 1l' % (addr.value + 1))
        tokn_disp.see('%d.0 + 1l' % (addr.value + 1))
        tokn_disp.see('%d.0' % (addr.value + 1))

    def update_displays(self, level=-1):
        currproc = self._selected_process()
        if currproc and level < 0:
            level = len(currproc.get_call_stack()) + level
        self.call_level = level
        self.update_buttonbar()
        self.update_process_selector()
        self.update_function_selector()
        self.update_call_stack_display()
        self.update_data_stack_display()
        self.update_variables_display()
        self.update_sourcecode_display()
        process_enablers(self)

    def update_buttonbar(self):
        runstate = "normal" if self.allow_run() else "disabled"
        livestate = "normal" if self.allow_debug() else "disabled"
        self.run_btn.config(state=runstate)
        self.trace_chk.config(state=runstate)
        livebtns = [
            self.stepi_btn,
            self.stepl_btn,
            self.nextl_btn,
            self.finish_btn,
            self.cont_btn,
        ]
        for btn in livebtns:
            btn.config(state=livestate)

    def populate_source_display(self, prog):
        srcs_disp = self.source_displays[prog]
        progobj = db.getobj(prog)
        srcs = []
        if progobj.sources:
            srcs = progobj.sources.split("\n")
        srcs_disp.delete('0.0', END)
        for i, srcline in enumerate(srcs):
            line = "%s\n" % srcline
            srcs_disp.insert(END, line)
        srcs_disp.delete('end-1c', END)
        srcs_disp.edit_reset()
        srcs_disp.edit_modified(False)

    def populate_token_display(self, prog):
        tokens = []
        progobj = db.getobj(prog)
        if progobj.compiled:
            tokens = progobj.compiled.get_tokens_info()
        tokn_disp = self.token_displays[prog]
        tokn_disp.delete('0.0', END)
        for i, token in enumerate(tokens):
            rep = token['repr']
            line = "%s\n" % rep
            if rep.startswith('Function:'):
                tokn_disp.insert(END, line, "func")
            else:
                tokn_disp.insert(END, line)
        tokn_disp.delete('end-1c', END)

    def compile_program(self, prog):
        self.clear_errors()
        process_list.killall(prog)
        progobj = db.getobj(prog)
        progobj.compiled = None
        success = MufCompiler().compile_source(prog)
        self.update_sourcecode_from_program(prog, force=True)
        if not success:
            errlog(
                "MUF tokenization of %s(#%d) failed!" % (
                    progobj.name, progobj.dbref
                )
            )
        else:
            log(
                "MUF tokenization of %s(#%d) successful." % (
                    progobj.name, progobj.dbref
                ),
                msgtype="good"
            )
            self.update_displays()
        self.update_errors()
        self.populate_token_display(prog)
        self.update_displays()

    def reset_execution(self, prog=None, command=""):
        # db.init_object_db()
        userobj = db.get_player_obj("John_Doe")
        trigobj = db.get_registered_obj(userobj, "$testaction")
        if prog:
            progobj = db.getobj(prog)
        else:
            progobj = db.get_registered_obj(userobj, "$cmd/test")
        breakpts = []
        currproc = self._selected_process()
        if currproc:
            breakpts = currproc.breakpoints
        currproc = process_list.new_process()
        currproc.set_break_on_error()
        currproc.set_trace(self.dotrace.get() != '0')
        currproc.breakpoints = breakpts
        currproc.setup(progobj, userobj, trigobj, command)

    def resume_execution(self):
        currproc = self._selected_process()
        if currproc and currproc.get_call_stack():
            currproc.execute_code(self.call_level)
            if not currproc.get_call_stack():
                warnlog("Program exited.")
        self.update_displays()
        self.cons_in.focus()

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
        outdata = outdata.decode()
        errdata = errdata.decode()
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

    def load_program_from_file(self, filename):
        self.cons_disp.delete('0.0', END)
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
        selprog = self._current_prog()
        if (
            selprog and db.validobj(selprog) and
            db.getobj(selprog).name == 'Untitled.muf' and
            db.getobj(selprog).objtype == 'program' and
            not db.getobj(selprog).sources
        ):
            progobj = db.getobj(selprog)
            progobj.name = os.path.basename(filename)
        else:
            progobj = db.DBObject(
                name=os.path.basename(filename),
                objtype="program",
                flags="3",
                owner=userobj.dbref,
                location=userobj.dbref,
            )
            log("CREATED PROG %s FROM %s" % (progobj, filename))
        progobj.sources = srcs
        self.setup_program_source_frame(
            progobj.dbref,
            progobj.name,
            progobj.sources,
        )
        self.compile_program(progobj.dbref)

    def save_program_to_file(self, prog):
        progobj = db.getobj(prog)
        srcs_disp = self.source_displays[prog]
        progobj.sources = srcs_disp.get('1.0', 'end-2c')
        if re.match(r'Untitled.mu[fv]$', progobj.name):
            extras = {}
            if platform.system() == 'Darwin':
                extras = dict(
                    message="Select a source file to load...",
                )
            filename = asksaveasfilename(
                parent=self.root,
                title="Load Program",
                initialfile=progobj.name,
                defaultextension=".muf",
                filetypes=[
                    ('MUF files', '.muf'),
                    ('MUF files', '.m'),
                    ('MUV files', '.muv'),
                ],
                **extras
            )
            if not filename:
                return
            progobj.name = filename
        with open(filename, "w") as f:
            f.write(progobj.sources)
        lbl = self.srcs_nb.pane_label(progobj.dbref)
        lbl.config(text="%s(#%d)" % (filename, progobj.dbref))
        srcs_disp.edit_modified(False)

    @debugger_command(
        words=["h", "help"],
        usage="help [CMD]",
        desc="Shows help."
    )
    def cmd_help(self, args):
        global command_handlers
        if args and args in command_handlers:
            func = getattr(self, command_handlers[args])
            log("Usage: %s" % func.usage_mesg)
            log("%s" % func.help_mesg)
        else:
            cmds = [
                x for x in sorted(list(command_handlers.keys()))
                if len(x) > 1
            ]
            log("Available commands: %s" % " ".join(cmds))
            log("Use 'help COMMAND' for more help on a command.")

    @debugger_command(
        words=["r", "run"],
        usage="run [TEXT]",
        desc="Starts the MUF program, with the given command args."
    )
    def cmd_run(self, args):
        log("Starting run with command = %s" % util.escape_str(args))
        prog = self._current_prog()
        self.reset_execution(prog=prog, command=args)
        self.update_displays()

    @debugger_command(
        words=["i", "istep"],
        usage="istep [COUNT]",
        desc="Steps execution by one or more instructions."
    )
    def cmd_istep(self, args):
        currproc = self._selected_process()
        if not currproc:
            errlog("Program not running.")
            return
        try:
            if not args:
                args = "1"
            cnt = int(args)
            currproc.set_break_insts(cnt)
            self.resume_execution()
        except:
            errlog("Usage: istep [COUNT]")

    @debugger_command(
        words=["s", "step"],
        usage="step [COUNT]",
        desc="Steps execution by one or more source lines.  Steps into calls."
    )
    def cmd_step(self, args):
        currproc = self._selected_process()
        if not currproc:
            errlog("Program not running.")
            return
        try:
            if not args:
                args = "1"
            cnt = int(args)
            currproc.set_break_steps(cnt)
            self.resume_execution()
        except:
            errlog("Usage: step [COUNT]")

    @debugger_command(
        words=["n", "next"],
        usage="next [COUNT]",
        desc="Steps execution by one or more source lines.  Steps over calls."
    )
    def cmd_next(self, args):
        currproc = self._selected_process()
        if not currproc:
            errlog("Program not running.")
            return
        try:
            if not args:
                args = "1"
            cnt = int(args)
            currproc.set_break_lines(cnt)
            self.resume_execution()
        except:
            errlog("Usage: next [COUNT]")

    @debugger_command(
        words=["f", "finish"],
        usage="finish",
        desc="Finish execution of current function."
    )
    def cmd_finish(self, args):
        currproc = self._selected_process()
        if not currproc:
            errlog("Program not running.")
            return
        if args:
            errlog("Usage: finish")
            return
        currproc.set_break_on_finish(True)
        self.resume_execution()

    @debugger_command(
        words=["c", "cont", "continue"],
        usage="finish",
        desc="Continue execution until next breakpoint, or program finishes."
    )
    def cmd_continue(self, args):
        currproc = self._selected_process()
        if not currproc:
            errlog("Program not running.")
            return
        if args:
            errlog("Usage: continue")
            return
        currproc.set_break_on_finish(True)
        self.resume_execution()

    @debugger_command(
        words=["b", "break"],
        usage="break LINE|FUNCNAME",
        desc="Sets breakpoint at given line or function."
    )
    def cmd_break(self, args):
        currproc = self._selected_process()
        if not currproc:
            errlog("Program not running.")
            return
        addr = currproc.call_addr(self.call_level)
        try:
            line = int(args)
            bpnum = currproc.add_breakpoint(addr.prog, line)
        except:
            funcaddr = currproc.program_function_addr(addr.prog, args)
            if not funcaddr:
                log("Usage: break [LINE|FUNCNAME]")
                return
            line = currproc.get_inst_line(funcaddr)
            bpnum = currproc.add_breakpoint(addr.prog, line)
        log("Added breakpoint %d at #%d line %d." % (bpnum, addr.prog, line))
        self.update_sourcecode_breakpoints(addr.prog)

    @debugger_command(
        words=["delete"],
        usage="delete BPNUM",
        desc="Deletes the given breakpoint."
    )
    def cmd_delete(self, args):
        currproc = self._selected_process()
        if not currproc:
            errlog("Program not running.")
            return
        bps = currproc.get_breakpoints()
        if not util.is_int(args) or int(args) - 1 not in list(range(len(bps))):
            errlog("Usage: delete BREAKPOINTNUM")
        else:
            currproc.del_breakpoint(int(args) - 1)
            log("Deleted breakpoint %d." % int(args))
            prog = _current_prog()
            self.update_sourcecode_breakpoints(prog)

    @debugger_command(
        words=["p", "print"],
        usage="print VAR",
        desc="Pretty-prints the given variable to the console."
    )
    def cmd_print(self, args):
        currproc = self._selected_process()
        if not currproc:
            log("Program not running.")
            return
        addr = currproc.call_addr(self.call_level)
        fun = currproc.program_find_func(addr)
        if currproc.program_func_var(addr.prog, fun, args):
            v = currproc.program_func_var(addr.prog, fun, args)
            val = currproc.funcvar_get(v)
        elif currproc.program_global_var(addr.prog, args):
            v = currproc.program_global_var(addr.prog, args)
            val = currproc.globalvar_get(v)
        else:
            errlog("Variable not found: %s" % args)
            val = None
        if val is not None:
            val = si.item_repr_pretty(val)
            log("%s = %s" % (args, val))

    @debugger_command(
        words=["w", "where"],
        usage="where",
        desc="Show the current call stack."
    )
    def cmd_where(self, args):
        currproc = self._selected_process()
        if not currproc:
            errlog("Program not running.")
            return
        fmt = (
            "{mk}{level:-3d}: In prog {prog}, func '{func}'," +
            " line {line}: {inst}\n" +
            "    {src}"
        )
        for callinfo in currproc.get_call_stack():
            if callinfo['level'] == self.call_level:
                callinfo['mk'] = '>'
            else:
                callinfo['mk'] = ' '
            log(fmt.format(**callinfo))

    @debugger_command(
        words=["up"],
        usage="up",
        desc="Move context up the call stack."
    )
    def cmd_up(self, args):
        currproc = self._selected_process()
        if not currproc:
            errlog("Program not running.")
            return
        if self.call_level <= 0:
            errlog("Already at first call level.")
            return
        self.call_level -= 1
        log("Now at call level %d" % (self.call_level + 1))

    @debugger_command(
        words=["dn", "down"],
        usage="down",
        desc="Move context down the call stack."
    )
    def cmd_down(self, args):
        if not currproc:
            errlog("Program not running.")
            return
        levels = currproc.get_call_stack()
        if self.call_level >= len(levels) - 1:
            errlog("Already at last call level.")
            return
        self.call_level += 1
        log("Now at call level %d" % (self.call_level + 1))

    @debugger_command(
        words=["trace"],
        usage="trace",
        desc="Enable per-instruction data stack tracing."
    )
    def cmd_trace(self, args):
        if not self.allow_run():
            errlog("Program not compiled.")
            return
        self.dotrace.set('1')
        if currproc:
            currproc.set_trace(self.dotrace.get() != '0')

    @debugger_command(
        words=["notrace"],
        usage="notrace",
        desc="Disable per-instruction data stack tracing."
    )
    def cmd_notrace(self, args):
        if not self.allow_run():
            errlog("Program not compiled.")
            return
        self.dotrace.set('0')
        currproc = self._selected_process()
        if currproc:
            currproc.set_trace(self.dotrace.get() != '0')

    @debugger_command(
        words=["pop"],
        usage="pop [COUNT]",
        desc="Pop one or more items off the data stack."
    )
    def cmd_pop(self, args):
        currproc = self._selected_process()
        if not currproc:
            errlog("Program not running.")
            return
        try:
            if not args:
                args = "1"
            cnt = int(args)
            for i in range(cnt):
                currproc.data_pop()
        except:
            errlog("Usage: pop [COUNT]")

    @debugger_command(
        words=["dup"],
        usage="dup [COUNT]",
        desc="Duplicate one or more items from the top of the data stack."
    )
    def cmd_dup(self, args):
        currproc = self._selected_process()
        if not currproc:
            errlog("Program not running.")
            return
        try:
            if not args:
                args = "1"
            cnt = int(args)
            for i in range(cnt):
                currproc.data_pick(cnt)
        except:
            errlog("Usage: dup [COUNT]")

    @debugger_command(
        words=["rot", "rotate"],
        usage="rot COUNT",
        desc="Rotate top COUNT items on the top of the data stack."
    )
    def cmd_rotate(self, args):
        currproc = self._selected_process()
        if not currproc:
            errlog("Program not running.")
            return
        try:
            if not args:
                args = "1"
            cnt = int(args)
            if cnt > 0:
                currproc.data_push(currproc.data_pull(cnt))
            elif cnt < 0:
                val = currproc.data_pop()
                currproc.data_insert((-cnt) - 1, val)
        except:
            errlog("Usage: dup [COUNT]")

    @debugger_command(
        words=["swap"],
        usage="swap",
        desc="Swap top two items on the top of the data stack."
    )
    def cmd_swap(self, args):
        currproc = self._selected_process()
        if not currproc:
            errlog("Program not running.")
            return
        a = currproc.data_pop()
        b = currproc.data_pop()
        currproc.data_push(a)
        currproc.data_push(b)

    @debugger_command(
        words=["push"],
        usage="push VALUE",
        desc="Push VALUE onto the top of the data stack."
    )
    def cmd_push(self, args):
        currproc = self._selected_process()
        if not currproc:
            errlog("Program not running.")
            return
        elif not args:
            errlog("Usage: push VALUE")
            return
        elif util.is_int(args):
            currproc.data_push(int(args))
        elif util.is_float(args):
            currproc.data_push(float(args))
        elif util.is_dbref(args):
            currproc.data_push(si.DBRef(int(args[1:])))
        elif util.is_strlit(args):
            currproc.data_push(args[1:-1])
        log("Stack item pushed.")

    def allow_srcsedit(self):
        prog = self._current_prog()
        if not prog:
            return False
        srcs_disp = self.source_displays[prog]
        return self.root.focus_get() == srcs_disp

    def allow_run(self):
        prog = self._current_prog()
        if not prog:
            return False
        return bool(db.getobj(prog).compiled)

    def allow_debug(self):
        currproc = self._selected_process()
        return currproc and currproc.get_call_stack()

    def appmenu_prefs_dlog(self, event=None):
        # TODO: implement!
        print("Display preferences dlog.")

    @menu_cmd("File", "New Program...")
    @accels(mac="Cmd-N", win="Ctrl-N", lin="Ctrl-N")
    def filemenu_new_program(self, event=None):
        self.cons_disp.delete('0.0', END)
        userobj = db.get_player_obj("John_Doe")
        progobj = db.DBObject(
            name='Untitled.muf',
            objtype="program",
            flags="3",
            owner=userobj.dbref,
            location=userobj.dbref,
        )
        self.setup_program_source_frame(progobj.dbref, progobj.name, "")
        self.update_displays()

    @menu_cmd("File", "Open Program...")
    @accels(mac="Cmd-O", win="Ctrl-O", lin="Ctrl-O")
    def filemenu_open_program(self, event=None):
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
                ('MUF files', '.muf'),
                ('MUF files', '.m'),
                ('MUV files', '.muv'),
            ],
            **extras
        )
        if not filename:
            return
        self.load_program_from_file(filename)

    @separator
    @menu_cmd("File", "Close Tab")
    @accels(mac="Cmd-W", win="Ctrl-W", lin="Ctrl-W")
    @enable_test('allow_run')
    def filemenu_close(self, event=None):
        prog = self._current_prog()
        if not prog:
            return
        progobj = db.getobj(prog)
        srcs_disp = self.source_displays[prog]
        if srcs_disp.edit_modified():
            dosave = askyesnocancel(
                "Unsaved Changes",
                "Save changes to %s?" % progobj.name,
                parent=self.root,
            )
            if dosave is None:
                return
            if dosave:
                self.save_program_to_file(prog)
        process_list.killall(prog)
        db.recycle_object(prog)
        self.srcs_nb.remove_pane(prog)
        self.update_displays()

    @menu_cmd("File", "Save Program")
    @accels(mac="Cmd-S", win="Ctrl-S", lin="Ctrl-S")
    @enable_test('allow_run')
    def filemenu_save_program(self, event=None):
        prog = self._current_prog()
        if not prog:
            return
        self.save_program_to_file(prog)
        self.update_displays()

    @separator
    @menu_cmd("File", "Exit", plats=["Windows"])
    @menu_cmd("File", "Quit", plats=["Linux"])
    @accels(win="Alt-F4", lin="Ctrl-Q")
    def filemenu_quit(self, event=None):
        netifc.notify_all('System shutting down.')
        netifc.flush_all_descrs()
        netifc.disconnect_all()
        try:
            self.root.destroy()
        except:
            pass

    @menu_cmd("Edit", "Undo")
    @accels(mac="Cmd-Z", win="Ctrl-Z", lin="Ctrl-Z")
    def editmenu_undo(self, event=None):
        self.root.focus_get().event_generate("<<Undo>>"),

    @menu_cmd("Edit", "Redo")
    @accels(mac="Cmd-Y", win="Ctrl-Y", lin="Ctrl-Y")
    def editmenu_redo(self, event=None):
        self.root.focus_get().event_generate("<<Redo>>"),

    @separator
    @menu_cmd("Edit", "Cut")
    @accels(mac="Cmd-X", win="Ctrl-X", lin="Ctrl-X")
    def editmenu_cut(self, event=None):
        self.root.focus_get().event_generate("<<Cut>>"),

    @menu_cmd("Edit", "Copy")
    @accels(mac="Cmd-C", win="Ctrl-C", lin="Ctrl-C")
    def editmenu_copy(self, event=None):
        self.root.focus_get().event_generate("<<Copy>>"),

    @menu_cmd("Edit", "Paste")
    @accels(mac="Cmd-V", win="Ctrl-V", lin="Ctrl-V")
    def editmenu_paste(self, event=None):
        self.root.focus_get().event_generate("<<Paste>>"),

    @separator
    @menu_cmd("Edit", "Clear")
    @accels(mac="Delete", win="Delete", lin="Delete")
    def editmenu_clear(self, event=None):
        self.root.focus_get().event_generate("<<Clear>>"),

    @separator
    @menu_cmd("Edit", "Indent")
    @accels(mac="Cmd-]", win="Ctrl+]", lin="Ctrl+]")
    @enable_test('allow_srcsedit')
    def editmenu_indent(self, event=None):
        prog = self._current_prog()
        if prog:
            srcs_disp = self.source_displays[prog]
            srcs_disp.indent_text(by=4)
        return 'break'

    @menu_cmd("Edit", "Unindent")
    @accels(mac="Cmd-[", win="Ctrl+[", lin="Ctrl+[")
    @enable_test('allow_srcsedit')
    def editmenu_unindent(self, event=None):
        prog = self._current_prog()
        if prog:
            srcs_disp = self.source_displays[prog]
            srcs_disp.indent_text(by=-4)
        return 'break'

    @menu_cmd("Program", "Compile")
    @accels(mac="Cmd-K", win="Ctrl-Shift-K", lin="Ctrl-K")
    def progmenu_compile(self, event=None):
        prog = self._current_prog()
        if prog:
            progobj = db.getobj(prog)
            srcs_disp = self.source_displays[prog]
            progobj.sources = srcs_disp.get('1.0', 'end-1c')
            self.compile_program(prog)

    @menu_cmd("Program", "Run...")
    @accels(mac="Cmd-R", win="Ctrl-R", lin="Ctrl-R")
    @enable_test('allow_run')
    def progmenu_run(self, event=None):
        command = askstring(
            "Run program",
            "What argument string should the program be run with?",
            initialvalue="",
            parent=self.root,
        )
        self.cons_in.focus()
        if command is None:
            return
        prog = self._current_prog()
        self.reset_execution(prog=prog, command=command)
        self.update_displays()

    @separator
    @menu_cmd("Program", "Step Instruction")
    @accels(mac="Ctrl-I", win="Ctrl-Shift-I", lin="Ctrl-Shift-I")
    @enable_test('allow_debug')
    def progmenu_step_inst(self, event=None):
        currproc = self._selected_process()
        if not currproc:
            return
        currproc.set_break_insts(1)
        self.resume_execution()

    @menu_cmd("Program", "Step Line")
    @accels(mac="Ctrl-S", win="Ctrl-Shift-S", lin="Ctrl-Shift-S")
    @enable_test('allow_debug')
    def progmenu_step_line(self, event=None):
        currproc = self._selected_process()
        if not currproc:
            return
        currproc.set_break_steps(1)
        self.resume_execution()

    @menu_cmd("Program", "Next Line")
    @accels(mac="Ctrl-N", win="Ctrl-Shift-N", lin="Ctrl-Shift-N")
    @enable_test('allow_debug')
    def progmenu_next_line(self, event=None):
        currproc = self._selected_process()
        if not currproc:
            return
        currproc.set_break_lines(1)
        self.resume_execution()

    @menu_cmd("Program", "Finish Function")
    @accels(mac="Ctrl-F", win="Ctrl-Shift-F", lin="Ctrl-Shift-F")
    @enable_test('allow_debug')
    def progmenu_finish(self, event=None):
        currproc = self._selected_process()
        if not currproc:
            return
        currproc.set_break_on_finish(True)
        self.resume_execution()

    @menu_cmd("Program", "Continue Execution")
    @accels(mac="Ctrl-C", win="Ctrl-Shift-C", lin="Ctrl-Shift-C")
    @enable_test('allow_debug')
    def progmenu_continue(self, event=None):
        currproc = self._selected_process()
        if not currproc:
            return
        currproc.reset_breaks()
        self.resume_execution()

    @separator
    @menu_check("Program", "Trace", 'dotrace')
    @accels(mac="Cmd-T", win="Ctrl-Shift-T", lin="Ctrl-Shift-T")
    @enable_test('allow_run')
    def progmenu_trace(self, event=None):
        if event:
            self.dotrace.set('0' if self.dotrace.get() != '0' else '1')
        currproc = self._selected_process()
        if currproc:
            currproc.set_trace(self.dotrace.get() != '0')

    @separator
    @menu_cmd("Program", "Register as...")
    @accels(mac="Cmd-Shift-R", win="Ctrl-Shift-R", lin="Ctrl-Shift-R")
    @enable_test('allow_run')
    def progmenu_register(self, event=None):
        prog = self._current_prog()
        if not prog:
            return
        progobj = db.getobj(prog)
        regname = os.path.basename(progobj.name)
        if regname.endswith('.muv') or regname.endswith('.muf'):
            regname = regname[:-4]
        regname = askstring(
            "Register as...",
            "What should this program be registered as?",
            initialvalue=regname,
            parent=self.root,
        )
        self.cons_in.focus()
        if not regname:
            return 'break'
        userobj = db.get_player_obj("John_Doe")
        globenv = db.get_registered_obj(userobj, "$globalenv")
        db.register_obj(globenv, regname, progobj)
        return 'break'

    def helpmenu_help_dlog(self):
        # TODO: implement!
        print("Display help dlog.")

    def main(self):
        self.root.mainloop()
        self.filemenu_quit()


def main():
    MufGui().main()


if __name__ == "__main__":
    main()


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
