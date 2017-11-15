import re
import copy
import random
from functools import cmp_to_key

import mufsim.utils as util
import mufsim.gamedb as db
import mufsim.stackitems as si
from mufsim.errors import MufRuntimeError
from mufsim.insts.base import Instruction, instr


@instr("array_default_pinning")
class InstArrayDefaultPinning(Instruction):
    def execute(self, fr):
        pin = fr.data_pop(int)
        fr.array_pinning = bool(pin)


@instr("array_pin")
class InstArrayPin(Instruction):
    def execute(self, fr):
        arr = fr.data_pop_array()
        arr.pinned = True
        fr.data_push(arr)


@instr("array_unpin")
class InstArrayPin(Instruction):
    def execute(self, fr):
        arr = fr.data_pop_array()
        arr.pinned = False
        fr.data_push(arr)


@instr("array_make")
class InstArrayMake(Instruction):
    def execute(self, fr):
        num = fr.data_pop(int)
        fr.check_underflow(num)
        arr = []
        for i in range(num):
            arr.insert(0, fr.data_pop())
        fr.data_push_list(arr)


@instr("array_make_dict")
class InstArrayMakeDict(Instruction):
    def execute(self, fr):
        num = fr.data_pop(int)
        fr.check_underflow(num * 2)
        d = {}
        for i in range(num):
            val = fr.data_pop()
            key = fr.data_pop(int, str)
            d[key] = val
        fr.data_push_dict(d)


@instr("array_count")
class InstArrayCount(Instruction):
    def execute(self, fr):
        arr = fr.data_pop_array()
        fr.data_push(len(arr))


@instr("array_compare")
class InstArrayCompare(Instruction):
    def execute(self, fr):
        arr2 = fr.data_pop_array()
        arr1 = fr.data_pop_array()
        fr.data_push(util.compare_dicts(arr1, arr2))


