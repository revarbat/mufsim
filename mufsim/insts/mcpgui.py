from mudclientprotocol import (
    McpMessage, McpPackage, mktoken
)

from mufsim.errors import MufRuntimeError
from mufsim.insts.base import Instruction, instr
from mufsim.interface import network_interface
import mufsim.stackitems as si


existing_dialogs = {}


def get_dlog(dlogid):
    global existing_dialogs
    return existing_dialogs.get(dlogid)


def add_dlog(dlogid, dlog):
    global existing_dialogs
    existing_dialogs[dlogid] = dlog


def del_dlog(dlogid):
    global existing_dialogs
    if dlogid in existing_dialogs:
        del existing_dialogs[dlogid]


def version2float(vers):
    major, minor = vers.split('.', 1)
    try:
        major = int(major)
        minor = int(minor)
    except ValueError:
        major = 0
        minor = 0
    return (major + (minor / 1000.0))


class McpGuiDialog(object):
    def __init__(self, descr, pid):
        self.pid = pid
        self.descr = descr
        self.values = {}
        while True:
            dlogid = mktoken()
            if not get_dlog(dlogid):
                break
        self.dlogid = dlogid
        add_dlog(dlogid, self)

    def get_id(self):
        return self.dlogid

    def getvalue(self, name, dflt=None):
        return self.values.get(name, dflt)

    def setvalue(self, name, val):
        self.values[name] = val

    def send_message(self, mesg, **kwargs):
        msg = McpMessage(
            'org-fuzzball-gui-%s' % mesg,
            dlogid=self.dlogid,
        )
        msg.extend(kwargs)
        mcp = netifc.descr_mcp_connection(self.descr)
        mcp.send_message(msg)


class McpGuiPackage(McpPackage):
    def __init__(self):
        McpPackage.__init__(self, 'org-fuzzball-gui', '1.0', '1.3')

    def process_value_msg(self, msg):
        dlogid = msg.get('dlogid')
        ctrlid = msg.get('id')
        value = msg.get('value')
        if value is None:
            return
        dlog = get_dlog(dlogid)
        if not dlog:
            return
        dlog.setvalue(ctrlid, value)

    def process_event_msg(self, msg):
        descr = msg.context
        dlogid = msg.get('dlogid')
        ctrlid = msg.get('id', '')
        event = msg.get('event', '')
        dismissed = msg.get('dismissed', '0')
        data = msg.get('data', [])
        dlog = get_dlog(dlogid)
        if not dlog:
            return
        from mufsim.processlist import process_list
        fr = process_list.get(dlog.pid)
        if fr is None:
            return
        dismissed = 0 if dismissed == '0' else 1
        if isinstance(data, str):
            data = [data]
        fr.events.add_event(
            'GUI.%s' % dlogid,
            {
                'descr': descr,
                'dlogid': dlogid,
                'id': ctrlid,
                'event': event,
                'dismissed': dismissed,
                'values': dlog.values,
                'data': data,
            }
        )
        if dismissed:
            del_dlog(dlogid)

    def process_error_msg(self, msg):
        descr = msg.context
        dlogid = msg.get('dlogid')
        ctrlid = msg.get('id')
        errcode = msg.get('errcode', '')
        errtext = msg.get('errtext', '')
        dlog = get_dlog(dlogid)
        if not dlog:
            return
        from mufsim.processlist import process_list
        fr = process_list.get(dlog.pid)
        if fr is None:
            return
        data = {
            'descr': descr,
            'dlogid': dlogid,
            'errcode': errcode,
            'errtext': errtext,
        }
        if ctrlid:
            data['id'] = ctrlid
        fr.events.add_event('GUI.%s' % dlogid, data)

    def process_message(self, msg):
        msgname = msg.name[len(self.name)+1:]
        if msgname == 'ctrl-value':
            self.process_value_msg(msg)
        elif msgname == 'ctrl-event':
            self.process_event_msg(msg)
        elif msgname == 'error':
            self.process_error_msg(msg)


