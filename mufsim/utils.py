import re


def escape_str(s):
    out = ''
    for ch in list(s):
        if ch == "\r" or ch == "\n":
            out += "\\r"
        elif ch == "\033":
            out += "\\["
        elif ch == "\\":
            out += "\\\\"
        elif ch == '"':
            out += '\\"'
        else:
            out += ch
    return '"%s"' % out


def is_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


def is_dbref(s):
    if s[0] != '#':
        return False
    try:
        int(s[1:])
        return True
    except ValueError:
        return False


def is_float(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def is_number(s):
    return(is_int(s) or is_float(s))


def is_strlit(s):
    return s[0] == '"' and s[-1] == '"'


def smatch(pat, txt):
    pats = [
        ('{', '\b('),
        ('}', ')\b'),
        ('?', '.'),
        ('*', '.*'),
    ]
    for fnd, repl in pats:
        pat = pat.replace(fnd, repl)
    try:
        pat = re.compile(pat, re.IGNORECASE)
    except:
        return False
    if pat.search(txt):
        return True
    return False


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
