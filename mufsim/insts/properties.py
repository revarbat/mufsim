import mufsim.utils as util
import mufsim.gamedb as db
import mufsim.stackitems as si
from mufsim.errors import MufRuntimeError
from mufsim.insts.base import Instruction, instr


@instr("addprop")
class InstAddProp(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        val2 = fr.data_pop(int)
        val = fr.data_pop(str)
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        if val:
            obj.setprop(prop, val)
        else:
            obj.setprop(prop, val2)


@instr("setprop")
class InstSetProp(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        val = fr.data_pop()
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        obj.setprop(prop, val)


@instr("remove_prop")
class InstRemoveProp(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        obj.delprop(prop)


@instr("propdir?")
class InstPropDirP(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        val = obj.is_propdir(prop)
        fr.data_push(1 if val else 0)


@instr("nextprop")
class InstNextProp(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        val = obj.next_prop(prop)
        fr.data_push(val)


@instr("array_get_propdirs")
class InstArrayGetPropDirs(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        prop = fr.data_pop(str) + '/'
        obj = fr.data_pop_object()
        out = []
        while True:
            prop = obj.next_prop(prop)
            if not prop:
                break
            if obj.is_propdir(prop):
                out.append(prop)
        fr.data_push(out)


@instr("getprop")
class InstGetProp(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        val = obj.getprop(prop)
        if val is None:
            val = 0
        fr.data_push(val)


@instr("getpropstr")
class InstGetPropStr(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        val = obj.getprop(prop)
        if type(val) is not str:
            val = ""
        fr.data_push(val)


@instr("getpropval")
class InstGetPropVal(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        val = obj.getprop(prop)
        if type(val) is not int:
            val = 0
        fr.data_push(val)


@instr("getpropfval")
class InstGetPropFVal(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        val = obj.getprop(prop)
        if type(val) is not float:
            val = 0.0
        fr.data_push(val)


@instr("envprop")
class InstEnvProp(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        prop = fr.data_pop(str)
        obj = fr.data_pop_object().dbref
        while obj >= 0:
            val = db.getobj(obj).getprop(prop)
            if val is not None:
                break
            obj = db.getobj(obj).location
        if val is None:
            val = 0
        fr.data_push(val)


@instr("envpropstr")
class InstEnvPropStr(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        prop = fr.data_pop(str)
        obj = fr.data_pop_object().dbref
        while obj >= 0:
            val = db.getobj(obj).getprop(prop)
            if val is not None:
                break
            obj = db.getobj(obj).location
        if type(val) is str:
            fr.data_push(val)
        else:
            fr.data_push("")


@instr("array_get_proplist")
class InstArrayGetPropList(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        out = []
        val = obj.getprop("%s#" % prop)
        cnt = 0
        if val:
            if type(val) is str:
                try:
                    cnt = int(cnt)
                except:
                    cnt = 0
            elif type(val) is int:
                cnt = val
        for i in xrange(cnt):
            val = obj.getprop("%s#/%d" % (prop, i + 1))
            if type(val) is str:
                out.append(val)
        fr.data_push(out)


@instr("array_put_proplist")
class InstArrayPutPropList(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        items = fr.data_pop(list)
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        obj.setprop("%s#" % prop, len(items))
        for i, item in enumerate(items):
            obj.setprop("%s#/%d" % (prop, i + 1), item)


@instr("array_get_reflist")
class InstArrayGetReflist(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        val = obj.getprop(prop)
        if type(val) is not str:
            fr.data_push([])
        else:
            vals = [
                si.DBRef(int(x[1:]))
                for x in val.split(" ")
                if util.is_dbref(x)
            ]
            fr.data_push(vals)


@instr("array_put_reflist")
class InstArrayPutReflist(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        refs = fr.data_pop(list)
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        for ref in refs:
            if type(ref) is not si.DBRef:
                raise MufRuntimeError("Expected list of dbrefs.")
        refstr = " ".join(["#%d" % ref.value for ref in refs])
        obj.setprop(prop, refstr)


@instr("reflist_add")
class InstRefListAdd(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        ref = fr.data_pop_dbref()
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        val = obj.getprop(prop)
        if type(val) is not str:
            refs = []
        else:
            refs = [
                si.DBRef(int(x[1:]))
                for x in val.split(" ")
                if util.is_dbref(x)
            ]
        if ref in refs:
            del refs[refs.index(ref)]
        refs.append(ref)
        refstr = " ".join(["#%d" % x.value for x in refs])
        obj.setprop(prop, refstr)


@instr("reflist_del")
class InstRefListDel(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        ref = fr.data_pop_dbref()
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        val = obj.getprop(prop)
        if type(val) is not str:
            refs = []
        else:
            refs = [
                si.DBRef(int(x[1:]))
                for x in val.split(" ")
                if util.is_dbref(x)
            ]
        if ref in refs:
            del refs[refs.index(ref)]
        refstr = " ".join(["#%d" % x.value for x in refs])
        obj.setprop(prop, refstr)


@instr("reflist_find")
class InstRefListFind(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        ref = fr.data_pop_dbref()
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        val = obj.getprop(prop)
        if type(val) is not str:
            refs = []
        else:
            refs = [
                si.DBRef(int(x[1:]))
                for x in val.split(" ")
                if util.is_dbref(x)
            ]
        if ref in refs:
            fr.data_push(refs.index(ref) + 1)
        else:
            fr.data_push(0)


@instr("array_filter_prop")
class InstArrayFilterProp(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        pat = fr.data_pop(str)
        prop = fr.data_pop(str)
        objs = fr.data_pop(list)
        found = []
        for obj in objs:
            if type(obj) is not si.DBRef:
                raise MufRuntimeError("Expected list of dbrefs.")
            if db.validobj(obj):
                val = db.getobj(obj).getprop(prop)
                if val and util.smatch(pat, val):
                    found.append(obj)
        fr.data_push(found)


@instr("array_filter_flags")
class InstArrayFilterFlags(Instruction):
    type_map = {
        'E': "exit",
        'F': "program",
        'G': "garbage",
        'P': "player",
        'R': "room",
        'T': "thing",
    }

    def execute(self, fr):
        fr.check_underflow(2)
        flags = fr.data_pop(str).upper()
        objs = fr.data_pop(list)
        found = []
        for obj in objs:
            fr.check_type(obj, [si.DBRef])
            if db.validobj(obj):
                obj = db.getobj(obj)
                good = True
                invert = False
                for flg in list(flags):
                    goodpass = True
                    mlev = 1 if '1' in obj.flags else 0
                    mlev += 2 if '2' in obj.flags else 0
                    mlev += 3 if '3' in obj.flags else 0
                    if flg == '!':
                        invert = not invert
                        continue
                    elif flg in self.type_map:
                        goodpass = self.type_map[flg] == obj.objtype
                    elif flg in ['1', '2', '3']:
                        goodpass = int(flg) <= mlev
                    elif flg == 'M':
                        goodpass = mlev >= 1
                    elif flg == 'N':
                        goodpass = mlev % 2 == 1
                    else:
                        goodpass = flg in obj.flags
                    goodpass = not goodpass if invert else goodpass
                    good = good and goodpass
                    invert = False
                if good:
                    found.append(si.DBRef(obj.dbref))
        fr.data_push(found)


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