@instr("gui_available")
class InstGuiAvailable(Instruction):
    def execute(self, fr):
        descr = fr.data_pop(int)
        mcp = netifc.descr_mcp_connection(descr)
        vers = mcp.supports_package('org-fuzzball-gui')
        vers = version2float(vers)
        fr.data_push(vers)


@instr("gui_dlog_create")
class InstGuiDlogCreate(Instruction):
    def execute(self, fr):
        fr.check_underflow(4)
        args = fr.data_pop(dict)
        title = fr.data_pop(str)
        dtype = fr.data_pop(str)
        descr = fr.data_pop(int)
        if dtype not in ['simple', 'tabbed', 'helper']:
            dtype = "simple"
        for key in args.keys():
            fr.check_type(key, [str])
        mcp = netifc.descr_mcp_connection(descr)
        dlog = McpGuiDialog(descr, fr.pid)
        msg = McpMessage(
            'org-fuzzball-gui-dlog-create',
            dlogid=dlog.dlogid,
            title=title,
            type=dtype,
        )
        msg.extend(args)
        mcp.send_message(msg)
        fr.data_push(dlog.dlogid)


@instr("gui_dlog_show")
class InstGuiDlogShow(Instruction):
    def execute(self, fr):
        dlogid = fr.data_pop(str)
        dlog = get_dlog(dlogid)
        if not dlog:
            raise MufRuntimeError("Invalid dialog ID")
        dlog.send_message('dlog-show')


@instr("gui_dlog_close")
class InstGuiDlogClose(Instruction):
    def execute(self, fr):
        dlogid = fr.data_pop(str)
        dlog = get_dlog(dlogid)
        if not dlog:
            raise MufRuntimeError("Invalid dialog ID")
        dlog.send_message('dlog-close')
        del_dlog(dlogid)


@instr("gui_ctrl_create")
class InstGuiCtrlCreate(Instruction):
    def execute(self, fr):
        fr.check_underflow(4)
        args = fr.data_pop(dict)
        ctrlid = fr.data_pop(str)
        ctype = fr.data_pop(str)
        dlogid = fr.data_pop(str)
        for key in args.keys():
            fr.check_type(key, [str])
        dlog = get_dlog(dlogid)
        args['id'] = ctrlid
        dlog.send_message('ctrl-%s' % ctype, **args)


@instr("gui_ctrl_command")
class InstGuiCtrlCommand(Instruction):
    def execute(self, fr):
        fr.check_underflow(4)
        args = fr.data_pop(dict)
        command = fr.data_pop(str)
        ctrlid = fr.data_pop(str)
        dlogid = fr.data_pop(str)
        for key in args.keys():
            fr.check_type(key, [str])
        dlog = get_dlog(dlogid)
        args['id'] = ctrlid
        args['command'] = command
        dlog.send_message('ctrl-command', **args)


@instr("gui_value_set")
class InstGuiValueSet(Instruction):
    def execute(self, fr):
        fr.check_underflow(3)
        val = fr.data_pop(str, int, float, si.DBRef, list)
        ctrlid = fr.data_pop(str)
        dlogid = fr.data_pop(str)
        if isinstance(val, list):
            for v in val:
                fr.check_type(v, [str, int, float, si.DBRef])
        dlog = get_dlog(dlogid)
        dlog.setvalue(ctrlid, val)
        dlog.send_message('ctrl-value', id=ctrlid, value=val)


@instr("gui_value_get")
class InstGuiValueGet(Instruction):
    def execute(self, fr):
        fr.check_underflow(2)
        ctrlid = fr.data_pop(str)
        dlogid = fr.data_pop(str)
        dlog = get_dlog(dlogid)
        val = dlog.getvalue(ctrlid, '')
        if isinstance(val, str):
            val = [val]
        fr.data_push(val)


@instr("gui_values_get")
class InstGuiValuesGet(Instruction):
    def execute(self, fr):
        dlogid = fr.data_pop(str)
        dlog = get_dlog(dlogid)
        fr.data_push(dlog.values)


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
