# from mufsim.logger import log
import mufsim.gamedb as db
from mufsim.interface import network_interface as netifc


user_commands = {}
force_level = 0


def getword(txt, delim=' '):
    txt = txt.lstrip()
    if delim in txt:
        return txt.split(delim, 1)
    else:
        return (txt.strip(), '')


def time_format_1(secs):
    days = secs // 86400
    secs = secs % 86400
    hours = secs // 3600
    secs = secs % 3600
    mins = secs // 60
    secs = secs % 60
    out = ''
    if days > 0:
        out = "%dd " % days
    out += "%02d:%02d" % (hours, mins)
    return out


def time_format_2(secs):
    days = secs // 86400
    secs = secs % 86400
    hours = secs // 3600
    secs = secs % 3600
    mins = secs // 60
    secs = secs % 60
    if days > 0:
        return "%dd" % days
    if hours > 0:
        return "%dh" % hours
    if mins > 0:
        return "%dm" % mins
    return "%ds" % secs


def notify_descr_or_user(descr, user, txt):
    if db.validobj(user):
        userobj = db.getobj(user)
        userobj.notify(txt)
    else:
        netifc.descr_notify(descr, txt)


def usercommand(cmdname):
    def _wrapper(func):
        global user_commands
        cmd = cmdname
        while cmd:
            if cmd in user_commands:
                user_commands[cmd] = None
            else:
                user_commands[cmd] = func
            cmd = cmd[:-1]
        return func
    return _wrapper


@usercommand('QUIT')
def usercmd_quit(descr, user, cmd):
    netifc.descr_disconnect(descr)


@usercommand('connect')
def usercmd_connect(descr, user, cmd):
    if user is not None:
        notify_descr_or_user(descr, user, "Huh?")
        return
    username, cmd = getword(cmd)
    passwd, cmd = getword(cmd)
    if not username or not passwd or cmd:
        notify_descr_or_user(descr, user, "Bad connect syntax.")
        return
    user = db.match_playername('*' + username)
    try:
        playerobj = db.get_player_obj(username)
    except:
        notify_descr_or_user(descr, user, "Invalid playername or password.")
        return
    if playerobj.password != passwd:
        notify_descr_or_user(descr, user, "Invalid playername or password.")
        return
    netifc.descr_set_user(descr, playerobj.dbref)
    notify_descr_or_user(descr, user, "Welcome to MufSim!")
    usercmd_look(descr, playerobj.dbref, "")


@usercommand('look')
def usercmd_look(descr, user, cmd):
    if user is None:
        notify_descr_or_user(descr, user, "Huh?")
        return
    userobj = db.getobj(user)
    if not cmd:
        targobj = db.getobj(userobj.location)
    else:
        targ = db.match_noisy(user, cmd)
        if not db.validobj(targ):
            return
        targobj = db.getobj(targ)
    userobj.notify(targobj.unparse_for(user))
    desc = targobj.getprop('_/de')
    if not desc:
        desc = "You see nothing special."
    # TODO: process for MPI
    userobj.notify(desc)
    if targobj.contents:
        userobj.notify('Contents:')
        for obj in targobj.contents:
            obj = db.getobj(obj)
            userobj.notify(obj.unparse_for(user))


@usercommand('whisper')
def usercmd_whisper(descr, user, cmd):
    if user is None:
        netifc.descr_notify(descr, "Huh?")
        return
    userobj = db.getobj(user)
    targname, mesg = getword(cmd, '=')
    targref = match_noisy(userobj.dbref, targname)
    if not db.validobj(targref):
        return
    targobj = db.getobj(targref)
    if targobj.objtype != "player":
        userobj.notify("You can't whisper to a non-player.")
        return
    if not netifc.is_user_online(targobj.dbref):
        targobj.notify('%s is not awake.' % targobj.name)
        return
    targobj.notify('%s whispers, "%s" to you.' % (userobj.name, mesg))
    userobj.notify('You whisper, "%s" to %s.' % (mesg, targobj.name))


