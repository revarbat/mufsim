import mufsim.utils as util
import mufsim.gamedb as db
from mufsim.logger import log
from mufsim.errors import MufCompileError
from mufsim.insts.base import Instruction, instr


@instr("$abort")
class InstDollarAbort(Instruction):
    def compile(self, cmplr, code, src):
        val, src = cmplr.get_to_eol(src)
        raise MufCompileError(val)


@instr("$echo")
class InstDollarEcho(Instruction):
    def compile(self, cmplr, code, src):
        val, src = cmplr.get_to_eol(src)
        log("$ECHO: %s" % val)
        return (False, src)


@instr("$pragma")
class InstDollarPragma(Instruction):
    def compile(self, cmplr, code, src):
        val, src = cmplr.get_to_eol(src)
        return (False, src)


@instr("$language")
class InstDollarLanguage(Instruction):
    def compile(self, cmplr, code, src):
        val, src = cmplr.get_to_eol(src)
        if val.strip().lower() == '"muv"':
            raise MufCompileError("MUV needs -m flag to compile.")
        return (False, src)


@instr("$author")
class InstDollarAuthor(Instruction):
    def compile(self, cmplr, code, src):
        val, src = cmplr.get_to_eol(src)
        comp = cmplr.compiled
        db.getobj(comp.program).setprop("_author", val)
        return (False, src)


@instr("$note")
class InstDollarNote(Instruction):
    def compile(self, cmplr, code, src):
        val, src = cmplr.get_to_eol(src)
        comp = cmplr.compiled
        db.getobj(comp.program).setprop("_note", val)
        return (False, src)


@instr("$version")
class InstDollarVersion(Instruction):
    def compile(self, cmplr, code, src):
        val, src = cmplr.get_word(src)
        comp = cmplr.compiled
        db.getobj(comp.program).setprop("_version", val)
        return (False, src)


@instr("$lib-version")
class InstDollarLibVersion(Instruction):
    def compile(self, cmplr, code, src):
        val, src = cmplr.get_word(src)
        comp = cmplr.compiled
        db.getobj(comp.program).setprop("_lib-version", val)
        return (False, src)


@instr("$def")
class InstDollarDef(Instruction):
    def compile(self, cmplr, code, src):
        nam, src = cmplr.get_word(src)
        val, src = cmplr.get_to_eol(src)
        cmplr.defines[nam] = val
        return (False, src)


@instr("$define")
class InstDollarDefine(Instruction):
    def compile(self, cmplr, code, src):
        nam, src = cmplr.get_word(src)
        if "$enddef" not in src:
            raise MufCompileError("Incomplete $define for %s" % nam)
        val, src = src.split("$enddef", 1)
        cmplr.defines[nam] = val
        return (False, src)


@instr("$undef")
class InstDollarUnDef(Instruction):
    def compile(self, cmplr, code, src):
        nam, src = cmplr.get_word(src)
        if nam in cmplr.defines:
            del cmplr.defines[nam]
        return (False, src)


@instr("$include")
class InstDollarInclude(Instruction):
    def compile(self, cmplr, code, src):
        comp = cmplr.compiled
        targ, src = cmplr.get_word(src)
        if targ == "this":
            obj = comp.program
        else:
            who = db.getobj(comp.program).owner
            obj = db.match_from(who, targ)
        cmplr.include_defs_from(obj)
        return (False, src)


@instr("$pubdef")
class InstDollarPubDef(Instruction):
    def compile(self, cmplr, code, src):
        comp = cmplr.compiled
        nam, src = cmplr.get_word(src)
        val, src = cmplr.get_to_eol(src)
        if nam == ":":
            db.getobj(comp.program).delprop("_defs")
        elif not val.strip():
            db.getobj(comp.program).delprop("_defs/%s" % nam)
        else:
            if nam[0] == '\\':
                nam = nam[1:]
                if db.getobj(comp.program).getprop("_defs/%s" % nam):
                    return (False, src)
            db.getobj(comp.program).setprop("_defs/%s" % nam, val)
        return (False, src)