@instr("array_getitem")
class InstArrayGetItem(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        key = fr.data_pop()
        arr = fr.data_pop_array()
        if isinstance(arr, si.MufList):
            if not isinstance(key, int):
                fr.data_push(0)
            elif key < 0 or key >= len(arr):
                fr.data_push(0)
            else:
                fr.data_push(arr[key])
        elif isinstance(arr, si.MufDict):
            if key in arr:
                fr.data_push(arr[key])
            else:
                fr.data_push(0)


@instr("array_setitem")
class InstArraySetItem(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        key = fr.data_pop()
        arr = fr.data_pop_array()
        val = fr.data_pop()
        if isinstance(arr, si.MufList):
            if key < 0 or key > len(arr):
                raise MufRuntimeError("Index out of array bounds.")
        arr = arr.set_item(key, val)
        fr.data_push(arr)


@instr("array_insertitem")
class InstArrayInsertItem(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        key = fr.data_pop()
        arr = fr.data_pop_array()
        val = fr.data_pop()
        if isinstance(arr, si.MufList):
            if not isinstance(key, int):
                raise MufRuntimeError("List array expects integer index.")
            elif key < 0 or key > len(arr):
                raise MufRuntimeError("Index out of array bounds.")
            arr = arr.set_item(slice(key, key), [val])
        elif isinstance(arr, si.MufDict):
            arr = arr.set_item(key, val)
        fr.data_push(arr)


@instr("array_delitem")
class InstArrayDelItem(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        key = fr.data_pop()
        arr = fr.data_pop_array()
        if isinstance(arr, si.MufList):
            if key < 0 or key > len(arr):
                raise MufRuntimeError("Index out of array bounds.")
        arr = arr.del_item(key)
        fr.data_push(arr)


@instr("array_appenditem")
class InstArrayAppendItem(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        arr = fr.data_pop_list()
        val = fr.data_pop()
        arr = arr.set_item(slice(len(arr), None, None), [val])
        fr.data_push(arr)


@instr("array_extract")
class InstArrayExtract(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        keys = fr.data_pop_list()
        arr = fr.data_pop_array()
        arrkeys = arr.keys()
        out = {key: arr[key] for key in keys if key in arrkeys}
        fr.data_push_dict(out)


@instr("array_getrange")
class InstArrayGetRange(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        end = fr.data_pop(int)
        st = fr.data_pop(int)
        arr = fr.data_pop_list()
        fr.data_push_list(arr[st:end + 1])


@instr("array_setrange")
class InstArraySetRange(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        items = fr.data_pop_list()
        st = fr.data_pop(int)
        arr = fr.data_pop_list()
        arr = arr.set_item(slice(st, st+len(items)), list(items))
        fr.data_push(arr)


@instr("array_delrange")
class InstArrayDelRange(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        end = fr.data_pop(int)
        st = fr.data_pop(int)
        arr = fr.data_pop_list()
        if end >= len(arr):
            end = len(arr) - 1
        arr = arr.del_item(slice(st, end+1))
        fr.data_push(arr)


@instr("array_insertrange")
class InstArrayInsertRange(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        items = fr.data_pop_list()
        st = fr.data_pop(int)
        arr = fr.data_pop_list()
        if st < 0 or st > len(arr):
            raise MufRuntimeError("Index outside array bounds. (2)")
        arr = arr.set_item(slice(st, st), list(items))
        fr.data_push(arr)


@instr("array_nested_get")
class InstArrayNestedGet(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        keys = fr.data_pop_list()
        arr = fr.data_pop_array()
        for key in keys:
            if not isinstance(arr, (si.MufList, si.MufDict)):
                arr = 0
                break
            try:
                arr = arr[key]
            except (TypeError, KeyError) as e:
                arr = 0
                break
        fr.data_push(arr)


@instr("array_nested_set")
class InstArrayNestedSet(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        keys = fr.data_pop_list()
        arr = fr.data_pop_array()
        val = fr.data_pop()
        stack = []
        for key in keys:
            if not isinstance(arr, (si.MufList, si.MufDict)):
                raise MufRuntimeError("Nested array not a list or dictionary.")
            if isinstance(arr, si.MufList):
                if not isinstance(key, int):
                    raise MufRuntimeError("List array expects integer index.")
                if key < 0 or key > len(subarr):
                    raise MufRuntimeError("Index out of list array bounds.")
            elif not isinstance(key, (int, str)):
                raise MufRuntimeError("Dictionary array expects integer or string index.")
            stack.append( (key, arr) )
            try:
                arr = arr[key]
            except (TypeError, KeyError) as e:
                arr = si.MufDict({}, fr.array_pinning)
        for key, arr in reversed(stack):
            val = arr.set_item(key, val)
        fr.data_push(val)


@instr("array_nested_del")
class InstArrayNestedDel(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        keys = fr.data_pop_list()
        arr = fr.data_pop_array()
        oarr = arr
        stack = []
        for key in keys:
            if not isinstance(arr, (si.MufList, si.MufDict)):
                raise MufRuntimeError("Nested array not a list or dictionary.")
            if isinstance(arr, si.MufList):
                if not isinstance(key, int):
                    raise MufRuntimeError("List array expects integer index.")
                if key < 0 or key > len(subarr):
                    raise MufRuntimeError("Index out of list array bounds.")
            elif not isinstance(key, (int, str)):
                raise MufRuntimeError("Dictionary array expects integer or string index.")
            stack.append( (key, arr) )
            try:
                arr = arr[key]
            except (TypeError, KeyError) as e:
                fr.data_push(oarr)
                return
        val = None
        for key, arr in reversed(stack):
            if val is None:
                val = arr.del_item(key)
            else:
                val = arr.set_item(key, val)
        fr.data_push(val)


@instr("array_keys")
class InstArrayKeys(Instruction):
    def execute(self, fr):
        arr = fr.data_pop_array()
        keys = sorted(
            list(arr.keys()),
            key=cmp_to_key(si.sortcomp),
        )
        for key in keys:
            fr.data_push(key)
        fr.data_push(len(arr))


@instr("array_vals")
class InstArrayVals(Instruction):
    def execute(self, fr):
        arr = fr.data_pop_array()
        keys = sorted(
            list(arr.keys()),
            key=cmp_to_key(si.sortcomp),
        )
        for key in keys:
            fr.data_push(arr[key])
        fr.data_push(len(arr))


@instr("array_explode")
class InstArrayExplode(Instruction):
    def execute(self, fr):
        arr = fr.data_pop_array()
        keys = sorted(
            list(arr.keys()),
            key=cmp_to_key(si.sortcomp),
        )
        for key in keys:
            fr.data_push(key)
            fr.data_push(arr[key])
        fr.data_push(len(arr))


@instr("array_join")
class InstArrayJoin(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        delim = fr.data_pop(str)
        arr = fr.data_pop_list()
        out = ""
        for val in arr:
            if out:
                out += delim
            if isinstance(val, str):
                out += val
            elif isinstance(val, int):
                out += "{0:d}".format(val)
            elif isinstance(val, float):
                out += "{0:g}".format(val)
            elif isinstance(val, si.DBRef):
                out += "#{0:d}".format(val.value)
            elif isinstance(val, si.Address):
                out += "Addr:{0:d}".format(val.value)
            else:
                out += str(val)
        fr.data_push(out)


@instr("array_findval")
class InstArrayFindVal(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        val = fr.data_pop()
        arr = fr.data_pop_array()
        out = [k for k in arr.keys() if arr[k] == val]
        fr.data_push(out)


@instr("array_matchkey")
class InstArrayMatchKey(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        pat = fr.data_pop(str)
        arr = fr.data_pop_array()
        out = {k: arr[k] for k in arr.keys() if isinstance(k, str) and util.smatch(pat, k)}
        fr.data_push(out)


@instr("array_matchval")
class InstArrayMatchVal(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        pat = fr.data_pop(str)
        arr = fr.data_pop_array()
        out = {k: arr[k] for k in arr.keys() if isinstance(arr[k], str) and util.smatch(pat, arr[k])}
        fr.data_push(out)


@instr("array_cut")
class InstArrayCut(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        pos = fr.data_pop(int, str)
        arr = fr.data_pop_array()
        if isinstance(arr, si.MufList):
            if isinstance(pos, str):
                fr.data_push_list(arr[:])
                fr.data_push_list([])
            else:
                fr.data_push_list(arr[:pos])
                fr.data_push_list(arr[pos:])
        else:
            out1 = {}
            out2 = {}
            for k in arr.keys():
                v = arr[k]
                if si.sortcomp(k, pos) < 0:
                    out1[k] = v
                else:
                    out2[k] = v
            fr.data_push_dict(out1)
            fr.data_push_dict(out2)


@instr("array_excludeval")
class InstArrayExcludeVal(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        val = fr.data_pop()
        arr = fr.data_pop_array()
        out = [k for k in arr.keys() if arr[k] != val]
        fr.data_push(out)


@instr("array_reverse")
class InstArrayReverse(Instruction):
    def execute(self, fr):
        arr = fr.data_pop_list()
        out = [x for x in reversed(arr)]
        fr.data_push_list(arr)


@instr("array_sort")
class InstArraySort(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        flags = fr.data_pop(int)
        arr = fr.data_pop_list()[:]
        nocase = flags & 1 != 0
        dorev = flags & 2 != 0
        doshuffle = flags & 4 != 0
        if doshuffle:
            for i in range(7):
                random.shuffle(arr)
        elif nocase:
            arr = sorted(arr, key=cmp_to_key(si.sortcompi), reverse=dorev)
        else:
            arr = sorted(arr, key=cmp_to_key(si.sortcomp), reverse=dorev)
        fr.data_push_list(arr)


@instr("array_sort_indexed")
class InstArraySortIndexed(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        idx = fr.data_pop(int, str)
        flags = fr.data_pop(int)
        arr = fr.data_pop_list()[:]
        nocase = flags & 1 != 0
        dorev = flags & 2 != 0
        doshuffle = flags & 4 != 0
        if doshuffle:
            random.shuffle(arr)
        elif nocase:
            arr = sorted(
                arr, reverse=dorev,
                key=cmp_to_key(lambda x, y: si.sortcompi(x[idx], y[idx])),
            )
        else:
            arr = sorted(
                arr, reverse=dorev,
                key=cmp_to_key(lambda x, y: si.sortcomp(x[idx], y[idx])),
            )
        fr.data_push_list(arr)


@instr("array_first")
class InstArrayFirst(Instruction):
    def execute(self, fr):
        arr = fr.data_pop_array()
        if not arr:
            fr.data_push(0)
            fr.data_push(0)
        elif isinstance(arr, si.MufList):
            fr.data_push(0)
            fr.data_push(1)
        else:
            keys = sorted(
                list(arr.keys()),
                key=cmp_to_key(si.sortcomp),
                reverse=False
            )
            fr.data_push(keys[0])
            fr.data_push(1)


@instr("array_last")
class InstArrayLast(Instruction):
    def execute(self, fr):
        arr = fr.data_pop_array()
        if not arr:
            fr.data_push(0)
            fr.data_push(0)
        elif isinstance(arr, si.MufList):
            fr.data_push(len(arr) - 1)
            fr.data_push(1)
        else:
            keys = sorted(
                list(arr.keys()),
                key=cmp_to_key(si.sortcomp),
                reverse=True
            )
            fr.data_push(keys[0])
            fr.data_push(1)


@instr("array_prev")
class InstArrayPrev(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        idx = fr.data_pop(int, str)
        arr = fr.data_pop_array()
        if not arr:
            fr.data_push(0)
            fr.data_push(0)
            return
        keys = [k for k in arr.keys() if si.sortcomp(k, idx) < 0]
        keys = sorted(keys, key=cmp_to_key(si.sortcomp), reverse=True)
        if keys:
            fr.data_push(keys[0])
            fr.data_push(1)
        else:
            fr.data_push(0)
            fr.data_push(0)


@instr("array_next")
class InstArrayNext(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        idx = fr.data_pop(int, str)
        arr = fr.data_pop_array()
        if not arr:
            fr.data_push(0)
            fr.data_push(0)
            return
        keys = [k for k in arr.keys() if si.sortcomp(k, idx) > 0]
        keys = sorted(keys, key=cmp_to_key(si.sortcomp))
        if keys:
            fr.data_push(keys[0])
            fr.data_push(1)
        else:
            fr.data_push(0)
            fr.data_push(0)


@instr("array_fmtstrings")
class InstArrayFmtStrings(Instruction):
    def execute(self, fr):
        def subfunc(matchobj):
            fmt = matchobj.group(1)
            key = matchobj.group(3)
            ftyp = matchobj.group(4)
            if ftyp == "%":
                return "%"
            elif ftyp == "i":
                val = d.get(key, 0)
                fr.check_type(val, [int])
                ftyp = "d"
            elif ftyp.lower() in ["e", "f", "g"]:
                val = d.get(key, 0.0)
                fr.check_type(val, [float])
            elif ftyp == "D" or ftyp == "d":
                val = d.get(key, si.DBRef(-1))
                fr.check_type(val, [si.DBRef])
                val = val if ftyp == "d" else db.getobj(val).name
                ftyp = "s"
            elif ftyp == "s":
                val = d.get(key, '')
                fr.check_type(val, [str])
            elif ftyp == "~":
                val = d.get(key, '')
                ftyp = "s"
            elif ftyp == "?":
                val = si.item_type_name(d.get(key, 0))
                ftyp = "s"
            else:
                return ""
            fmt = fmt.replace('|', '^')
            fmt = fmt + ftyp
            return fmt % val

        fmt = fr.data_pop(str)
        arr = fr.data_pop_list()
        fr.check_list_type(arr, (si.MufDict), argnum=1)
        outarr = []
        for d in arr:
            out = re.sub(
                r'(%[| 0+-]*[0-9]*(\.[0-9]*)?)\[([^]]+)\]([idDefgEFGsl%?~])',
                subfunc, fmt
            )
            outarr.append(out)
        fr.data_push_list(outarr)


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
