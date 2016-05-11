from functools import cmp_to_key

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
        if not isinstance(val, str):
            val = ""
        fr.data_push(val)


@instr("getpropval")
class InstGetPropVal(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        val = obj.getprop(prop)
        if not isinstance(val, int):
            val = 0
        fr.data_push(val)


@instr("getpropfval")
class InstGetPropFVal(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        val = obj.getprop(prop)
        if not isinstance(val, float):
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
        if isinstance(val, str):
            fr.data_push(val)
        else:
            fr.data_push("")


@instr("blessprop")
class InstBlessProp(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        obj.blessprop(prop)


@instr("unblessprop")
class InstUnBlessProp(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        obj.unblessprop(prop)


@instr("blessed?")
class InstBlessedP(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        val = obj.is_blessed(prop)
        fr.data_push(1 if val else 0)


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
            if isinstance(val, str):
                try:
                    cnt = int(cnt)
                except:
                    cnt = 0
            elif isinstance(val, int):
                cnt = val
        for i in range(cnt):
            val = obj.getprop("%s#/%d" % (prop, i + 1))
            if isinstance(val, str):
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


@instr("array_get_propvals")
class InstArrayGetPropVals(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        prop = obj.normalize_prop(prop) + '/'
        plen = len(prop)
        out = {}
        vprop = obj.next_prop(prop)
        while vprop:
            val = obj.getprop(vprop)
            if val is not None:
                out[vprop[plen:]] = val
            vprop = obj.next_prop(vprop)
        fr.data_push(out)


@instr("array_put_propvals")
class InstArrayPutPropVals(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        d = fr.data_pop(dict)
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        keys = sorted(
            list(d.keys()),
            key=cmp_to_key(si.sortcomp),
        )
        for key in keys:
            obj.setprop("%s/%s" % (prop, key), d[key])


@instr("array_get_reflist")
class InstArrayGetReflist(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        prop = fr.data_pop(str)
        obj = fr.data_pop_object()
        val = obj.getprop(prop)
        if not isinstance(val, str):
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
            if not isinstance(ref, si.DBRef):
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
        if not isinstance(val, str):
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
        if not isinstance(val, str):
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
        if not isinstance(val, str):
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
            if not isinstance(obj, si.DBRef):
                raise MufRuntimeError("Expected list of dbrefs.")
            if db.validobj(obj):
                val = db.getobj(obj).getprop(prop)
                if val and util.smatch(pat, val):
                    found.append(obj)
        fr.data_push(found)


@instr("array_filter_flags")
class InstArrayFilterFlags(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        flags = fr.data_pop(str).upper()
        objs = fr.data_pop(list)
        found = []
        for obj in objs:
            fr.check_type(obj, [si.DBRef])
            if db.validobj(obj):
                obj = db.getobj(obj)
                if db.flagsmatch(flags, obj):
                    found.append(si.DBRef(obj.dbref))
        fr.data_push(found)


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