@instr("$libdef")
class InstDollarLibDef(Instruction):
    def compile(self, cmplr, code, src):
        comp = cmplr.compiled
        nam, src = cmplr.get_word(src)
        if nam.startswith('\\'):
            nam = nam[1:]
            if db.getobj(comp.program).getprop("_defs/%s" % nam):
                return (False, src)
        prog = db.getobj(comp.program)
        val = "#%d %s call" % (prog.dbref, util.escape_str(nam))
        prog.setprop("_defs/%s" % nam, val)
        return (False, src)


@instr("$cleardefs")
class InstDollarClearDefs(Instruction):
    def compile(self, cmplr, code, src):
        val, src = cmplr.get_word(src)
        cmplr.defines = dict(cmplr.builtin_defines)
        if val.strip().upper() != "ALL":
            cmplr.include_defs_from(0, suppress=True)
        return (False, src)


@instr("$ifdef")
class InstDollarIfDef(Instruction):
    def compile(self, cmplr, code, src):
        cond, src = cmplr.get_word(src, expand=False)
        istrue = True
        if '=' in cond:
            nam, val = cond.split('=', 1)
            istrue = nam in cmplr.defines and cmplr.defines[nam] == val
        elif '>' in cond:
            nam, val = cond.split('>', 1)
            istrue = nam in cmplr.defines and cmplr.defines[nam] > val
        elif '<' in cond:
            nam, val = cond.split('<', 1)
            istrue = nam in cmplr.defines and cmplr.defines[nam] < val
        else:
            istrue = cond in cmplr.defines
        if not istrue:
            src = cmplr.skip_directive_if_block(src)
        return (False, src)


@instr("$ifndef")
class InstDollarIfNDef(Instruction):
    def compile(self, cmplr, code, src):
        cond, src = cmplr.get_word(src, expand=False)
        istrue = True
        if '=' in cond:
            nam, val = cond.split('=', 1)
            istrue = nam in cmplr.defines and cmplr.defines[nam] == val
        elif '>' in cond:
            nam, val = cond.split('>', 1)
            istrue = nam in cmplr.defines and cmplr.defines[nam] > val
        elif '<' in cond:
            nam, val = cond.split('<', 1)
            istrue = nam in cmplr.defines and cmplr.defines[nam] < val
        else:
            istrue = cond in cmplr.defines
        if istrue:
            src = cmplr.skip_directive_if_block(src)
        return (False, src)


@instr("$ifver")
class InstDollarIfVer(Instruction):
    def compile(self, cmplr, code, src):
        comp = cmplr.compiled
        obj, src = cmplr.get_word(src)
        ver, src = cmplr.get_word(src)
        if obj == "this":
            obj = comp.program
        else:
            who = db.getobj(comp.program).owner
            obj = db.match_from(who, obj)
        istrue = True
        if not db.validobj(obj):
            istrue = False
        else:
            val = db.getobj(obj).getprop("_version")
            if not val:
                istrue = False
            else:
                istrue = val >= ver
        if not istrue:
            src = cmplr.skip_directive_if_block(src)
        return (False, src)


@instr("$ifnver")
class InstDollarIfNVer(Instruction):
    def compile(self, cmplr, code, src):
        comp = cmplr.compiled
        obj, src = cmplr.get_word(src)
        ver, src = cmplr.get_word(src)
        if obj == "this":
            obj = comp.program
        else:
            who = db.getobj(comp.program).owner
            obj = db.match_from(who, obj)
        istrue = True
        if not db.validobj(obj):
            istrue = False
        else:
            val = db.getobj(obj).getprop("_version")
            if not val:
                istrue = False
            else:
                istrue = val >= ver
        if istrue:
            src = cmplr.skip_directive_if_block(src)
        return (False, src)


