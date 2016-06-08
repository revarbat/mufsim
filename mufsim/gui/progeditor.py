try:  # Python 2
    from Tkinter import *  # noqa
except ImportError:  # Python 3
    from tkinter import *  # noqa

from mufsim.gui.listdisplay import ListDisplay


def _getstring(txt):
    txt = txt[1:]
    out = '"'
    while txt:
        if txt.startswith('\\'):
            out += txt[:2]
            txt = txt[2:]
            continue
        if txt.startswith('"'):
            out += '"'
            txt = txt[1:]
            break
        pos = min(txt.index(c) for c in '\\"')
        out += txt[:pos]
        txt = txt[pos:]
    return out, txt


def _words(txt):
    words = []
    startlen = len(txt)
    txt = txt.strip()
    while txt:
        pos = startlen - len(txt)
        if txt.startswith('"'):
            word, txt = _getstring(txt)
        elif ' ' in txt:
            word, txt = txt.split(' ')
            txt = txt.strip()
        else:
            word, txt = txt, ''
        words.append((word, pos))
    return words


class ProgramEditor(ListDisplay):
    def __init__(self, master, **kwargs):
        self.incr_words = [
            ":", "begin", "for", "foreach", "if", "else",
            "try", "catch", "catch_detailed",
        ]
        self.decr_words = [
            ";", "repeat", "until", "else", "then",
            "catch", "catch_detailed", "endcatch",
        ]
        self.keywords = list(set(self.incr_words + self.decr_words))
        self.comment_prefix = "("
        self.comment_suffix = ")"
        self.syntax_colors = {
            'funcdef': dict(foreground='#070'),
            'keyword': dict(foreground='#077'),
            'comment': dict(foreground='#777'),
            'mufprim': dict(foreground='#770'),
            'string': dict(foreground='#707'),
            'error': dict(foreground='#f00', underline=1),
        }
        kwargs.setdefault('font', ("Courier", "12"))
        kwargs.setdefault('gutterfont', kwargs['font'])
        kwargs.setdefault('gutter', 5)
        kwargs.setdefault('undo', True)
        kwargs.setdefault('autoseparators', True)
        kwargs.setdefault('maxundo', 1000)
        kwargs.setdefault('readonly', False)
        kwargs.setdefault('basecount', 1)
        ListDisplay.__init__(
            self, master,
            **kwargs
        )
        for tag, attrs in self.syntax_colors.items():
            self.tag_config('_ed_' + tag, **attrs)
        self.bind('<Key-Return>', self.handle_key_enter)
        self.bind('<Key-space>', self.handle_key_space)
        self.bind("<Key-Tab>", self.handle_key_tab)

    def handle_key_tab(self, event):
        self.insert(INSERT, "    ")
        return 'break'

    def handle_key_enter(self, event=None):
        prevline = self.get('insert-1l linestart', 'insert-1l lineend')
        line = self.get('insert linestart', 'insert lineend')
        previndent = len(prevline) - len(prevline.lstrip(' '))
        indent = len(line) - len(line.lstrip(' '))
        incs = decs = 0
        for word, pos in _words(line):
            if word in self.incr_words:
                incs = 1
            if line.strip().startswith(word) and word in self.decr_words:
                decs = 1
        if decs and indent - previndent >= 0:
            self.delete('insert linestart', 'insert lineend')
            self.insert(
                INSERT,
                (' ' * (indent + 4 * (incs-decs))) + line.lstrip()
            )
            indent -= 4 * decs
        self.insert(INSERT, "\n" + ' ' * (indent + 4 * incs))
        return 'break'

    def handle_key_space(self, event=None):
        return


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
