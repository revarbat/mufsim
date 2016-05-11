import re
import random

import mufsim.utils as util
import mufsim.stackitems as si
from mufsim.errors import MufRuntimeError
from mufsim.insts.base import Instruction, instr


@instr("fmtstring")
class InstFmtString(Instruction):
    def handle_fieldsubs(self, fmt, fr):
        while '*' in fmt:
            pre, post = fmt.split('*', 1)
            x = fr.data_pop(int)
            fmt = pre + str(x) + post
        fmt = fmt.replace('|', '^')
        return fmt

    def execute(self, fr):
        def subfunc(matchobj):
            fmt = matchobj.group(1)
            ftyp = matchobj.group(3)
            if ftyp == "%":
                return "%"
            elif ftyp == "i":
                val = fr.data_pop(int)
                ftyp = "d"
            elif ftyp.lower() in ["e", "f", "g"]:
                val = fr.data_pop(float)
            elif ftyp == "s":
                val = fr.data_pop(str)
            elif ftyp == "D":
                val = fr.data_pop_object().name
                ftyp = "s"
            elif ftyp == "d":
                val = fr.data_pop_dbref()
                ftyp = "s"
            elif ftyp == "~":
                val = si.item_repr(fr.data_pop())
                ftyp = "s"
            elif ftyp == "?":
                val = si.item_type_name(fr.data_pop())
                ftyp = "s"
            else:
                return ""
            fmt = self.handle_fieldsubs(fmt, fr)
            fmt = fmt + ftyp
            return fmt % val

        fmt = fr.data_pop(str)
        out = re.sub(
            r'(%[| 0+-]*[0-9]*(\.[0-9]*)?)([idDefgEFGsl%?~])',
            subfunc, fmt
        )
        fr.data_push(out)


