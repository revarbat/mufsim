import copy

import mufsim.stackitems as si


class MufCallFrame(object):
    def __init__(self, addr, caller):
        if isinstance(caller, int):
            caller = si.DBRef(caller)
        self.variables = {}
        self.loop_stack = []
        self.pc = addr
        self.caller = caller

    def pc_advance(self, delta):
        self.pc.value += delta

    def pc_set(self, addr):
        self.pc = copy.deepcopy(addr)

    def loop_iter_push(self, typ, it):
        self.loop_stack.append((typ, it))

    def loop_iter_pop(self):
        return self.loop_stack.pop()

    def loop_iter_top(self):
        return self.loop_stack[-1]

    def variable_get(self, varnum):
        if varnum in self.variables:
            return self.variables[varnum]
        return 0

    def variable_set(self, varnum, val):
        self.variables[varnum] = val


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
