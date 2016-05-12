from textwrap import dedent

import mufsim.stackitems as si
import mufsim.gamedb as db
import mufsim.utils as util
from mufsim.logger import errlog
from mufsim.compiled import CompiledMuf
from mufsim.errors import MufCompileError

import mufsim.insts.flow as instfl
import mufsim.insts.stack as instst
import mufsim.insts.arrays  # noqa
import mufsim.insts.comparators  # noqa
import mufsim.insts.connections  # noqa
import mufsim.insts.debug  # noqa
import mufsim.insts.descriptors  # noqa
import mufsim.insts.directives  # noqa
import mufsim.insts.fpmath  # noqa
import mufsim.insts.intmath  # noqa
import mufsim.insts.io  # noqa
import mufsim.insts.locks  # noqa
import mufsim.insts.objectdb  # noqa
import mufsim.insts.predicates  # noqa
import mufsim.insts.properties  # noqa
import mufsim.insts.strings  # noqa
import mufsim.insts.timedate  # noqa


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
from mufsim.insts.base import primitives
import mufsim.configs as confs


literal_handlers = []


# Decorator
def literal_handler(cls):
    literal_handlers.append(cls)
    return cls


class MufCompiler(object):
    builtin_defines = {
        '__version': util.escape_str(confs.EMULATED_VERSION),
        '__muckname': util.escape_str("MufSim"),
        '__fuzzball__': '1',
        'max_variable_count': str(confs.MAX_VARS),

        '}array': '} array_make',
        '}list': '} array_make',
        '}dict': '} 2 / array_make_dict',
        '}join': '} array_make "" array_join',
        '}cat': '} array_make "" array_join',
        '}tell': '} array_make me @ 1 array_make array_notify',
        '[]': 'array_getitem',
        '[..]': 'array_getrange',
        '->[]': 'array_setitem',
        '[]<-': 'array_appenditem',
        'array_interpret': '"" array_join',
        'array_union': '2 array_nunion',
        'array_diff': '2 array_ndiff',
        'array_intersect': '2 array_nintersect',

        'desc': '"_/de" getpropstr',
        'idesc': '"_/ide" getpropstr',
        'succ': '"_/sc" getpropstr',
        'osucc': '"_/osc" getpropstr',
        'fail': '"_/fl" getpropstr',
        'ofail': '"_/ofl" getpropstr',
        'drop': '"_/dr" getpropstr',
        'odrop': '"_/odr" getpropstr',
        'oecho': '"_/oecho" getpropstr',
        'pecho': '"_/pecho" getpropstr',

        'setdesc': '"_/de" swap setprop',
        'setidesc': '"_/ide" swap setprop',
        'setsucc': '"_/sc" swap setprop',
        'setosucc': '"_/osc" swap setprop',
        'setfail': '"_/fl" swap setprop',
        'setofail': '"_/ofl" swap setprop',
        'setdrop': '"_/dr" swap setprop',
        'setodrop': '"_/odr" swap setprop',
        'setoecho': '"_/oecho" swap setprop',
        'setpecho': '"_/pecho" swap setprop',

        'ignoring?': dedent(
            '''\
                "@__sys__/ignore/def" swap 3 dupn 3 reverse
                reflist_find -4 rotate reflist_find or
            '''
        ),
        'ignore_add': '"@__sys__/ignore/def" swap reflist_add',
        'ignore_del': '"@__sys__/ignore/def" swap reflist_del',
        'array_get_ignorelist': '"@__sys__/ignore/def" array_get_reflist',

        'secure_sysvars': '"me" match dup me ! location loc ! trig trigger !',
        'truename': 'name',
        'version': '__version',
        'strip': 'striplead striptail',
        'event_wait': '0 array_make event_waitfor',

        'preempt': 'pr_mode setmode',
        'background': 'bg_mode setmode',
        'foreground': 'fg_mode setmode',

        'pr_mode': '0',
        'fg_mode': '1',
        'bg_mode': '2',

        'reg_icase': '1',
        'reg_all': '2',
        'reg_extended': '4',

        'sorttype_case_ascend': '0',
        'sorttype_nocase_ascend': '1',
        'sorttype_case_descend': '2',
        'sorttype_nocase_descend': '3',

        'sorttype_caseinsens': '1',
        'sorttype_descending': '2',
        'sorttype_shuffle': '4',
    }

    def __init__(self):
        self.compiled = None
        self.word_line = 1
        self.line = 1
        self.stmt_stack = []
        self.funcname = None
        self.defines = dict(self.builtin_defines)
        self.include_defs_from(0, suppress=True)

    def splitword(self, txt):
        txt = self.lstrip(txt)
        for i in range(len(txt)):
            if txt[i].isspace():
                break
            i += 1
        return (txt[:i], txt[i:])

    def lstrip(self, txt):
        i = 0
        while i < len(txt) and txt[i].isspace():
            if txt[i] == "\n":
                self.line += 1
            i += 1
        return txt[i:]

    def strip_comment(self, src):
        src = src[1:]
        lev = 1
        for i in range(len(src)):
            if lev <= 0:
                break
            if src[i] == "\n":
                self.line += 1
            elif src[i] == '(':
                lev += 1
            elif src[i] == ')':
                lev -= 1
        if lev > 0:
            raise MufCompileError("CommentNotTerminated")
        return src[i:]

    def get_string(self, src):
        out = '"'
        i = 1
        srclen = len(src)
        while i < srclen:
            if src[i] == "\n":
                raise MufCompileError("StringNotTerminated")
            elif src[i] == "\\":
                i += 1
                if src[i] in ["r", "n"]:
                    out += "\r"
                elif src[i] == "[":
                    out += "\033"
                else:
                    out += src[i]
            elif src[i] == '"':
                out += '"'
                src = self.lstrip(src[i + 1:])
                return (out, src)
            else:
                out += src[i]
            i += 1
        raise MufCompileError("StringNotTerminated")

    def get_to_eol(self, src):
        if "\n" in src:
            self.line += 1
            return src.split("\n", 1)
        else:
            return (src, "")

    def get_word(self, src, expand=True):
        while True:
            # Strip whitespace
            src = self.lstrip(src)
            if not src:
                return (None, None)
            if src[0] != '(':
                break
            src = self.strip_comment(src)
        self.word_line = self.line
        if src[0] == '"':
            word, src = self.get_string(src)
            return (word, src)
        # Get next word.
        word, src = self.splitword(src)
        # Expand defines if needed
        if word[0] == '\\':
            word = word[1:]
        elif expand and word in self.defines:
            src = self.defines[word] + " " + src
            word, src = self.get_word(src)
            return (word, src)
        # Return raw word.
        src = self.lstrip(src)
        return (word, src)

    def skip_directive_if_block(self, src):
        level = 0
        while True:
            if not src:
                raise MufCompileError("Incomplete $if directive block.")
            word, src = self.get_word(src)
            if word.startswith("$if"):
                cond, src = self.get_word(src, expand=False)
                level += 1
            elif word == "$endif":
                if not level:
                    break
                level -= 1
            elif word == "$else":
                if not level:
                    break
        return src

    def in_loop_inst(self):
        for inst in reversed(self.stmt_stack):
            if type(inst) in [
                instfl.InstBegin,
                instfl.InstFor,
                instfl.InstForeach
            ]:
                return inst
        return None

    def include_defs_from(self, obj, suppress=False):
        obj = db.getobj(obj)
        prop = "_defs/"
        while prop:
            prop = obj.next_prop(prop, suppress=suppress)
            if not prop:
                break
            val = obj.getprop(prop, suppress=suppress)
            if val:
                defname = prop.split('/', 1)[1]
                self.defines[defname] = val

    def check_for_incomplete_block(self):
        if self.stmt_stack:
            if isinstance(self.stmt_stack[-1], instfl.InstIf):
                raise MufCompileError("Incomplete if-then block.")
            if isinstance(self.stmt_stack[-1], instfl.InstTry):
                raise MufCompileError("Incomplete try-catch block.")
            if isinstance(self.stmt_stack[-1], instfl.InstBegin):
                raise MufCompileError("Incomplete loop.")
            if isinstance(self.stmt_stack[-1], instfl.InstFor):
                raise MufCompileError("Incomplete for loop.")
            if isinstance(self.stmt_stack[-1], instfl.InstForeach):
                raise MufCompileError("Incomplete foreach loop.")

    @literal_handler
    def literal_integer(self, line, code, word):
        if util.is_int(word):
            code.append(instst.InstPushItem(line, int(word)))
            return True
        return False

    @literal_handler
    def literal_dbref(self, line, code, word):
        if util.is_dbref(word):
            code.append(instst.InstPushItem(line, si.DBRef(int(word[1:]))))
            return True
        return False

    @literal_handler
    def literal_float(self, line, code, word):
        if util.is_float(word):
            code.append(instst.InstPushItem(line, float(word)))
            return True
        return False

    @literal_handler
    def literal_string(self, line, code, word):
        if word.startswith('"'):
            code.append(instst.InstPushItem(line, word[1:-1]))
            return True
        return False

    @literal_handler
    def literal_globalvar(self, line, code, word):
        comp = self.compiled
        if comp.get_global_var(word):
            v = comp.get_global_var(word)
            code.append(instst.InstGlobalVar(line, v.value, word))
            return True
        return False

    @literal_handler
    def literal_funcvar(self, line, code, word):
        comp = self.compiled
        if comp.get_func_var(self.funcname, word):
            v = comp.get_func_var(self.funcname, word)
            code.append(instst.InstFuncVar(line, v.value, word))
            return True
        return False

    @literal_handler
    def literal_tick(self, line, code, word):
        comp = self.compiled
        if word.startswith("'"):
            word = word[1:]
            addr = comp.get_function_addr(word)
            if addr is None:
                raise MufCompileError("Unrecognized identifier: %s" % word)
            code.append(instst.InstPushItem(line, addr))
            return True
        return False

    @literal_handler
    def literal_function(self, line, code, word):
        comp = self.compiled
        if comp.get_function_addr(word) is not None:
            addr = comp.get_function_addr(word)
            code.append(instst.InstPushItem(line, addr))
            code.append(instfl.InstExecute(line))
            return True
        return False

    def compile_r(self, src):
        code = []
        while True:
            word, src = self.get_word(src)
            if not word:
                return (code, src)
            if not self.funcname:
                if (
                    not word.startswith('$') and
                    word not in [":", "lvar", "var", "public", "wizcall"]
                ):
                    raise MufCompileError("Not in function: %s" % word)
            foundlit = False
            for fun in literal_handlers:
                if fun(self, self.word_line, code, word):
                    foundlit = True
                    break
            if foundlit:
                continue
            if word in primitives:
                instcls = primitives[word]
                inst = instcls(self.word_line)
                doret, src = inst.compile(self, code, src)
                if doret:
                    return (code, src)
            else:
                raise MufCompileError("Unrecognized identifier: %s" % word)

    def compile_source(self, prog):
        comp = CompiledMuf(prog)
        self.compiled = comp
        self.line = 1
        self.word_line = 1
        self.stmt_stack = []
        self.funcname = None
        self.defines = dict(self.builtin_defines)
        self.include_defs_from(0, suppress=True)
        src = db.getobj(prog).sources
        try:
            code, src = self.compile_r(src)
            if self.funcname:
                raise MufCompileError("Function incomplete.")
            self.check_for_incomplete_block()
            if code:
                for inum, inst in enumerate(code):
                    if type(inst) in [
                        instfl.InstTry,
                        instfl.InstJmp,
                        instfl.InstJmpIfFalse
                    ]:
                        inst.value += inum
                comp.code = code
                db.getobj(prog).compiled = comp
                return True
            return False
        except MufCompileError as e:
            errlog("Error in line %d: %s" % (self.word_line, e))
            return None


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