@instr("explode_array")
class InstExplodeArray(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        delim = fr.data_pop(str)
        txt = fr.data_pop(str)
        fr.data_push(txt.split(delim))


@instr("toupper")
class InstToUpper(Instruction):
    def execute(self, fr):
        txt = fr.data_pop(str)
        fr.data_push(txt.upper())


@instr("tolower")
class InstToLower(Instruction):
    def execute(self, fr):
        txt = fr.data_pop(str)
        fr.data_push(txt.lower())


@instr("explode")
class InstExplode(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        delim = fr.data_pop(str)
        txt = fr.data_pop(str)
        if not delim:
            raise MufRuntimeError("Expected non-null string argument. (2)")
        parts = txt.split(delim)
        for part in reversed(parts):
            fr.data_push(part)
        fr.data_push(len(parts))


@instr("split")
class InstSplit(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        delim = fr.data_pop(str)
        txt = fr.data_pop(str)
        parts = txt.split(delim, 1)
        fr.data_push(parts[0])
        if len(parts) > 1:
            fr.data_push(parts[1])
        else:
            fr.data_push("")


@instr("rsplit")
class InstRSplit(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        delim = fr.data_pop(str)
        txt = fr.data_pop(str)
        parts = txt.rsplit(delim, 1)
        fr.data_push(parts[0])
        if len(parts) > 1:
            fr.data_push(parts[1])
        else:
            fr.data_push("")


@instr("striplead")
class InstStripLead(Instruction):
    def execute(self, fr):
        txt = fr.data_pop(str)
        fr.data_push(txt.lstrip())


@instr("striptail")
class InstStripTail(Instruction):
    def execute(self, fr):
        txt = fr.data_pop(str)
        fr.data_push(txt.rstrip())


@instr("strlen")
class InstStrLen(Instruction):
    def execute(self, fr):
        txt = fr.data_pop(str)
        fr.data_push(len(txt))


@instr("strcat")
class InstStrCat(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        txt2 = fr.data_pop(str)
        txt = fr.data_pop(str)
        fr.data_push(txt + txt2)


@instr("instr")
class InstInstr(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        fnd = fr.data_pop(str)
        txt = fr.data_pop(str)
        fr.data_push(txt.find(fnd) + 1)


@instr("instring")
class InstInString(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        fnd = fr.data_pop(str).lower()
        txt = fr.data_pop(str).lower()
        fr.data_push(txt.find(fnd) + 1)


@instr("rinstr")
class InstRInstr(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        fnd = fr.data_pop(str)
        txt = fr.data_pop(str)
        fr.data_push(txt.rfind(fnd) + 1)


@instr("rinstring")
class InstRInString(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        fnd = fr.data_pop(str).lower()
        txt = fr.data_pop(str).lower()
        fr.data_push(txt.rfind(fnd) + 1)


@instr("strcut")
class InstStrCut(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(int)
        a = fr.data_pop(str)
        fr.data_push(a[:b])
        fr.data_push(a[b:])


@instr("midstr")
class InstMidStr(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        num = fr.data_pop(int)
        pos = fr.data_pop(int)
        s = fr.data_pop(str)
        fr.data_push(s[pos - 1:pos + num - 1])


@instr("regexp")
class InstRegExp(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        flags = fr.data_pop(int)
        pat = fr.data_pop(str)
        txt = fr.data_pop(str)
        flgs = 0
        if (flags % 0x1) != 0:
            flgs |= re.IGNORECASE
        try:
            pat = re.compile(pat, flgs)
        except:
            raise MufRuntimeError("Malformed regexp pattern. (2)")
        matches = pat.search(txt)
        if not matches:
            fr.data_push([])
            fr.data_push([])
        else:
            submatches = []
            indexes = []
            for i in range(len(matches.groups()) + 1):
                submatches.append(matches.group(i))
                indexes.append(list(matches.span(i)))
            fr.data_push(submatches)
            fr.data_push(indexes)


@instr("regsub")
class InstRegSub(Instruction):
    def execute(self, fr):
        fr.check_underflow(4)
        flags = fr.data_pop(int)
        repl = fr.data_pop(str)
        pat = fr.data_pop(str)
        txt = fr.data_pop(str)
        flgs = 0
        if (flags % 0x1) != 0:
            flgs |= re.IGNORECASE
        try:
            val = re.sub(pat, repl, txt, flgs)
        except:
            raise MufRuntimeError("Malformed regexp pattern. (2)")
        fr.data_push(val)


@instr("subst")
class InstSubst(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        fnd = fr.data_pop(str)
        repl = fr.data_pop(str)
        txt = fr.data_pop(str)
        fr.data_push(txt.replace(fnd, repl))


@instr("strcmp")
class InstStrCmp(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(str)
        a = fr.data_pop(str)
        fr.data_push((a > b) - (a < b))


@instr("strncmp")
class InstStrNCmp(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        n = fr.data_pop(int)
        b = fr.data_pop(str)[:n]
        a = fr.data_pop(str)[:n]
        fr.data_push((a > b) - (a < b))


@instr("stringcmp")
class InstStringCmp(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(str).upper()
        a = fr.data_pop(str).upper()
        fr.data_push((a > b) - (a < b))


@instr("stringpfx")
class InstStringPfx(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        b = fr.data_pop(str).upper()
        a = fr.data_pop(str).upper()
        fr.data_push(1 if a.startswith(b) else 0)


@instr("smatch")
class InstSMatch(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        pat = fr.data_pop(str).upper()
        txt = fr.data_pop(str).upper()
        fr.data_push(1 if util.smatch(pat, txt) else 0)


@instr("strencrypt")
class InstStrEncrypt(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        key = fr.data_pop(str)
        data = fr.data_pop(str)
        enarr = list(range(256))
        for i in range(ord('A'), ord('M') + 1):
            enarr[i] += 13
        for i in range(ord('N'), ord('Z') + 1):
            enarr[i] -= 13
        enarr[13] = 127
        enarr[127] = 13
        enarr[27] = 31
        enarr[31] = 27
        charcount = 97
        seed = 0
        for cp in list(key):
            seed = ((ord(cp) ^ seed) + 170) % 192
        seed2 = 0
        for cp in list(data):
            seed2 = ((ord(cp) ^ seed2) + 21) & 0xff
        seed3 = seed2 = (seed2 ^ (seed ^ random.randint(0, 255))) & 0x3f
        count = seed + 11
        repkey = key * (len(data) / len(key) + 1)
        repkey = repkey[:len(data)]
        out = chr(32 + 2) + chr(32 + seed3)
        for upt, cp in zip(list(data), list(repkey)):
            count = ((ord(cp) ^ count) + (seed ^ seed2)) & 0xff
            seed2 = (seed2 + 1) & 0x3f
            result = (enarr[ord(upt)] - (32 - (charcount - 96))) + count + seed
            ups = enarr[(result % charcount) + (32 - (charcount - 96))]
            count = ((ord(upt) ^ count) + seed) & 0xff
            out += chr(ups)
        fr.data_push(out)


@instr("strdecrypt")
class InstStrDecrypt(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        key = fr.data_pop(str)
        data = fr.data_pop(str)
        if not data:
            fr.data_push("")
            return
        enarr = list(range(256))
        for i in range(ord('A'), ord('M') + 1):
            enarr[i] += 13
        for i in range(ord('N'), ord('Z') + 1):
            enarr[i] -= 13
        enarr[13] = 127
        enarr[127] = 13
        enarr[27] = 31
        enarr[31] = 27
        charset_count = [96, 97]
        rev = ord(data[0]) - 32
        if rev not in [1, 2]:
            fr.data_push("")
            return
        chrcnt = charset_count[rev - 1]
        seed2 = ord(data[1]) - 32
        data = data[2:]
        seed = 0
        for cp in list(key):
            seed = ((ord(cp) ^ seed) + 170) % 192
        count = seed + 11
        repkey = key * (len(data) / len(key) + 1)
        repkey = repkey[:len(data)]
        out = ''
        for upt, cp in zip(list(data), list(repkey)):
            count = ((ord(cp) ^ count) + (seed ^ seed2)) & 0xff
            seed2 = (seed2 + 1) & 0x3f
            result = (enarr[ord(upt)] - (32 - (chrcnt - 96))) - (count + seed)
            while result < 0:
                result += chrcnt
            ups = enarr[result + (32 - (chrcnt - 96))]
            count = ((ups ^ count) + seed) & 0xff
            out += chr(ups)
        fr.data_push(out)


@instr("tokensplit")
class InstTokenSplit(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        esc = fr.data_pop(str)
        delim = fr.data_pop(str)
        txt = fr.data_pop(str)
        txtlen = len(txt)
        pos = 0
        while pos < txtlen:
            if txt[pos] in esc:
                pos += 2
                continue
            if txt[pos] in delim:
                break
            pos += 1
        fr.data_push(txt[:pos])
        fr.data_push(txt[pos + 1:])
        fr.data_push(txt[pos])


@instr("pronoun_sub")
class InstPronounSub(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        txt = fr.data_pop(str)
        obj = fr.data_pop_object()
        sex = obj.getprop("sex")
        if not isinstance(sex, str):
            sex = ""
        if sex.strip().lower() == "male":
            subs = {
                "%a": "his",
                "%s": "he",
                "%o": "him",
                "%p": "his",
                "%r": "himself",
                "%n": obj.name,
                "%A": "His",
                "%S": "He",
                "%O": "Him",
                "%P": "His",
                "%R": "Himself",
                "%N": obj.name,
            }
        elif sex.strip().lower() == "female":
            subs = {
                "%a": "hers",
                "%s": "she",
                "%o": "her",
                "%p": "her",
                "%r": "herself",
                "%n": obj.name,
                "%A": "Hers",
                "%S": "She",
                "%O": "Her",
                "%P": "Her",
                "%R": "Herself",
                "%N": obj.name,
            }
        elif sex.strip().lower() in ["herm", "hermaphrodite"]:
            subs = {
                "%a": "hirs",
                "%s": "shi",
                "%o": "hir",
                "%p": "hir",
                "%r": "hirself",
                "%n": obj.name,
                "%A": "Hirs",
                "%S": "Shi",
                "%O": "Hir",
                "%P": "Hir",
                "%R": "Hirself",
                "%N": obj.name,
            }
        else:
            subs = {
                "%a": "its",
                "%s": "it",
                "%o": "it",
                "%p": "its",
                "%r": "itself",
                "%n": obj.name,
                "%A": "Its",
                "%S": "It",
                "%O": "It",
                "%P": "Its",
                "%R": "Itself",
                "%N": obj.name,
            }
        for fnd, repl in subs.items():
            txt = txt.replace(fnd, repl)
        fr.data_push(txt)


@instr("textattr")
class InstTextAttr(Instruction):
    ATTRCODES = {
        "reset": "0",
        "bold": "1",
        "dim": "2",
        "uline": "4",
        "flash": "5",
        "reverse": "7",
        "black": "30",
        "red": "31",
        "green": "32",
        "yellow": "33",
        "blue": "34",
        "magenta": "35",
        "cyan": "36",
        "white": "37",
        "bg_black": "40",
        "bg_red": "41",
        "bg_green": "42",
        "bg_yellow": "43",
        "bg_blue": "44",
        "bg_magenta": "45",
        "bg_cyan": "46",
        "bg_white": "47",
    }

    def execute(self, fr):
        fr.check_underflow(2)
        attrs = fr.data_pop(str)
        txt = fr.data_pop(str)
        codes = []
        endcode = ""
        for attr in attrs.split(','):
            attr = attr.strip()
            if attr in self.ATTRCODES:
                codes.append(self.ATTRCODES[attr])
        if codes:
            codes = "\033[%sm" % ";".join(codes)
            endcode = "\033[0m"
        fr.data_push(codes + txt + endcode)


@instr("ansi_strip")
class InstAnsiStrip(Instruction):
    def execute(self, fr):
        txt = fr.data_pop(str)
        pos = 0
        txtlen = len(txt)
        out = ""
        while pos < txtlen:
            if txt[pos] == "\033":
                while pos < txtlen and txt[pos] != "m":
                    pos += 1
                pos += 1
                continue
            out += txt[pos]
            pos += 1
        fr.data_push(out)


@instr("ansi_strlen")
class InstAnsiStrLen(Instruction):
    def execute(self, fr):
        txt = fr.data_pop(str)
        pos = 0
        txtlen = len(txt)
        outlen = 0
        while pos < txtlen:
            if txt[pos] == "\033":
                while pos < txtlen and txt[pos] != "m":
                    pos += 1
                pos += 1
                continue
            pos += 1
            outlen += 1
        fr.data_push(outlen)


@instr("ansi_strcut")
class InstAnsiStrCut(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        cutpos = fr.data_pop(int)
        txt = fr.data_pop(str)
        pos = 0
        txtlen = len(txt)
        while pos < txtlen:
            if cutpos == 0:
                break
            if txt[pos] == "\033":
                while pos < txtlen and txt[pos] != "m":
                    pos += 1
                pos += 1
                continue
            pos += 1
            cutpos -= 1
        fr.data_push(txt[:pos])
        fr.data_push(txt[pos:])


@instr("ansi_midstr")
class InstAnsiMidStr(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        end = fr.data_pop(int)
        start = fr.data_pop(int) - 1
        txt = fr.data_pop(str)
        pos = 0
        strpos = 0
        end += start
        txtlen = len(txt)
        while pos < txtlen:
            if strpos >= start:
                break
            if txt[pos] == "\033":
                while pos < txtlen and txt[pos] != "m":
                    pos += 1
                pos += 1
                continue
            pos += 1
            strpos += 1
        start = pos
        while pos < txtlen:
            if strpos >= end:
                break
            if txt[pos] == "\033":
                while pos < txtlen and txt[pos] != "m":
                    pos += 1
                pos += 1
                continue
            pos += 1
            strpos += 1
        end = pos
        fr.data_push(txt[start:end])


@instr("atoi")
class InstAtoI(Instruction):
    def execute(self, fr):
        a = fr.data_pop(str)
        try:
            fr.data_push(int(a))
        except:
            fr.data_push(0)


@instr("stod")
class InstStoD(Instruction):
    def execute(self, fr):
        a = fr.data_pop(str)
        if a[0] == '#':
            a = a[1:]
        try:
            fr.data_push(si.DBRef(int(a)))
        except:
            fr.data_push(si.DBRef(-1))


@instr("intostr")
class InstIntostr(Instruction):
    def execute(self, fr):
        a = fr.data_pop(int)
        fr.data_push("%d" % a)


@instr("itoc")
class InstItoC(Instruction):
    def execute(self, fr):
        c = fr.data_pop(int)
        if c == 13 or c == 27 or c >= 32 or c < 127:
            fr.data_push("%c" % c)
        else:
            fr.data_push("")


@instr("ctoi")
class InstCtoI(Instruction):
    def execute(self, fr):
        c = ord(fr.data_pop(str)[0])
        if c == 13 or c == 27 or c >= 32 or c < 127:
            fr.data_push(c)
        else:
            fr.data_push(0)


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
