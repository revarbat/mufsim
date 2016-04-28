primitives = {}


# Decorator
def instr(inst_name):
    def instr_decorator(func):
        primitives[inst_name] = func
        func.prim_name = inst_name
        return func
    return instr_decorator


class Instruction(object):
    prim_name = None

    def __init__(self, line):
        self.line = line

    def execute(self, fr):
        pass

    def compile(self, cmplr, code, src):
        cls = type(self)
        inst = cls(self.line)
        code.append(inst)
        return (False, src)

    def __str__(self):
        if self.prim_name:
            return self.prim_name.upper().strip()
        primname = str(type(self))
        primname = primname.split("'")[1]
        primname = primname.split('.')[-1]
        primname = primname.strip()[4:]
        return primname

    def __repr__(self):
        return str(self)


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
