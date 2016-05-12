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
except ImportError:  # Python 3
    from tkinter import *  # noqa
    from tkinter.simpledialog import askstring
    from tkinter.filedialog import askopenfilename
    from tkinter.messagebox import showinfo
    from tkinter.font import Font

from mufgui.tooltip import CreateToolTip
from mufgui.listdisplay import ListDisplay

import mufsim.stackitems as si
import mufsim.gamedb as db
from mufsim.logger import log, warnlog, errlog, set_output_command
from mufsim.compiler import MufCompiler
from mufsim.stackframe import MufStackFrame

mufsim_version = None
menu_item_handlers = []


# Decorator declarations
def menu_item(menu_name, label, plats=["Windows", "Darwin", "Linux"]):
    def func_decorator(func):
        if platform.system() in plats:
            func.menu_name = menu_name
            func.menu_label = label
            global menu_item_handlers
            menu_item_handlers.append(func.__name__)
        return func
    return func_decorator


def separator(func):
    func.separator = True
    return func


def accels(mac=None, win=None, lin=None):
    def func_decorator(func):
        if platform.system() == "Darwin":
            func.accelerator = mac
        if platform.system() == "Windows":
            func.accelerator = win
        if platform.system() == "Linux":
            func.accelerator = lin
        return func
    return func_decorator


def enable_test(tst):
    def func_decorator(func):
        func.enable_test = tst
        return func
    return func_decorator


