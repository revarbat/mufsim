import mufsim.stackitems as si

descriptors_list = []
descriptors = {}

MAX_DESCR = 1024


def get_descriptors():
    global descriptors_list
    return descriptors_list


def _gen_descr(who):
    global descriptors
    descr = (who * 2 + 1) % MAX_DESCR
    while descr in descriptors:
        descr = (descr + 1) % MAX_DESCR
    return descr


def connect(who):
    global descriptors_list
    global descriptors
    descr = _gen_descr(who)
    descriptors_list.append(descr)
    descriptors[descr] = who
    return descr


def disconnect(descr):
    global descriptors_list
    global descriptors
    if descr not in descriptors:
        return False
    descriptors_list.remove(descr)
    del descriptors[descr]
    return True


def reconnect(descr, who):
    global descriptors_list
    global descriptors
    if descr not in descriptors:
        return False
    descriptors[descr] = who
    return True


def user_descrs(who):
    global descriptors_list
    global descriptors
    return [
        d for d in descriptors_list if descriptors[d] == who
    ]


def user_cons(who):
    global descriptors_list
    global descriptors
    return [
        i + 1 for i, d in enumerate(descriptors_list)
        if descriptors[d] == who
    ]


def is_user_online(who):
    global descriptors
    return who in list(descriptors.values())


def is_descr_online(descr):
    global descriptors
    return descr in descriptors


def descr_flush(descr):
    pass


def descr_bufsize(descr):
    global descriptors
    if descr in descriptors:
        return 4096
    return 0


def descr_secure(descr):
    global descriptors
    if descr in descriptors:
        # TODO: report real SSL secured info.
        return ((descr - 1) / 2) % 2 == 1
    return False


def flush_all_descrs():
    global descriptors
    for descr in descriptors_list:
        descr_flush(descr)


def descr_from_con(num):
    global descriptors_list
    try:
        return descriptors_list[num]
    except:
        return -1


def descr_user(descr):
    global descriptors
    if descr not in descriptors:
        return -1
    return descriptors[descr]


def descr_time(descr):
    global descriptors
    if descr not in descriptors:
        return 0
    # TODO: Generate real connection times.
    return descr * 731 + 1


def descr_idle(descr):
    global descriptors
    if descr not in descriptors:
        return 0
    # TODO: Generate real idle times.
    return descr * 79 + 1


def descr_host(descr):
    global descriptors
    if descr not in descriptors:
        return ""
    return "host%d.remotedomain.com" % descr


def descr_con(descr):
    global descriptors_list
    global descriptors
    if descr not in descriptors:
        return -1
    return descriptors_list.index(descr)


def get_users_online():
    global descriptors_list
    global descriptors
    return [
        si.DBRef(descriptors[d])
        for d in descriptors_list
    ]


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
