import mufsim.stackitems as si
import mufsim.gamedb as db
from mufsim.insts.flow import InstFunc


class CompiledMuf(object):
    def __init__(self, prog):
        self.program = prog
        self.srclines = db.getobj(prog).sources.split("\n")
        self.code = []
        self.functions = {}
        self.publics = {}
        self.func_vars = {}
        self.global_vars = ["me", "loc", "trigger", "command"]
        self.lastfunction = None

    def get_tokens_info(self):
        return [
            {
                "prog": self.program,
                "addr": i,
                "line": inst.line,
                "repr": str(inst)
            }
            for i, inst in enumerate(self.code)
        ]

    def add_function(self, funcname, addr):
        if isinstance(addr, int):
            addr = si.Address(addr, self.program)
        self.functions[funcname] = addr
        self.func_vars[funcname] = []
        self.lastfunction = addr

    def get_functions(self):
        funcs = sorted(self.functions.keys())
        return funcs

    def get_function_addr(self, funcname):
        if funcname not in self.functions:
            return None
        return self.functions[funcname]

    def publicize_function(self, funcname):
        if funcname not in self.functions:
            return False
        self.publics[funcname] = self.functions[funcname]
        return True

    def find_func(self, addr):
        if isinstance(addr, si.Address):
            addr = addr.value
        while addr > 0 and not isinstance(self.code[addr], InstFunc):
            addr -= 1
        if not isinstance(self.code[addr], InstFunc):
            return ""
        return self.code[addr].funcname

    def get_inst(self, addr):
        if isinstance(addr, si.Address):
            addr = addr.value
        return self.code[addr]

    def get_inst_line(self, addr):
        if isinstance(addr, si.Address):
            addr = addr.value
        return self.code[addr].line

    def add_func_var(self, funcname, varname):
        varcount = len(self.func_vars[funcname])
        self.func_vars[funcname].append(varname)
        return varcount

    def get_func_var(self, funcname, varname):
        if funcname not in self.func_vars:
            return None
        if varname not in self.func_vars[funcname]:
            return None
        return si.FuncVar(self.func_vars[funcname].index(varname))

    def get_func_vars(self, funcname):
        if funcname not in self.func_vars:
            return None
        return self.func_vars[funcname]

    def add_global_var(self, varname):
        varcount = len(self.global_vars)
        self.global_vars.append(varname)
        return varcount

    def get_global_var(self, varname):
        if varname in self.global_vars:
            return si.GlobalVar(self.global_vars.index(varname))
        return None

    def get_global_vars(self):
        return self.global_vars


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