@instr("$iflibver")
class InstDollarIfLibVer(Instruction):
    def compile(self, cmplr, code, src):
        comp = cmplr.compiled
        obj, src = cmplr.get_word(src)
        ver, src = cmplr.get_word(src)
        if obj == "this":
            obj = comp.program
        else:
            who = db.getobj(comp.program).owner
            obj = db.match_from(who, obj)
        istrue = True
        if not db.validobj(obj):
            istrue = False
        else:
            val = db.getobj(obj).getprop("_lib-version")
            if not val:
                istrue = False
            else:
                istrue = val >= ver
        if not istrue:
            src = cmplr.skip_directive_if_block(src)
        return (False, src)


@instr("$ifnlibver")
class InstDollarIfNLibVer(Instruction):
    def compile(self, cmplr, code, src):
        comp = cmplr.compiled
        obj, src = cmplr.get_word(src)
        ver, src = cmplr.get_word(src)
        if obj == "this":
            obj = comp.program
        else:
            who = db.getobj(comp.program).owner
            obj = db.match_from(who, obj)
        istrue = True
        if not db.validobj(obj):
            istrue = False
        else:
            val = db.getobj(obj).getprop("_lib-version")
            if not val:
                istrue = False
            else:
                istrue = val >= ver
        if istrue:
            src = cmplr.skip_directive_if_block(src)
        return (False, src)


@instr("$iflib")
class InstDollarIfLib(Instruction):
    def compile(self, cmplr, code, src):
        comp = cmplr.compiled
        obj, src = cmplr.get_word(src)
        if obj == "this":
            obj = comp.program
        else:
            who = db.getobj(comp.program).owner
            obj = db.match_from(who, obj)
        istrue = db.validobj(obj) and db.getobj(obj).objtype == "program"
        if not istrue:
            src = cmplr.skip_directive_if_block(src)
        return (False, src)


@instr("$ifnlib")
class InstDollarIfNLib(Instruction):
    def compile(self, cmplr, code, src):
        comp = cmplr.compiled
        obj, src = cmplr.get_word(src)
        if obj == "this":
            obj = comp.program
        else:
            who = db.getobj(comp.program).owner
            obj = db.match_from(who, obj)
        istrue = db.validobj(obj) and db.getobj(obj).objtype == "program"
        if istrue:
            src = cmplr.skip_directive_if_block(src)
        return (False, src)


@instr("$ifcancall")
class InstDollarIfCanCall(Instruction):
    def compile(self, cmplr, code, src):
        comp = cmplr.compiled
        obj, src = cmplr.get_word(src)
        pub, src = cmplr.get_word(src)
        if obj == "this":
            obj = comp.program
        else:
            who = db.getobj(comp.program).owner
            obj = db.match_from(who, obj)
        obj = db.getobj(obj)
        istrue = (
            obj.objtype == "program" and
            obj.compiled and
            obj.compiled.publics and
            pub in obj.compiled.publics
        )
        if not istrue:
            src = cmplr.skip_directive_if_block(src)
        return (False, src)


@instr("$ifncancall")
class InstDollarIfNCanCall(Instruction):
    def compile(self, cmplr, code, src):
        comp = cmplr.compiled
        obj, src = cmplr.get_word(src)
        pub, src = cmplr.get_word(src)
        if obj == "this":
            obj = comp.program
        else:
            who = db.getobj(comp.program).owner
            obj = db.match_from(who, obj)
        obj = db.getobj(obj)
        istrue = (
            obj.objtype == "program" and
            obj.compiled and
            obj.compiled.publics and
            pub in obj.compiled.publics
        )
        if istrue:
            src = cmplr.skip_directive_if_block(src)
        return (False, src)


@instr("$else")
class InstDollarElse(Instruction):
    def compile(self, cmplr, code, src):
        level = 0
        while True:
            if not src:
                raise MufCompileError("Incomplete $else directive block.")
            word, src = cmplr.get_word(src, expand=False)
            if word.startswith("$if"):
                cond, src = cmplr.get_word(src, expand=False)
                level += 1
            elif word == "$endif":
                if not level:
                    break
                level -= 1
            elif word == "$else":
                if not level:
                    raise MufCompileError("Multiple $else clauses.")
        return (False, src)


@instr("$endif")
class InstDollarEndif(Instruction):
    def compile(self, cmplr, code, src):
        return (False, src)


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
