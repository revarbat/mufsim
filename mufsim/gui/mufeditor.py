try:  # Python 2
    from Tkinter import *  # noqa
except ImportError:  # Python 3
    from tkinter import *  # noqa

import mufsim.utils as util
from mufsim.logger import log
from mufsim.gui.listdisplay import ListDisplay
from mufsim.insts.base import primitives
from mufsim.compiler import MufCompiler


class MufEditor(ListDisplay):
    def __init__(self, master, **kwargs):
        self.syntax_mode = "muf"
        self.scheduled_update = False
        self.dirty_lines = []

        self.syntax_data = {
            "muf": {
                "incr": [
                    ":", "begin", "for", "foreach", "if", "else",
                    "try", "catch", "catch_detailed", "{",
                ],
                "decr": [
                    ";", "repeat", "until", "else", "then",
                    "catch", "catch_detailed", "endcatch",
                    "}array", "}list", "}dict", "}join", "}cat", "}tell",
                ],
                "keywords": [
                    ":", ";", "begin", "for", "foreach", "repeat", "until",
                    "if", "else", "then", "try", "exit",
                    "catch", "catch_detailed", "endcatch",
                    "{", "}array", "}list", "}dict", "}join", "}cat", "}tell",
                ],
                "declared": [':', 'lvar', 'var'],
                "wordseps": [r'(?ms)(\S+)\s*(.*$)'],
                "comments": {
                    "line": None,
                    "multi": ("(", ")"),
                },
            },
            "muv": {
                "incr": ['{', '('],
                "decr": ['}', ')'],
                "keywords": [
                    "func", "for", "while", "until", "if", "else",
                    "try", "catch", "break", "continue", "var", "const",
                    "switch", "case", "default", "using", "namespace",
                    "return", "include", "by", "del", "eq", "extern",
                    "fmtstring", "muf", "multiple", "single", "void",
                    "public", "push", "top", "unless", "in", "=>", ",",
                    "abort", "throw", "tell", "count", "cat", "haskey",
                    "me", "loc", "trigger", "command", "true", "false",
                    "$author", "$echo", "$error", "$include",
                    "$language", "$libversion", "$note", "$pragma",
                    "$version", "$warn", ",",
                    "=", "==", "!=", "<", ">", "<=", ">=", "&&", "||",
                    "^^", "!", "^", "+=", "-=", "*=", "/=", "%=",
                    "<<=", ">>=", "&=", "|=", "^=", "**=",
                    "+", "-", "*", "/", "%", "**", "&", "|", "^",
                ],
                "declared": ['func', 'var', 'const', 'namespace'],
                "wordseps": [
                    r'([a-z_$][a-z_0-9]*\??)\s*(.*$)',
                    r'(\d*\.\d+[eE][+-]?\d+)\s*(.*$)',
                    r'(\d+\.\d*[eE][+-]?\d+)\s*(.*$)',
                    r'(\d+[eE][+-]?\d+)\s*(.*$)',
                    r'(\d*\.\d+)\s*(.*$)',
                    r'(\d+\.\d*)\s*(.*$)',
                    r'([0-9]+)\s*(.*$)',
                    r'([-+*/%^&|=!]=?|<<?=?|>>?=?|&&|[|][|]|[*][*]=?|=>|\?|[][,;:.(){}])\s*(.*$)',  # noqa
                ],
                "comments": {
                    "line": "//",
                    "multi": ("/*", "*/"),
                },
            },
        }
        self.syntax_colors = {
            'comment': dict(foreground='#999'),
            'string': dict(foreground='#80f'),
            'number': dict(foreground='#090'),
            'declared': dict(foreground='#00f'),
            'keyword': dict(foreground='#0aa'),
            'mufprim': dict(foreground='#750'),
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
        self.bind('<Key-BackSpace>', self.handle_key_backspace)
        self.bind('<Key-Return>', self.handle_key_enter)
        self.bind("<Key-Tab>", self.handle_key_tab)
        self.bind('<Key>', self.handle_keypress)

    def _get_comment(self, txt):
        syndata = self.syntax_data[self.syntax_mode]
        linepfx = syndata['comments']['line']
        if linepfx and txt.startswith(linepfx):
            if '\n' in txt:
                out, txt = txt.split('\n', 1)
            else:
                out, txt = txt, ''
            return out, txt
        prefix, suffix = syndata['comments']['multi']
        if prefix and txt.startswith(prefix):
            out = txt[:len(prefix)]
            txt = txt[len(prefix):]
        else:
            return None, txt
        lev = 1
        commentdelims = [prefix, suffix]
        while txt:
            if txt.startswith(prefix):
                lev += 1
                out += txt[:len(prefix)]
                txt = txt[len(prefix):]
                continue
            if txt.startswith(suffix):
                lev -= 1
                out += txt[:len(suffix)]
                txt = txt[len(suffix):]
                if not lev:
                    break
            pfx, txt = util.split_char(txt, commentdelims)
            out += pfx
        return out, txt

    def _get_string(self, txt):
        if not txt.startswith('"'):
            return None, txt
        out = txt[:1]
        txt = txt[1:]
        while txt:
            if txt.startswith('\\'):
                out += txt[:2]
                txt = txt[2:]
                continue
            if txt.startswith('"'):
                out += '"'
                txt = txt[1:]
                break
            pfx, txt = util.split_char(txt, '\\"')
            out += pfx
        return out, txt

    def _words(self, txt):
        words = []
        startlen = len(txt)
        txt = txt.lstrip()
        syndata = self.syntax_data[self.syntax_mode]
        prefix, suffix = syndata['comments']['multi']
        while txt:
            start = startlen - len(txt)
            word, txt = self._get_string(txt)
            if word is None:
                word, txt = self._get_comment(txt)
            if word is None:
                for pat in syndata['wordseps']:
                    m = re.match(pat, txt, re.I)
                    if m:
                        word = m.group(1)
                        txt = m.group(2)
                        break
            if word is None:
                word = txt
                txt = ''
            end = startlen - len(txt)
            txt = txt.lstrip()
            words.append((word, start, end))
        return words

    def _syntax_hilite_all(self):
        end = int(self.index(END).split('.', 1)[0])
        self.dirty_lines = list(range(1, end))
        self._schedule_update()

    def _syntax_hilite_line(self, pos):  # noqa
        lstart = self.index('%s linestart' % pos)
        lend = self.index('%s lineend' % pos)
        lnum = lstart.split('.', 1)[0]
        for tag, attrs in self.syntax_colors.items():
            self.tag_remove('_ed_' + tag, lstart, lend)
        line = self.get(lstart, lend)
        if self.syntax_mode != "muv" and re.match(r'[$]language +"muv"', line):
            self.syntax_mode = "muv"
            self._syntax_hilite_all()
            return
        if self.syntax_mode != "muf" and re.match(r'[:;]', line):
            self.syntax_mode = "muf"
            self._syntax_hilite_all()
            return
        syndata = self.syntax_data[self.syntax_mode]
        keywords = syndata['keywords']
        prefix, suffix = syndata['comments']['multi']
        linepfx = syndata['comments']['line']
        next_is_declared = False
        for word, start, end in self._words(line):
            tag = None
            if linepfx and word.startswith(linepfx):
                tag = 'comment'
            elif prefix and word.startswith(prefix):
                tag = 'comment' if (
                    len(word) > len(prefix) and word.endswith(suffix)
                ) else 'error'
            elif word.startswith('"'):
                tag = 'string' if (
                    len(word) > 1 and
                    word.endswith('"')
                ) else 'error'
            elif util.is_int(word) or util.is_float(word):
                tag = 'number'
            elif util.is_dbref(word):
                tag = 'number'
            elif next_is_declared:
                tag = 'declared'
                next_is_declared = False
            elif word in keywords:
                tag = 'keyword'
            elif (
                self.syntax_mode == "muf" and
                (word in primitives or word in MufCompiler.builtin_defines)
            ):
                tag = 'mufprim'
            declared = syndata['declared']
            if word in declared:
                next_is_declared = True
            start = "%s.%d" % (lnum, start)
            end = "%s.%d" % (lnum, end)
            if tag:
                self.tag_add('_ed_' + tag, start, end)

    def handle_key_tab(self, event):
        curridx = self.index(INSERT)
        currline, currpos = [int(i) for i in curridx.split('.')]
        line = self.get('insert linestart', 'insert lineend')
        indent = len(line) - len(line.lstrip())
        toadd = 4 - (indent % 4)
        if currpos <= indent:
            self.insert('insert linestart', ' ' * toadd)
        elif not self.get("insert-1c", "insert").lstrip():
            self.insert(INSERT, ' ' * 4)
        else:
            word = self.get("insert-1c wordstart", "insert")
            words = [
                x for x in (
                    list(primitives.keys()) +
                    list(MufCompiler.builtin_defines.keys())
                )
                if x.startswith(word)
            ]
            words.sort()
            pfx = util.common_prefix(words)
            if len(pfx) > len(word):
                self.delete("insert-1c wordstart", "insert")
                self.insert(INSERT, pfx)
                self._syntax_hilite_line(INSERT)
            else:
                if len(words) > 1:
                    log("Completion: %s" % ", ".join(words))
                self.bell()
        return 'break'

    def handle_key_backspace(self, event=None):
        selranges = self.tag_ranges(SEL)
        if selranges:
            self.delete(SEL_FIRST, SEL_LAST)
            self._syntax_hilite_line('insert')
            return 'break'
        curridx = self.index(INSERT)
        currline, currpos = [int(i) for i in curridx.split('.')]
        line = self.get('insert linestart', 'insert lineend')
        indent = len(line) - len(line.lstrip())
        if currpos == indent and currpos > 0:
            todel = indent % 4
            if not todel:
                todel = 4
            if todel > currpos:
                todel = currpos
            self.delete('insert linestart', 'insert linestart+%dc' % todel)
            return 'break'
        self.schedule_gutter_update(event=event)

    def handle_key_enter(self, event=None):
        self._syntax_hilite_line('insert')
        prevline = self.get('insert-1l linestart', 'insert-1l lineend')
        line = self.get('insert linestart', 'insert lineend')
        previndent = len(prevline) - len(prevline.lstrip(' '))
        indent = len(line) - len(line.lstrip(' '))
        incs = decs = 0
        syndata = self.syntax_data[self.syntax_mode]
        incr_words = syndata['incr']
        decr_words = syndata['decr']
        for word, start, end in self._words(line):
            if word in incr_words:
                incs = 1
            if line.strip().startswith(word) and word in decr_words:
                decs = 1
        if decs and indent - previndent >= 0:
            self.delete('insert linestart', 'insert lineend')
            self.insert(
                INSERT,
                (' ' * (previndent - 4 * decs)) + line.lstrip()
            )
            indent -= 4 * decs
        self._syntax_hilite_line('insert')
        self.insert(INSERT, "\n" + ' ' * (indent + 4 * incs))
        self.see(INSERT)
        return 'break'

    def handle_keypress(self, event=None):
        self.after_idle(self._syntax_hilite_line, 'insert')

    def insert(self, pos, txt, tags=None):
        start = int(self.index(pos).split('.', 1)[0])
        lines = len(txt.split('\n'))
        end = start + lines
        ListDisplay.insert(self, pos, txt, tags)
        for linenum in range(start-1, end+1):
            if linenum >= 0:
                self.dirty_lines.append(linenum)
        self._schedule_update()

    def _schedule_update(self):
        if not self.scheduled_update:
            self.scheduled_update = True
            self.after_idle(self._update_dirty_lines)

    def _update_dirty_lines(self):
        self.scheduled_update = False
        for linenum in self.dirty_lines:
            pos = "%s.0" % linenum
            self._syntax_hilite_line(pos)
        self.dirty_lines = []


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
