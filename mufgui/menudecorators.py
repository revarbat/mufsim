import platform

try:  # Python 2
    from Tkinter import *  # noqa
except ImportError:  # Python 3
    from tkinter import *  # noqa


menu_item_handlers = []


# Decorator declarations
def menu_cmd(menu_name, label, plats=["Windows", "Darwin", "Linux"]):
    def func_decorator(func):
        if platform.system() in plats:
            func.menu_name = menu_name
            func.menu_label = label
            func.menu_item_type = "command"
            global menu_item_handlers
            menu_item_handlers.append(func.__name__)
        return func
    return func_decorator


def menu_check(
    menu_name, label,
    var, onvalue="1", offvalue="0",
    plats=["Windows", "Darwin", "Linux"]
):
    def func_decorator(func):
        if platform.system() in plats:
            func.menu_name = menu_name
            func.menu_label = label
            func.menu_item_type = "check"
            func.variable = var
            func.on_value = onvalue
            func.off_value = offvalue
            global menu_item_handlers
            menu_item_handlers.append(func.__name__)
        return func
    return func_decorator


def menu_radio(
    menu_name, label,
    var, value="1",
    plats=["Windows", "Darwin", "Linux"]
):
    def func_decorator(func):
        if platform.system() in plats:
            func.menu_name = menu_name
            func.menu_label = label
            func.menu_item_type = "radio"
            func.variable = var
            func.value = value
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


def process_enablers(obj, menu_name=None):
    global menu_item_handlers
    for hndlr_name in menu_item_handlers:
        hndlr = getattr(obj, hndlr_name)
        if not menu_name or menu_name == hndlr.menu_name:
            menu = obj.menus_by_name[hndlr.menu_name]
            if hasattr(hndlr, 'enable_test') and hndlr.enable_test:
                test = getattr(obj, hndlr.enable_test)
                state = "disabled"
                color = "#bbb"
                if test():
                    state = "normal"
                    color = "black"
                idx = menu.index(hndlr.menu_label)
                menu.entryconfig(idx, state=state)
                if platform.system() == "Darwin":
                    menu.entryconfig(idx, foreground=color)


def create_menus(obj, master, menubar):
    """
    Make menus from methods marked with @menu_cmd decorator.
    Will appear in menus in order declared.
    """
    menu_names = []
    obj.menus_by_name = {}
    global menu_item_handlers
    for hndlr_name in menu_item_handlers:
        hndlr = getattr(obj, hndlr_name)
        if hndlr.menu_name not in menu_names:
            name = hndlr.menu_name
            menu_names.append(name)
            menu = Menu(menubar, tearoff=0)
            obj.menus_by_name[hndlr.menu_name] = menu
            menu.config(
                postcommand=lambda o=obj, n=name: process_enablers(o, n)
            )
        menu = obj.menus_by_name[hndlr.menu_name]
        if hasattr(hndlr, 'separator') and hndlr.separator:
            menu.add_separator()
        extraopts = {}
        if hasattr(hndlr, 'accelerator') and hndlr.accelerator:
            accel = hndlr.accelerator
            # Standardize to proper binding format.
            replacements = [
                ('Ctrl', 'Control'),
                ('Cmd', 'Command'),
                ('Opt', 'Option'),
                ('[', 'bracketleft'),
                (']', 'bracketright'),
                ('+', '-'),
            ]
            for find, repl in replacements:
                accel = accel.replace(find, repl)
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
            master.bind(
                "<%s%s>" % (mods, key_u),
                lambda e, h=hndlr: master.after(100, h, e)
            )
            key_l = key.lower() if len(key) == 1 else key
            master.bind(
                "<%s%s>" % (mods, key_l),
                lambda e, h=hndlr: master.after(100, h, e)
            )
            if platform.system() == "Windows":
                # Standardize menu accelerator for Windows
                menuaccel = "%s%s" % (mods, key.title())
                menuaccel = menuaccel.replace('Control', 'Ctrl')
                menuaccel = menuaccel.replace('Alt', 'Alt')
                menuaccel = menuaccel.replace('Shift', 'Shift')
                menuaccel = menuaccel.replace('-', '+')
            else:
                # Always show uppercase letter in menu accelerator.
                menuaccel = "%s%s" % (mods, key_u.title())
            replacements = [
                ('Bracketleft', '['),
                ('Bracketright', ']'),
            ]
            for find, repl in replacements:
                menuaccel = menuaccel.replace(find, repl)
            extraopts['accel'] = menuaccel
        if hndlr.menu_item_type == "command":
            menu.add_command(
                label=hndlr.menu_label,
                command=lambda h=hndlr: master.after(100, h),
                **extraopts
            )
        elif hndlr.menu_item_type == "check":
            if isinstance(hndlr.variable, str):
                var = getattr(obj, hndlr.variable)
            else:
                var = hndlr.variable
            menu.add_checkbutton(
                label=hndlr.menu_label,
                command=lambda h=hndlr: master.after(100, h),
                variable=var,
                onvalue=hndlr.on_value,
                offvalue=hndlr.off_value,
                **extraopts
            )
        elif hndlr.menu_item_type == "radio":
            if isinstance(hndlr.variable, str):
                var = getattr(obj, hndlr.variable)
            else:
                var = hndlr.variable
            menu.add_radiobutton(
                label=hndlr.menu_label,
                command=lambda h=hndlr: master.after(100, h),
                variable=var,
                onvalue=hndlr.value,
                **extraopts
            )
    for menu_name in menu_names:
        menubar.add_cascade(
            label=menu_name,
            menu=obj.menus_by_name[menu_name]
        )
    return obj.menus_by_name


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