@usercommand('page')
def usercmd_page(descr, user, cmd):
    if user is None:
        netifc.descr_notify(descr, "Huh?")
        return
    userobj = db.getobj(user)
    targname, mesg = getword(cmd, '=')
    targref = match_playername(targname)
    if targref == -1:
        targref = match_playername_prefix(targname)
    if targref == -1:
        userobj.notify("I don't recognize that player.")
        return
    if targref == -2:
        userobj.notify("I don't know which player you mean.")
        return
    targobj = db.getobj(targref)
    if not netifc.is_user_online(targobj.dbref):
        targobj.notify('%s is not awake.' % targobj.name)
        return
    if not mesg:
        locname = db.getobj(userobj.location).name
        targobj.notify('%s is looking for you in %s.' % (userobj.name, locname))
        userobj.notify('You page %s.' % targobj.name)
    else:
        targobj.notify('%s pages, "%s" to you.' % (userobj.name, mesg))
        userobj.notify('You page, "%s" to %s.' % (mesg, targobj.name))


@usercommand('say')
def usercmd_say(descr, user, cmd):
    if user is None:
        netifc.descr_notify(descr, "Huh?")
        return
    loc = db.getobj(user).location
    conts = db.getobj(loc).contents
    userobj = db.getobj(user)
    for obj in conts:
        obj = db.getobj(obj)
        if obj.dbref == user:
            obj.notify('You say, "%s"' % cmd)
        else:
            obj.notify('%s says, "%s"' % (userobj.name, cmd))


@usercommand('pose')
def usercmd_pose(descr, user, cmd):
    if user is None:
        netifc.descr_notify(descr, "Huh?")
        return
    loc = db.getobj(user).location
    conts = db.getobj(loc).contents
    userobj = db.getobj(user)
    for obj in conts:
        obj = db.getobj(obj)
        if cmd.startswith("'"):
            obj.notify("%s%s" % (userobj.name, cmd))
        else:
            obj.notify("%s %s" % (userobj.name, cmd))


@usercommand('@who')
def usercmd_at_who(descr, user, cmd):
    if db.validobj(user) and 'W' in db.getobj(user).flags:
        fmt = (
            "{name:<30s} {loc:>8s} {time:>10s} {idle:>4s}"
            "{iflag:1s}{secure:1s} {remote}"
        )
    else:
        fmt = "{name:<30s} {time:>10s} {idle:>4s}{iflag:1s}{secure:1s}"
    data = dict(
        name="Name",
        loc="Location",
        time="On For",
        idle="Idle",
        iflag=' ',
        secure=' ',
        remote="Remote Host",
    )
    netifc.descr_notify(descr, fmt.format(**data))
    outdata = []
    for descr in netifc.get_descriptors():
        targuser = netifc.descr_dbref(descr)
        if not db.validobj(targuser):
            continue
        targobj = db.getobj(targuser)
        rem_user = netifc.descr_user(descr)
        rem_host = netifc.descr_host(descr)
        remote = "@".join([x for x in [rem_user, rem_host] if x])
        iflag = ' '
        if 'I' in targobj.flags:
            iflag = '*'
        data = dict(
            name=targobj.name,
            loc="[%d]" % targobj.location,
            time=time_format_1(netifc.descr_time(descr)),
            timesecs=netifc.descr_time(descr),
            idle=time_format_2(netifc.descr_idle(descr)),
            iflag=iflag,
            secure=('@' if netifc.descr_secure(descr) else ' '),
            remote=remote,
        )
        outdata.append(data)
    outdata.sort(key=lambda x: x['timesecs'])
    for data in outdata:
        if not cmd or data['name'].startswith(cmd):
            netifc.descr_notify(descr, fmt.format(**data))
    netifc.descr_notify(descr, "%d users online." % len(outdata))


@usercommand('@dig')
def usercmd_at_dig(descr, user, cmd):
    if user is None:
        notify_descr_or_user(descr, user, "Huh?")
        return
    userobj = db.getobj(user)
    roomname, cmd = getword(cmd, '=')
    envroom, regname = getword(cmd, '=')
    regname = regname.strip()
    envref = match_from(userobj.dbref, envroom)
    if not db.validobj(envref):
        userobj.notify("I don't know which room you mean.")
        return
    envobj = db.getobj(envref)
    if envobj.objtype != "room":
        userobj.notify("I don't know which room you mean.")
        return
    newroom = db.DBObject(
        name=roomname.strip(),
        objtype="room",
        location=envobj.dbref,
        owner=user,
    )
    if regname:
        db.register_obj(user, regname, newroom.dbref)
    userobj.notify("Room created as #%d." % newroom.dbref)


