import re
import copy
import random
from functools import cmp_to_key

import mufsim.utils as util
import mufsim.gamedb as db
import mufsim.stackitems as si
from mufsim.errors import MufRuntimeError
from mufsim.insts.base import Instruction, instr


@instr("array_make")
class InstArrayMake(Instruction):
    def execute(self, fr):
        num = fr.data_pop(int)
        fr.check_underflow(num)
        arr = []
        for i in range(num):
            arr.insert(0, fr.data_pop())
        fr.data_push(arr)


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
        fr.data_push(d)


@instr("array_count")
class InstArrayCount(Instruction):
    def execute(self, fr):
        arr = fr.data_pop(list, dict)
        fr.data_push(len(arr))


@instr("array_compare")
class InstArrayCompare(Instruction):
    def execute(self, fr):
        arr2 = fr.data_pop(list, dict)
        arr1 = fr.data_pop(list, dict)
        fr.data_push(util.compare_dicts(arr1, arr2))


@instr("array_getitem")
class InstArrayGetItem(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        key = fr.data_pop()
        arr = fr.data_pop(list, dict)
        if isinstance(arr, list):
            if not isinstance(key, int):
                fr.data_push(0)
            elif key < 0 or key >= len(arr):
                fr.data_push(0)
            else:
                fr.data_push(arr[key])
        elif isinstance(arr, dict):
            if key in arr:
                fr.data_push(arr[key])
            else:
                fr.data_push(0)


@instr("array_setitem")
class InstArraySetItem(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        key = fr.data_pop()
        arr = fr.data_pop(list, dict)
        val = fr.data_pop()
        if isinstance(arr, list):
            if not isinstance(key, int):
                raise MufRuntimeError("List array expects integer index.")
            elif key < 0 or key > len(arr):
                raise MufRuntimeError("Index out of array bounds.")
            else:
                arr = arr[:]
                arr[key] = val
            fr.data_push(arr)
        elif isinstance(arr, dict):
            if not isinstance(key, int) and not isinstance(key, str):
                raise MufRuntimeError("Index must be integer or string.")
            arr = dict(arr)
            arr[key] = val
            fr.data_push(arr)


@instr("array_insertitem")
class InstArrayInsertItem(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        key = fr.data_pop()
        arr = fr.data_pop(list, dict)
        val = fr.data_pop()
        if isinstance(arr, list):
            if not isinstance(key, int):
                raise MufRuntimeError("List array expects integer index.")
            elif key < 0 or key > len(arr):
                raise MufRuntimeError("Index out of array bounds.")
            else:
                arr = arr[:]
                arr.insert(key, val)
            fr.data_push(arr)
        elif isinstance(arr, dict):
            if not isinstance(key, int) and not isinstance(key, str):
                raise MufRuntimeError("Index must be integer or string.")
            arr = dict(arr)
            arr[key] = val
            fr.data_push(arr)


@instr("array_delitem")
class InstArrayDelItem(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        key = fr.data_pop()
        arr = fr.data_pop(list, dict)
        if isinstance(arr, list):
            if not isinstance(key, int):
                raise MufRuntimeError("List array expects integer index.")
            elif key < 0 or key > len(arr):
                raise MufRuntimeError("Index out of array bounds.")
            else:
                arr = arr[:]
                del arr[key]
            fr.data_push(arr)
        elif isinstance(arr, dict):
            if not isinstance(key, int) and not isinstance(key, str):
                raise MufRuntimeError("Index must be integer or string.")
            arr = dict(arr)
            del arr[key]
            fr.data_push(arr)


@instr("array_appenditem")
class InstArrayAppendItem(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        arr = fr.data_pop(list)
        val = fr.data_pop()
        arr = arr[:]
        arr.append(val)
        fr.data_push(arr)


@instr("array_extract")
class InstArrayExtract(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        keys = fr.data_pop(list)
        arr = fr.data_pop(list, dict)
        if isinstance(arr, list):
            arr = {k: v for k, v in enumerate(arr)}
        out = {}
        for key in keys:
            if key in arr:
                out[key] = arr[key]
        fr.data_push(out)


@instr("array_getrange")
class InstArrayGetRange(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        end = fr.data_pop(int)
        st = fr.data_pop(int)
        arr = fr.data_pop(list)
        fr.data_push(arr[st:end + 1])


@instr("array_setrange")
class InstArraySetRange(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        items = fr.data_pop(list)
        st = fr.data_pop(int)
        arr = fr.data_pop(list)[:]
        for i, item in enumerate(items):
            arr[st + i] = item
        fr.data_push(arr)


@instr("array_delrange")
class InstArrayDelRange(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        end = fr.data_pop(int)
        st = fr.data_pop(int)
        arr = fr.data_pop(list)[:]
        if end >= len(arr):
            end = len(arr) - 1
        for i in range(st, end + 1):
            del arr[st]
        fr.data_push(arr)


@instr("array_insertrange")
class InstArrayInsertRange(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        items = fr.data_pop(list)
        st = fr.data_pop(int)
        arr = fr.data_pop(list)[:]
        if st < 0 or st > len(arr):
            raise MufRuntimeError("Index outside array bounds. (2)")
        for i, item in enumerate(items):
            arr.insert(st + i, item)
        fr.data_push(arr)


@instr("array_nested_get")
class InstArrayNestedGet(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        keys = fr.data_pop(list)
        arr = fr.data_pop(list, dict)
        for key in keys:
            if not isinstance(key, int) and not isinstance(key, str):
                raise MufRuntimeError("Index must be integer or string.")
            if isinstance(arr, list):
                arr = {idx: val for idx, val in enumerate(arr)}
            if not isinstance(arr, dict):
                arr = 0
                break
            elif key not in arr:
                arr = 0
                break
            else:
                arr = arr[key]
        fr.data_push(arr)


@instr("array_nested_set")
class InstArrayNestedSet(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        keys = fr.data_pop(list)
        arr = fr.data_pop(list, dict)
        val = fr.data_pop()
        arr = copy.deepcopy(arr)
        subarr = arr
        keyslen = len(keys)
        for keynum, key in enumerate(keys):
            if isinstance(subarr, list):
                fr.check_type(key, [int])
                if key < 0 or key > len(subarr):
                    raise MufRuntimeError("Index out of list array bounds.")
                if keynum < keyslen - 1:
                    if key == len(subarr):
                        subarr[key] = {}
                    subarr = subarr[key]
                else:
                    subarr[key] = val
            elif isinstance(subarr, dict):
                fr.check_type(key, [int, str])
                if keynum < keyslen - 1:
                    if key not in subarr:
                        subarr[key] = {}
                    subarr = subarr[key]
                else:
                    subarr[key] = val
            elif keynum < keyslen - 1:
                raise MufRuntimeError("Nested array not a list or dictionary.")
        fr.data_push(arr)


@instr("array_nested_del")
class InstArrayNestedDel(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        keys = fr.data_pop(list)
        arr = fr.data_pop(list, dict)
        arr = copy.deepcopy(arr)
        subarr = arr
        keyslen = len(keys)
        for keynum, key in enumerate(keys):
            if isinstance(subarr, list):
                fr.check_type(key, [int])
                if key < 0 or key > len(subarr):
                    raise MufRuntimeError("Index out of list array bounds.")
                if keynum < keyslen - 1:
                    if key == len(subarr):
                        subarr[key] = {}
                    subarr = subarr[key]
                else:
                    del subarr[key]
            elif isinstance(subarr, dict):
                fr.check_type(key, [int, str])
                if keynum < keyslen - 1:
                    if key not in subarr:
                        subarr[key] = {}
                    subarr = subarr[key]
                else:
                    del subarr[key]
            elif keynum < keyslen - 1:
                raise MufRuntimeError("Nested array not a list or dictionary.")
        fr.data_push(arr)


@instr("array_keys")
class InstArrayKeys(Instruction):
    def execute(self, fr):
        arr = fr.data_pop(list, dict)
        if isinstance(arr, list):
            for key, val in enumerate(arr):
                fr.data_push(key)
            fr.data_push(len(arr))
        elif isinstance(arr, dict):
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
        arr = fr.data_pop(list, dict)
        if isinstance(arr, list):
            for val in arr:
                fr.data_push(val)
            fr.data_push(len(arr))
        elif isinstance(arr, dict):
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
        arr = fr.data_pop(list, dict)
        if isinstance(arr, list):
            for key, val in enumerate(arr):
                fr.data_push(key)
                fr.data_push(val)
            fr.data_push(len(arr))
        elif isinstance(arr, dict):
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
        arr = fr.data_pop(list)
        out = ""
        for idx, val in enumerate(arr):
            if idx > 0:
                out += delim
            if isinstance(val, str):
                out += val
            elif isinstance(val, int):
                out += "%d" % val
            elif isinstance(val, float):
                out += "%g" % val
            elif isinstance(val, si.DBRef):
                out += "#%d" % val.value
            elif isinstance(val, si.Address):
                out += "Addr:%d" % val.value
            else:
                out += str(val)
        fr.data_push(out)


@instr("array_findval")
class InstArrayFindVal(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        val = fr.data_pop()
        arr = fr.data_pop(list, dict)
        if isinstance(arr, list):
            arr = {k: v for k, v in enumerate(arr)}
        out = []
        for k, v in arr.items():
            if v == val:
                out.append(k)
        fr.data_push(out)


@instr("array_matchkey")
class InstArrayMatchKey(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        pat = fr.data_pop(str)
        arr = fr.data_pop(list, dict)
        if isinstance(arr, list):
            arr = {k: v for k, v in enumerate(arr)}
        out = {}
        for k, v in arr.items():
            if isinstance(k, str) and util.smatch(pat, k):
                out[k] = v
        fr.data_push(out)


@instr("array_matchval")
class InstArrayMatchVal(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        pat = fr.data_pop(str)
        arr = fr.data_pop(list, dict)
        if isinstance(arr, list):
            arr = {k: v for k, v in enumerate(arr)}
        out = {}
        for k, v in arr.items():
            if isinstance(v, str) and util.smatch(pat, v):
                out[k] = v
        fr.data_push(out)


@instr("array_cut")
class InstArrayCut(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        pos = fr.data_pop(int, str)
        arr = fr.data_pop(list, dict)
        if isinstance(arr, list):
            if isinstance(pos, str):
                fr.data_push(arr[:])
                fr.data_push([])
            else:
                fr.data_push(arr[:pos])
                fr.data_push(arr[pos:])
        else:
            out1 = {}
            out2 = {}
            for k, v in arr.items():
                if si.sortcomp(k, pos) < 0:
                    out1[k] = v
                else:
                    out2[k] = v
            fr.data_push(out1)
            fr.data_push(out2)


@instr("array_excludeval")
class InstArrayExcludeVal(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        val = fr.data_pop()
        arr = fr.data_pop(list, dict)
        if isinstance(arr, list):
            arr = {k: v for k, v in enumerate(arr)}
        out = []
        for k, v in arr.items():
            if v != val:
                out.append(k)
        fr.data_push(out)


@instr("array_reverse")
class InstArrayReverse(Instruction):
    def execute(self, fr):
        arr = fr.data_pop(list)[:]
        arr = [x for x in reversed(arr)]
        fr.data_push(arr)


@instr("array_sort")
class InstArraySort(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        flags = fr.data_pop(int)
        arr = fr.data_pop(list)[:]
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
        fr.data_push(arr)


@instr("array_sort_indexed")
class InstArraySortIndexed(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        idx = fr.data_pop(int, str)
        flags = fr.data_pop(int)
        arr = fr.data_pop(list)[:]
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
        fr.data_push(arr)


@instr("array_first")
class InstArrayFirst(Instruction):
    def execute(self, fr):
        arr = fr.data_pop(list, dict)
        if not arr:
            fr.data_push(0)
            fr.data_push(0)
        elif isinstance(arr, list):
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
        arr = fr.data_pop(list, dict)
        if not arr:
            fr.data_push(0)
            fr.data_push(0)
        elif isinstance(arr, list):
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
        arr = fr.data_pop(list, dict)
        if not arr:
            fr.data_push(0)
            fr.data_push(0)
            return
        if isinstance(arr, list):
            keys = list(range(len(arr)))
        else:
            keys = list(arr.keys())
        keys = [k for k in keys if si.sortcomp(k, idx) < 0]
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
        arr = fr.data_pop(list, dict)
        if not arr:
            fr.data_push(0)
            fr.data_push(0)
            return
        if isinstance(arr, list):
            keys = list(range(len(arr)))
        else:
            keys = list(arr.keys())
        keys = [k for k in keys if si.sortcomp(k, idx) > 0]
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
        arr = fr.data_pop(list)
        outarr = []
        for d in arr:
            fr.check_type(d, [dict])
            out = re.sub(
                r'(%[| 0+-]*[0-9]*(\.[0-9]*)?)\[([^]]+)\]([idDefgEFGsl%?~])',
                subfunc, fmt
            )
            outarr.append(out)
        fr.data_push(outarr)


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