class MufGui(object):
    def __init__(self):
        self.fr = None
        self.current_program = None
        self.call_level = 0
        self.prev_prog = -1
        self.setup_gui()
        set_output_command(self.log_to_console)
        if len(sys.argv) > 1:
            self.defer(self.handle_open_files, sys.argv[1])

    def setup_gui(self):
        self.root = Tk()
        self.root.title("MUF Debugger")
        self.root.protocol("WM_DELETE_WINDOW", self.filemenu_quit)

        self.current_program = StringVar()
        self.current_program.set("- Load a Program -")
        self.current_function = StringVar()
        self.current_function.set("")
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

        panes2.add(self.setup_gui_data_frame(panes2), minsize=100, height=200)
        panes2.add(self.setup_gui_call_frame(panes2), minsize=100, height=200)
        panes2.add(self.setup_gui_vars_frame(panes2), minsize=100, height=200)

        panes3.add(self.setup_gui_source_frame(panes3), minsize=100, height=350)
        panes3.add(self.setup_gui_tokens_frame(panes3), minsize=100, height=150)
        panes3.add(self.setup_gui_console_frame(panes3), minsize=50, height=100)

        self.gui_raise_window()
        self.update_displays()

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
        root.option_add("*Background", "gray75")
        root.option_add("*Button.highlightBackground", "gray75")
        root.option_add("*Entry.background", "white")
        root.option_add("*Entry.highlightBackground", "gray75")
        root.option_add("*Menu.disabledForeground", "#bbb")
        root.option_add("*Menu.foreground", "black")
        root.option_add("*Panedwindow.borderWidth", "1")
        root.option_add("*Panedwindow.sashRelief", "raised")
        root.option_add("*Panedwindow.sashWidth", "6")
        root.option_add("*Text.background", "white")
        root.option_add("*Text.highlightBackground", "white")
        root.option_add("*Text.font", self.sansserif)
        if platform.system() == 'Windows':
            root.option_add("*Menubutton.relief", "raised")

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

        # Make menus from methods marked with @menu_item decorator.
        # Will appear in menus in order declared.
        menu_names = []
        menus = {}
        global menu_item_handlers
        for hndlr_name in menu_item_handlers:
            hndlr = getattr(self, hndlr_name)
            if hndlr.menu_name not in menu_names:
                name = hndlr.menu_name
                menu_names.append(name)
                menus[hndlr.menu_name] = Menu(
                    self.menubar,
                    tearoff=0,
                    postcommand=lambda x=name: self.gui_menu_enabler(x),
                )
            menu = menus[hndlr.menu_name]
            if hasattr(hndlr, 'separator') and hndlr.separator:
                menu.add_separator()
            extraopts = {}
            if hasattr(hndlr, 'accelerator') and hndlr.accelerator:
                accel = hndlr.accelerator
                # Standardize to proper binding format.
                accel = accel.replace('Ctrl', 'Control')
                accel = accel.replace('Cmd', 'Command')
                accel = accel.replace('Opt', 'Option')
                accel = accel.replace('+', '-')
                if '-' in accel:
                    mods, key = accel.rsplit('-', 1)
                    mods += '-'
                else:
                    mods = ''
                    key = accel
                # Tk is odd about how it handles Caps Lock.
                # <a> triggers only if CapsLock and Shift are off.
                # <A> triggers only if CapsLock or Shift is on.
                # <Shift-a> never ever triggers for ANY key combination.
                # <Shift-A> triggers only when Shift is pressed.
                # <Shift-A> has priority over <Command-A>
                # May as well bind for both upper and lowercase key.
                key_u = key.upper() if len(key) == 1 else key
                self.root.bind(
                    "<%s%s>" % (mods, key_u),
                    self.defer_evt(hndlr)  # Prevents some window deadlocks
                )
                key_l = key.lower() if len(key) == 1 else key
                self.root.bind(
                    "<%s%s>" % (mods, key_l),
                    self.defer_evt(hndlr)  # Prevents some window deadlocks
                )
                if platform.system() == "Windows":
                    # Standardize menu accelerator for Windows
                    menuaccel = "%s%s" % (mods, key.upper()),
                    menuaccel.replace('Control', 'CTRL')
                    menuaccel.replace('Alt', 'ALT')
                    menuaccel.replace('Shift', 'SHIFT')
                    menuaccel.replace('-', '+')
                else:
                    # Always show uppercase letter in menu accelerator.
                    menuaccel = "%s%s" % (mods, key_u),
                extraopts['accel'] = menuaccel
            menu.add_command(
                label=hndlr.menu_label,
                command=self.defer(hndlr),  # Prevents some window deadlocks
                **extraopts
            )
        for menu_name in menu_names:
            self.menubar.add_cascade(label=menu_name, menu=menus[menu_name])
        if platform.system() == 'Darwin':
            self.helpmenu = Menu(self.menubar, name="help", tearoff=0)
            # self.root.createcommand(
            #     'tk::mac::ShowHelp', self.helpmenu_help_dlog)
            self.menubar.add_cascade(label="Help", menu=self.helpmenu)
        self.menus = menus
        return self.menubar

    def setup_gui_data_frame(self, master):
        datafr = LabelFrame(master, text="Data Stack", relief="flat", borderwidth=0)
        self.data_disp = ListDisplay(datafr, readonly=True, gutter=4)
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
        callfr = LabelFrame(master, text="Call Stack", relief="flat", borderwidth=0)
        self.call_disp = ListDisplay(callfr, readonly=True, gutter=4)
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
        varsfr = LabelFrame(master, text="Variables", relief="flat", borderwidth=0)
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

    def setup_gui_source_selectors_frame(self, master):
        srcselfr = Frame(master)
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
        self.comp_btn = Button(
            srcselfr, text="Compile", command=self.debugmenu_compile)
        self.src_lbl.pack(side=LEFT, fill=NONE, expand=0)
        self.src_sel.pack(side=LEFT, fill=NONE, expand=0)
        self.fun_lbl.pack(side=LEFT, fill=NONE, expand=0)
        self.fun_sel.pack(side=LEFT, fill=NONE, expand=0)
        self.comp_btn.pack(side=LEFT, fill=NONE, expand=0)
        return srcselfr

    def setup_gui_source_display_frame(self, master):
        srcdispfr = Frame(master)
        self.srcs_disp = ListDisplay(srcdispfr, font=self.monospace, gutter=5)
        self.srcs_disp.gutter.bind(
            '<Button-1>', self.handle_sources_breakpoint_toggle)
        self.srcs_disp.tag_config(
            'hilite', background="#aff", foreground="black")
        self.srcs_disp.tag_config(
            'error', background="#faa", foreground="black")
        self.srcs_disp.tag_config(
            'warning', background="#ffa", foreground="black")
        self.srcs_disp.tag_config(
            'currline', background="#77f", foreground="white")
        self.srcs_disp.gutter.tag_config(
            'breakpt', background="#447", foreground="white")
        self.srcs_disp.pack(side=BOTTOM, fill=BOTH, expand=1)
        CreateToolTip(
            self.srcs_disp.gutter,
            'Click on line number to toggle breakpoint.',
        )
        return srcdispfr

    def setup_gui_source_frame(self, master):
        srcfr = Frame(master)
        srcselfr = self.setup_gui_source_selectors_frame(srcfr)
        srcdispfr = self.setup_gui_source_display_frame(srcfr)
        srcselfr.pack(side=TOP, fill=X, expand=0)
        srcdispfr.pack(side=BOTTOM, fill=BOTH, expand=1)
        return srcfr

    def setup_gui_tokens_display_frame(self, master):
        tokfr = LabelFrame(master, text="Tokens", relief="flat", borderwidth=0)
        self.tokn_disp = ListDisplay(
            tokfr,
            font=self.monospace,
            readonly=True,
            gutter=5,
        )
        self.tokn_disp.tag_config(
            'func', foreground="#00c", font=self.monospace_b)
        self.tokn_disp.tag_config(
            'hilite', background="#aff", foreground="black")
        self.tokn_disp.tag_config(
            'currline', background="#77f", foreground="white")
        self.tokn_disp.pack(side=TOP, fill=BOTH, expand=1)
        return tokfr

    def setup_gui_debug_buttons_frame(self, master):
        btnsfr = Frame(master)
        self.run_btn = Button(
            btnsfr, text="Run", command=self.debugmenu_run)
        self.stepi_btn = Button(
            btnsfr, text="Inst", command=self.debugmenu_step_inst)
        self.stepl_btn = Button(
            btnsfr, text="Step", command=self.debugmenu_step_line)
        self.nextl_btn = Button(
            btnsfr, text="Next", command=self.debugmenu_next_line)
        self.finish_btn = Button(
            btnsfr, text="Finish", command=self.debugmenu_finish)
        self.cont_btn = Button(
            btnsfr, text="Cont", command=self.debugmenu_continue)
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
        CreateToolTip(self.run_btn, 'Run program from the start.')
        CreateToolTip(self.stepi_btn, 'Execute one instruction.')
        CreateToolTip(self.stepl_btn, 'Step one line, following calls.')
        CreateToolTip(self.nextl_btn, 'Next line, stepping over calls.')
        CreateToolTip(self.finish_btn, 'Finish the current function.')
        CreateToolTip(self.cont_btn, 'Continue execution.')
        CreateToolTip(self.trace_chk, 'Show stack trace for each instruction.')
        return btnsfr

    def setup_gui_tokens_frame(self, master):
        tokfr = Frame(master)
        tokdispfr = self.setup_gui_tokens_display_frame(tokfr)
        btnsfr = self.setup_gui_debug_buttons_frame(tokfr)
        btnsfr.pack(side=BOTTOM, fill=X, expand=0)
        tokdispfr.pack(side=BOTTOM, fill=BOTH, expand=1)
        return tokfr

    def setup_gui_console_frame(self, master):
        consfr = Frame(master)
        self.cons_disp = ListDisplay(
            consfr,
            height=1,
            readonly=True,
            font=self.monospace
        )
        self.cons_disp.tag_config('good', foreground="#0a0")
        self.cons_disp.tag_config('trace', foreground="#777")
        self.cons_disp.tag_config('warning', foreground="#880")
        self.cons_disp.tag_config('error', foreground="#c00")
        self.cons_in = Entry(consfr, relief=SUNKEN)
        self.cons_disp.pack(side=TOP, fill=BOTH, expand=1)
        self.cons_in.pack(side=TOP, fill=X, expand=0)
        self.cons_in.focus()
        return consfr

    def gui_menu_enabler(self, menu_name):
        menu = self.menus[menu_name]
        global menu_item_handlers
        for hndlr_name in menu_item_handlers:
            hndlr = getattr(self, hndlr_name)
            if menu_name == hndlr.menu_name:
                if hasattr(hndlr, 'enable_test') and hndlr.enable_test:
                    test = getattr(self, hndlr.enable_test)
                    state = "disabled"
                    color = "#bbb"
                    if test():
                        state = "normal"
                        color = "black"
                    idx = menu.index(hndlr.menu_label)
                    menu.entryconfig(idx, state=state)
                    menu.entryconfig(idx, foreground=color)

    def allow_run(self):
        return self.fr is not None

    def allow_debug(self):
        return self.fr and self.fr.get_call_stack()

    def appmenu_prefs_dlog(self):
        # TODO: implement!
        print("Display preferences dlog.")

    @menu_item("File", "Open Program...")
    @accels(mac="Cmd-O", win="Ctrl-O", lin="Ctrl-O")
    def filemenu_load_program(self, event=None):
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

    @menu_item("File", "Open Library...")
    @accels(mac="Cmd-L", win="Ctrl-L", lin="Ctrl-L")
    def filemenu_load_library(self, event=None):
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

    @separator
    @menu_item("File", "Exit", plats=["Windows"])
    @menu_item("File", "Quit", plats=["Linux"])
    @accels(win="Alt-F4", lin="Ctrl-Q")
    def filemenu_quit(self):
        try:
            self.root.destroy()
        except:
            pass

    @menu_item("Edit", "Cut")
    @accels(mac="Cmd-X", win="Ctrl-X", lin="Ctrl-X")
    def editmenu_cut(self):
        self.gen_foc_ev("Cut"),

    @menu_item("Edit", "Copy")
    @accels(mac="Cmd-C", win="Ctrl-C", lin="Ctrl-C")
    def editmenu_copy(self):
        self.gen_foc_ev("Copy"),

    @menu_item("Edit", "Paste")
    @accels(mac="Cmd-V", win="Ctrl-V", lin="Ctrl-V")
    def editmenu_paste(self):
        self.gen_foc_ev("Paste"),

    @separator
    @menu_item("Edit", "Clear")
    @accels(mac="Delete", win="Delete", lin="Delete")
    def editmenu_clear(self):
        self.gen_foc_ev("Clear"),

    @menu_item("Debug", "Compile")
    @accels(mac="Cmd-K", win="Ctrl-Shift-K", lin="Ctrl-Shift-K")
    def debugmenu_compile(self, event=None):
        prog = self._get_prog_from_selector()
        if prog:
            progobj = db.getobj(prog)
            progobj.sources = self.srcs_disp.get('1.0', 'end-2c')
            self.compile_program(prog)

    @menu_item("Debug", "Run...")
    @accels(mac="Cmd-R", win="Ctrl-Shift-R", lin="Ctrl-Shift-R")
    @enable_test('allow_run')
    def debugmenu_run(self, event=None):
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

    @separator
    @menu_item("Debug", "Step Instruction")
    @accels(mac="Ctrl-I", win="Ctrl-Shift-I", lin="Ctrl-Shift-I")
    @enable_test('allow_debug')
    def debugmenu_step_inst(self, event=None):
        self.fr.set_break_insts(1)
        self.resume_execution()

    @menu_item("Debug", "Step Line")
    @accels(mac="Ctrl-S", win="Ctrl-Shift-S", lin="Ctrl-Shift-S")
    @enable_test('allow_debug')
    def debugmenu_step_line(self, event=None):
        self.fr.set_break_steps(1)
        self.resume_execution()

    @menu_item("Debug", "Next Line")
    @accels(mac="Ctrl-N", win="Ctrl-Shift-N", lin="Ctrl-Shift-N")
    @enable_test('allow_debug')
    def debugmenu_next_line(self, event=None):
        self.fr.set_break_lines(1)
        self.resume_execution()

    @menu_item("Debug", "Finish Function")
    @accels(mac="Ctrl-F", win="Ctrl-Shift-F", lin="Ctrl-Shift-F")
    @enable_test('allow_debug')
    def debugmenu_finish(self, event=None):
        self.fr.set_break_on_finish(True)
        self.resume_execution()

    @menu_item("Debug", "Continue Execution")
    @accels(mac="Ctrl-C", win="Ctrl-Shift-C", lin="Ctrl-Shift-C")
    @enable_test('allow_debug')
    def debugmenu_continue(self, event=None):
        self.fr.reset_breaks()
        self.resume_execution()

    def helpmenu_help_dlog(self):
        # TODO: implement!
        print("Display help dlog.")

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

    def handle_stack_item_dblclick(self, event):
        w = event.widget
        index = w.index("@%s,%s" % (event.x, event.y))
        if index and self.fr:
            item = int(float(index))
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

    def handle_source_selector_change(self):
        prog = self._get_prog_from_selector()
        if prog is not None:
            self.update_sourcecode_from_program(prog)

    def handle_function_selector_change(self):
        self.srcs_disp.tag_remove('hilite', '0.0', END)
        self.tokn_disp.tag_remove('hilite', '0.0', END)
        prog = self._get_prog_from_selector()
        if prog is None:
            return
        if not self.current_function.get():
            return
        fun = self.current_function.get()
        addr = self.fr.program_function_addr(prog, fun)
        line = self.fr.get_inst_line(addr)
        self.srcs_disp.tag_add(
            'hilite',
            '%d.0' % line,
            '%d.end+1c' % line,
        )
        self.tokn_disp.tag_add(
            'hilite',
            '%d.0' % (addr.value + 1),
            '%d.end+1c' % (addr.value + 1),
        )
        self.srcs_disp.see('%d.0' % line)
        self.tokn_disp.see('%d.0' % (addr.value + 1))

    def handle_sources_breakpoint_toggle(self, event):
        if not self.fr:
            return
        w = event.widget
        index = w.index("@%s,%s" % (event.x, event.y))
        line = int(float(index))
        prog = self._get_prog_from_selector()
        if prog is None:
            return
        bpnum = self.fr.find_breakpoint(prog, line)
        if bpnum is not None:
            self.fr.del_breakpoint(bpnum)
        else:
            self.fr.add_breakpoint(prog, line)
        self.update_sourcecode_breakpoints(prog)

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

    def handle_trace(self, event=None):
        if self.fr:
            self.fr.set_trace(self.dotrace.get() != '0')

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

    def gen_foc_ev(self, virt):
        return "event generate [focus] <<%s>>" % virt

    def defer(self, *args):
        return lambda: self.root.after(10, *args)

    def defer_evt(self, cmd):
        return lambda e: self.root.after(10, cmd)

    def clear_errors(self):
        self.errors_queue = []

    def update_errors(self):
        first = True
        for line, typ, msg in self.errors_queue:
            self.srcs_disp.tag_add(typ, '%d.0' % line, '%d.end+1c' % line)
            # CreateToolTip(self.srcs_disp, msg, tag=typ)
            if first:
                first = False
                self.srcs_disp.see('%d.0' % line)

    def log_to_console(self, msgtype, msg):
        m = re.match(r'^(Warning|Error) in line (\d+): (.*)$', msg)
        if m:
            errtype = m.group(1).lower()
            errline = int(m.group(2))
            errmsg = m.group(3)
            self.errors_queue.append((errline, errtype, errmsg))
        self.cons_disp.insert(END, msg + "\n", msgtype)
        self.cons_disp.see('end linestart')

    def _get_prog_from_selector(self):
        if self.current_program.get().startswith('- '):
            return None
        prog = self.current_program.get()
        prog = prog.split('(#', 1)[1]
        prog = prog.split(')', 1)[0]
        return int(prog)

    def update_program_selector(self):
        self.src_sel.menu.delete(0, END)
        progs = db.get_all_programs()
        if not progs:
            self.current_program.set("- Load a Program -")
        for prog in progs:
            progobj = db.getobj(prog)
            name = "%s(%s)" % (progobj.name, prog)
            self.src_sel.menu.add_radiobutton(
                label=name, value=name,
                variable=self.current_program,
                command=self.handle_source_selector_change,
            )
            if self.fr:
                addr = self.fr.call_addr(self.call_level)
                if addr and prog.value == addr.prog:
                    self.current_program.set(name)
            elif prog == progs[0]:
                self.current_program.set(name)
        self.src_sel.menu.add_separator()
        self.src_sel.menu.add_command(
            label="Load Program...",
            command=self.filemenu_load_program,
        )
        self.src_sel.menu.add_command(
            label="Load Library...",
            command=self.filemenu_load_library,
        )

    def update_function_selector(self):
        prog = self._get_prog_from_selector()
        if prog is None:
            prog = -1
        if self.fr:
            addr = self.fr.call_addr(self.call_level)
            if addr:
                prog = addr.prog
        self.fun_sel.menu.delete(0, END)
        if not db.validobj(prog):
            self.current_function.set("")
            return
        funs = []
        comp = db.getobj(prog).compiled
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
            line = '%s\n' % si.item_repr(val)
            self.data_disp.insert(END, line, 'sitem')
        self.data_disp.delete('end-1c', END)
        self.data_disp.see('0.0')

    def update_call_stack_display(self):
        self.call_disp.tag_remove('currline', '0.0', END)
        fmt = "{progname}({prog}), {func}, {line}\n"
        self.call_disp.delete('0.0', END)
        if not self.fr or not self.fr.get_call_stack():
            self.call_disp.insert('0.0', ' - NOT RUNNING - ', 'empty')
            return
        for callinfo in self.fr.get_call_stack():
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

    def update_sourcecode_from_program(self, prog, force=False):
        if prog != self.prev_prog or force:
            if not db.validobj(prog):
                return
            self.prev_prog = prog
            progobj = db.getobj(prog)
            srcs = []
            if progobj.sources:
                srcs = progobj.sources.split("\n")
            self.srcs_disp.delete('0.0', END)
            for i, srcline in enumerate(srcs):
                line = "%s\n" % srcline
                self.srcs_disp.insert(END, line)
            self.tokn_disp.delete('end-1c', END)

            tokens = []
            if progobj.compiled:
                tokens = progobj.compiled.get_tokens_info()
            self.tokn_disp.delete('0.0', END)
            for i, token in enumerate(tokens):
                rep = token['repr']
                line = "%s\n" % rep
                if rep.startswith('Function:'):
                    self.tokn_disp.insert(END, line, "func")
                else:
                    self.tokn_disp.insert(END, line)
            self.tokn_disp.delete('end-1c', END)

    def update_sourcecode_breakpoints(self, prog):
        self.srcs_disp.gutter.tag_remove('breakpt', '0.0', END)
        for bpprog, line in self.fr.get_breakpoints():
            if bpprog == prog:
                self.srcs_disp.gutter.tag_add(
                    'breakpt',
                    '%d.0' % line,
                    '%d.5' % line
                )

    def update_sourcecode_display(self):
        self.srcs_disp.tag_remove('hilite', '0.0', END)
        self.tokn_disp.tag_remove('hilite', '0.0', END)
        self.srcs_disp.tag_remove('currline', '0.0', END)
        self.tokn_disp.tag_remove('currline', '0.0', END)
        selprog = self._get_prog_from_selector()
        addr = None
        if self.fr:
            addr = self.fr.call_addr(self.call_level)
            if addr:
                selprog = addr.prog
        if selprog is None:
            selprog = db.get_registered_obj(1, "$cmd/test")
        self.update_sourcecode_from_program(selprog)
        if not self.fr:
            return
        if not addr:
            return
        inst = self.fr.get_inst(addr)
        self.srcs_disp.tag_add(
            'currline',
            '%d.0' % inst.line,
            '%d.end+1c' % inst.line,
        )
        self.tokn_disp.tag_add(
            'currline',
            '%d.0' % (addr.value + 1),
            '%d.end+1c' % (addr.value + 1),
        )
        self.update_sourcecode_breakpoints(selprog)
        self.srcs_disp.see('%d.0 - 2l' % inst.line)
        self.srcs_disp.see('%d.0 + 2l' % inst.line)
        self.srcs_disp.see('%d.0' % inst.line)
        self.tokn_disp.see('%d.0 - 1l' % (addr.value + 1))
        self.tokn_disp.see('%d.0 + 1l' % (addr.value + 1))
        self.tokn_disp.see('%d.0' % (addr.value + 1))

    def update_displays(self, level=-1):
        if self.fr and level < 0:
            level = len(self.fr.get_call_stack()) + level
        self.call_level = level
        self.update_buttonbar()
        self.update_program_selector()
        self.update_function_selector()
        self.update_call_stack_display()
        self.update_data_stack_display()
        self.update_variables_display()
        self.update_sourcecode_display()

    def update_buttonbar(self):
        runstate = "normal" if self.allow_run() else "disabled"
        livestate = "normal" if self.allow_debug() else "disabled"
        self.run_btn.config(state=runstate)
        livebtns = [
            self.stepi_btn,
            self.stepl_btn,
            self.nextl_btn,
            self.finish_btn,
            self.cont_btn,
        ]
        for btn in livebtns:
            btn.config(state=livestate)

    def compile_program(self, prog):
        self.clear_errors()
        self.fr = None
        success = MufCompiler().compile_source(prog)
        self.update_sourcecode_from_program(prog, force=True)
        if not success:
            errlog("MUF tokenization failed!")
        else:
            log("MUF tokenization successful.", msgtype="good")
            self.reset_execution()
            self.update_displays()
            self.fr.call_stack = []
        self.update_errors()
        self.update_displays()

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
        self.compile_program(progobj.dbref)

    def main(self):
        self.root.mainloop()
        self.filemenu_quit()


def main():
    MufGui().main()


if __name__ == "__main__":
    main()


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