@usercommand('@action')
def usercmd_at_action(descr, user, cmd):
    if user is None:
        notify_descr_or_user(descr, user, "Huh?")
        return
    userobj = db.getobj(user)
    exitname, cmd = getword(cmd, '=')
    srcname, regname = getword(cmd, '=')
    regname = regname.strip()
    srcref = match_controlled(userobj.dbref, srcname)
    if not db.validobj(srcref):
        return
    srcobj = db.getobj(srcref)
    newexit = db.DBObject(
        name=exitname.strip(),
        objtype="exit",
        location=srcobj.dbref,
        owner=user,
    )
    if regname:
        db.register_obj(user, regname, newexit.dbref)
    userobj.notify("Exit created as #%d." % newexit.dbref)


@usercommand('@open')
def usercmd_at_open(descr, user, cmd):
    if user is None:
        notify_descr_or_user(descr, user, "Huh?")
        return
    userobj = db.getobj(user)
    exitname, cmd = getword(cmd, '=')
    dests, regname = getword(cmd, '=')
    regname = regname.strip()
    destrefs = []
    for destname in dests.split(';'):
        destname = destname.strip()
        destref = match_controlled(userobj.dbref, destname)
        if not db.validobj(destref):
            return
        destrefs.append(destref)
    newexit = db.DBObject(
        name=exitname.strip(),
        objtype="exit",
        location=srcobj.dbref,
        owner=user,
    )
    newexit.links = destrefs
    if regname:
        db.register_obj(user, regname, newexit.dbref)
    userobj.notify("Exit created as #%d." % newexit.dbref)


@usercommand('@pcreate')
def usercmd_at_pcreate(descr, user, cmd):
    if user is None:
        notify_descr_or_user(descr, user, "Huh?")
        return
    userobj = db.getobj(user)
    newname, passwd = getword(cmd, '=')
    newname = newname.strip()
    passwd = passwd.strip()
    if not db.ok_player_name(newname):
        userobj.notify("Bad name.")
        return
    main_room = db.get_registered_obj(user, "mainroom")
    newobj = db.DBObject(
        name=newname,
        objtype="player",
        flags="1",
        location=main_room,
        passwd=passwd,
        props={},
        pennies=100,
    )
    if regname:
        db.register_obj(user, regname, newobj.dbref)
    userobj.notify("Thing created as #%d." % newobj.dbref)


@usercommand('@create')
def usercmd_at_create(descr, user, cmd):
    if user is None:
        notify_descr_or_user(descr, user, "Huh?")
        return
    userobj = db.getobj(user)
    thingname, cmd = getword(cmd, '=')
    cost, regname = getword(cmd, '=')
    regname = regname.strip()
    newthing = db.DBObject(
        name=thingname.strip(),
        objtype="thing",
        location=user,
        owner=user,
        pennies=((cost/5)-1),
    )
    if regname:
        db.register_obj(user, regname, newthing.dbref)
    userobj.notify("Thing created as #%d." % newthing.dbref)


@usercommand('@teleport')
def usercmd_at_teleport(descr, user, cmd):
    if user is None:
        notify_descr_or_user(descr, user, "Huh?")
        return
    userobj = db.getobj(user)
    objname, destname = getword(cmd, '=')
    objname = objname.strip()
    destname = destname.strip()
    obj = match_controlled(user, objname)
    if not db.validobj(obj):
        return
    destref = match_controlled(user, destname)
    if not db.validobj(destref):
        return
    obj = db.getobj(obj)
    destobj = db.getobj(destref)
    if destobj.objtype in ["exit", "program"]:
        userobj.notify("Cannot teleport objects there.")
    if obj.objtype == "room" and destobj.objtype != "room":
        userobj.notify("Cannot teleport rooms into non-rooms.")
    obj.moveto(destobj.dbref)
    userobj.notify("Teleported.")


@usercommand('@set')
def usercmd_at_set(descr, user, cmd):
    if user is None:
        notify_descr_or_user(descr, user, "Huh?")
        return
    userobj = db.getobj(user)
    objname, flag = getword(cmd, '=')
    obj = match_controlled(user, objname)
    if not db.validobj(obj):
        return
    if ':' in flag:
        propname, value = flag.split(':')
        propname = propname.strip()
        if value:
            obj.setprop(propname, value)
        else:
            obj.delprop(propname)
        userobj.notify("Property set.")
    else:
        flag = flag.strip().upper()[:1]
        if not flag:
            userobj.notify("Bad flag.")
            return
        obj.flags = "".join(set((obj.flags + flag).upper()))
        userobj.notify("Flag set.")


