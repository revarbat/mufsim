from mudclientprotocol import (
    McpMessage, McpPackage,
)

from mufsim.errors import MufRuntimeError
from mufsim.insts.base import Instruction, instr
from mufsim.interface import network_interface as netifc
import mufsim.stackitems as si


mcp_packages = {}
mcp_pkg_program = {}


def float2version(f):
    major = int(f)
    minor = int((f-major)*1000.0+0.5)
    return "%d.%d" % (major, minor)


def version2float(vers):
    major, minor = vers.split('.', 1)
    try:
        major = int(major)
        minor = int(minor)
    except ValueError:
        major = 0
        minor = 0
    return (major + (minor / 1000.0))


class McpMufPackage(McpPackage):
    def __init__(self, pkgname, minver, maxver):
        self.handler_pid = None
        self.message_handlers = {}
        McpPackage.__init__(self, pkgname, minver, maxver)

    def process_message(self, msg):
        from mufsim.processlist import process_list
        name = msg.name[len(self.name) + 1:]
        descr = msg.context
        if name in self.message_handlers:
            addr = self.message_handlers[name]
            user = netifc.descr_dbref(descr)
            newproc = process_list.new_process()
            newproc.setup(addr.prog, user, -1, "")
            newproc.call_pop()
            newproc.call_push(addr, -1)
            newproc.data_pop()
            newproc.data_push(descr)
            newproc.data_push(dict(msg))
            newproc.sleep(0)
        elif self.handler_pid:
            pid = self.handler_pid
            fr = process_list.get(pid)
            if fr is None:
                return
            fr.events.add_event(
                'MCP.%s' % msg.name,
                {
                    'descr': descr,
                    'package': self.name,
                    'message': name,
                    'args': dict(msg),
                }
            )

    def register_for_events(self, pid):
        self.handler_pid = pid

    def register_message(self, msg, addr):
        self.message_handler[msg] = addr


@instr("mcp_register")
class InstMcpRegister(Instruction):
    def execute(self, fr):
        global mcp_packages, mcp_pkg_program
        fr.check_underflow(3)
        maxver = fr.data_pop(float)
        minver = fr.data_pop(float)
        pkgname = fr.data_pop(str)
        if pkgname in mcp_packages:
            addr = fr.curr_addr()
            if mcp_pkg_program[pkgname] != addr.prog:
                raise MufRuntimeError("Package already registered!")
        minver = float2version(minver)
        maxver = float2version(maxver)
        pkg = McpMufPackage(pkgname, minver, maxver)
        mcp_packages[pkgname] = pkg
        mcp_pkg_program[pkgname] = addr.prog


@instr("mcp_register_event")
class InstMcpRegisterEvent(Instruction):
    def execute(self, fr):
        global mcp_packages, mcp_pkg_program
        fr.check_underflow(3)
        maxver = fr.data_pop(float)
        minver = fr.data_pop(float)
        pkgname = fr.data_pop(str)
        if pkgname in mcp_packages:
            addr = fr.curr_addr()
            if mcp_pkg_program[pkgname] != addr.prog:
                raise MufRuntimeError("Package already registered!")
        minver = float2version(minver)
        maxver = float2version(maxver)
        pkg = McpMufPackage(pkgname, minver, maxver)
        pkg.register_for_events(self.pid)
        mcp_packages[pkgname] = pkg
        mcp_pkg_program[pkgname] = addr.prog


@instr("mcp_bind")
class InstMcpBind(Instruction):
    def execute(self, fr):
        global mcp_packages, mcp_pkg_program
        fr.check_underflow(3)
        targaddr = fr.data_pop(si.Address)
        msgname = fr.data_pop(str)
        pkgname = fr.data_pop(str)
        addr = fr.curr_addr()
        if mcp_pkg_program[pkgname] != addr.prog:
            raise MufRuntimeError("MCP package bound to another program.")
        pkg = mcp_packages[pkgname]
        pkg.register_message(msgname, targaddr)


@instr("mcp_send")
class InstMcpSend(Instruction):
    def execute(self, fr):
        global mcp_pkg_program
        fr.check_underflow(4)
        args = fr.data_pop(dict)
        msgname = fr.data_pop(str)
        pkgname = fr.data_pop(str)
        descr = fr.data_pop(int)
        mcp = netifc.descr_mcp_connection(descr)
        ver = mcp.supports_package(pkgname)
        if ver is None:
            raise MufRuntimeError("MCP package not registered.")
        addr = fr.curr_addr()
        if mcp_pkg_program[pkgname] != addr.prog:
            raise MufRuntimeError("MCP package bound to another program.")
        msg_full_name = pkgname
        if msgname:
            msg_full_name += '-' + msgname
        msg = McpMessage(msg_full_name)
        msg.extend(args)
        mcp.send_message(msg)


@instr("mcp_supports")
class InstMcpSupports(Instruction):
    def execute(self, fr):
        pkgname = fr.data_pop(str)
        descr = fr.data_pop(int)
        mcp = netifc.descr_mcp_connection(descr)
        ver = mcp.supports_package(pkgname)
        if ver is None:
            fr.data_push(0.0)
        else:
            fr.data_push(version2float(ver))


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