@usercommand('@program')
def usercmd_at_program(descr, user, cmd):
    if user is None:
        notify_descr_or_user(descr, user, "Huh?")
        return
    userobj = db.getobj(user)
    progname, regname = getword(cmd, '=')
    progname = progname.strip()
    regname = regname.strip()
    newprog = db.DBObject(
        name=progname,
        objtype="program",
        flags="3",
        owner=user,
        location=user,
    )
    if regname:
        db.register_obj(user, regname, newprog.dbref)
    userobj.notify("Program created as #%d." % newprog.dbref)


@usercommand('@edit')
def usercmd_at_edit(descr, user, cmd):
    if user is None:
        notify_descr_or_user(descr, user, "Huh?")
        return
    pass


@usercommand('@unlink')
def usercmd_at_unlink(descr, user, cmd):
    if user is None:
        notify_descr_or_user(descr, user, "Huh?")
        return
    userobj = db.getobj(user)
    objname = cmd.strip()
    obj = match_controlled(user, objname)
    if not db.validobj(obj):
        return
    obj = db.getobj(obj)
    obj.links = {}
    userobj.notify("Unlinked.")


@usercommand('@link')
def usercmd_at_link(descr, user, cmd):
    if user is None:
        netifc.descr_notify(descr, "Huh?")
        return
    userobj = db.getobj(user)
    objname, dests = getword(cmd, '=')
    obj = match_controlled(user, objname)
    if not db.validobj(obj):
        return
    destrefs = []
    for destname in dests.split(';'):
        destname = destname.strip()
        destref = match_controlled(userobj.dbref, destname)
        if not db.validobj(destref):
            return
        destrefs.append(destref)
    obj = db.getobj(obj)
    obj.links = destrefs
    userobj.notify("Linked.")


@usercommand('@chown')
def usercmd_at_chown(descr, user, cmd):
    if user is None:
        notify_descr_or_user(descr, user, "Huh?")
        return
    userobj = db.getobj(user)
    objname, newowner = getword(cmd, '=')
    objname = objname.strip()
    newowner = newowner.strip()
    obj = match_controlled(user, objname)
    if not db.validobj(obj):
        return
    newowner = match_controlled(user, newowner)
    if not db.validobj(newowner):
        return
    obj = db.getobj(obj)
    ownerobj = db.getobj(newowner)
    if ownerobj.objtype != "player":
        userobj.notify("Cannot chown objects to non-players.")
    obj.owner = ownerobj.dbref
    userobj.notify("Chowned.")


def get_force_level():
    global force_level
    return force_level


def process_command(proclist, descr, user, cmd):
    global force_level, user_commands
    try:
        force_level += 1
        if cmd.lstrip().startswith(':'):
            cmd = 'pose ' + cmd.lstrip()[1:]
        elif cmd.lstrip().startswith('"'):
            cmd = 'say ' + cmd.lstrip()[1:]
        elif cmd.lstrip().startswith('WHO'):
            cmd = '@who ' + cmd.lstrip()[3:]
        word, cmdarg = getword(cmd)
        trig = -1
        if db.validobj(user):
            trig = db.match_all_exits(user, word)
        if trig < 0:
            if word in user_commands:
                cmdfunc = user_commands[word]
                if cmdfunc is None:
                    notify_descr_or_user(descr, user, "Huh?")
                    return
                cmdfunc(descr, user, cmdarg)
                return
            notify_descr_or_user(descr, user, "Huh?")
            return
        links = db.links_array(trig)
        if not links:
            notify_descr_or_user(descr, user, "Huh?")
            return
        if db.getobj(links[0]).objtype != "program":
            # TODO: moveto room, or fetch thing on non-program?
            notify_descr_or_user(descr, user, "Huh?")
            return
        progobj = db.getobj(links[0])
        userobj = db.getobj(user)
        trigobj = db.getobj(trig)
        if not progobj.compiled:
            notify_descr_or_user(descr, user, "Program not compiled.")
            return
        newproc = proclist.new_process()
        newproc.setup(progobj, userobj, trigobj, cmdarg)
        newproc.descr = descr
        newproc.execute_code()
    finally:
        force_level -= 1


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
