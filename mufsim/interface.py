import time
import select
import socket
import threading

from mudclientprotocol import McpConnection

from mufsim.logger import log


welcome_banner = """\
 __  __            __    _____   _
|  \/  |          / _|  / ____| (_)
| \  / |  _   _  | |_  | (___    _   _ __ ___
| |\/| | | | | | |  _|  \___ \  | | | '_ ` _ \ 
| |  | | | |_| | | |    ____) | | | | | | | | |
|_|  |_|  \__,_| |_|   |_____/  |_| |_| |_| |_|

The Muf Debugger/Editor/Simulator
"""


class Connection(object):
    def __init__(self, sock, host):
        self.MAXBUF = 16384
        self.socket = sock
        self.descr = sock.fileno()
        self.mcp_conn = McpConnection(self._notify_raw, True)
        self.user = None
        self.remote_host = host
        self.remote_user = ""
        self.connect_time = time.time()
        self.last_time = time.time()
        self.outbuf = bytearray()
        self.inbuf = bytearray()
        self.lock = threading.RLock()
        for line in welcome_banner.split('\n'):
            self._notify_raw(line)

    def read_available(self):
        with self.lock:
            self.inbuf += self.socket.recv(2048)
            self.last_time = time.time()

    def write_available(self):
        with self.lock:
            sent = self.socket.send(self.outbuf)
            self.outbuf = self.outbuf[sent:]

    def close_connection(self):
        with self.lock:
            self.socket.shutdown(socket.SHUT_WR)
            self.socket.close()
        log("DISCONNECTED DESCR %d" % self.descr)

    def _notify_raw(self, mesg):
        with self.lock:
            mesg += '\r\n'
            bmesg = mesg.encode(encoding='utf-8', errors='ignore')
            self.outbuf += bmesg
            while len(self.outbuf) > self.MAXBUF:
                self.outbuf = self.outbuf.split(b'\n', 1)[1]

    def get_line(self):
        with self.lock:
            if b'\n' in self.inbuf:
                line, self.inbuf = self.inbuf.split(b'\n', 1)
                line = line.decode(encoding='utf-8', errors='ignore')
                return line.strip('\r')
            return None

    def notify(self, mesg):
        self.mcp_conn.write_inband(mesg)

    def get_remote_host(self):
        with self.lock:
            return self.remote_host

    def get_remote_user(self):
        with self.lock:
            return self.remote_user

    def is_secure(self):
        with self.lock:
            return False

    def setuser(self, user):
        with self.lock:
            self.user = user
        log("LOGIN DESCR %d to #%d" % (self.descr, self.user))

    def buffer_free_space(self):
        with self.lock:
            return self.MAXBUF - len(self.outbuf)

    def time_connected(self):
        with self.lock:
            return time.time() - self.connect_time

    def idle_time(self):
        with self.lock:
            return time.time() - self.last_time

    def flush(self):
        self.write_available()

    def get_mcp_connection(self):
        with self.lock:
            return self.mcp_conn


class Server(object):
    def __init__(self, host='localhost', port=8888):
        self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serversocket.bind((host, port))
        self.serversocket.listen(5)
        self.descriptors = {}
        self.user_descriptors = {}
        self.lock = threading.RLock()

    def _accept_connection(self):
        (sock, addr) = self.serversocket.accept()
        sock.setblocking(False)
        con = Connection(sock, addr[0])
        self.descriptors[con.descr] = con
        log("ACCEPTED CONNECTION ON DESCR %d FROM %s" % (con.descr, addr))

    def _reader_descrs(self):
        return [descr for descr in self.descriptors]

    def _writer_descrs(self):
        return [
            descr
            for descr, con in self.descriptors.items()
            if con.outbuf
        ]

    def get_descriptors(self):
        with self.lock:
            return sorted(list(self.descriptors.keys()))

    def notify_all(self, mesg):
        with self.lock:
            for descr in self.get_descriptors():
                self.descr_notify(descr, mesg)

    def disconnect_all(self):
        with self.lock:
            for descr in self.get_descriptors():
                self.descr_disconnect(descr)

    def descr_from_con(self, con):
        with self.lock:
            descrs = self.get_descriptors()
            if con < 1 or con > len(descrs):
                return -1
            return descrs[con - 1]

    def descr_con(self, descr):
        with self.lock:
            if descr not in self.descriptors:
                return -1
            return self.get_descriptors().index(descr)

    def descr_notify(self, descr, mesg):
        with self.lock:
            con = self.descriptors.get(descr)
            if con:
                con.notify(mesg)

    def descr_set_user(self, descr, user):
        with self.lock:
            self.user_descriptors.setdefault(user, [])
            self.user_descriptors[user].append(descr)
            con = self.descriptors[descr]
            return con.setuser(user)

    def descr_secure(self, descr):
        with self.lock:
            con = self.descriptors.get(descr)
            if con:
                return con.is_secure()
            return 0

    def is_descr_online(self, descr):
        with self.lock:
            con = self.descriptors.get(descr)
            if con:
                return bool(con)
            return False

    def descr_bufsize(self, descr):
        with self.lock:
            con = self.descriptors.get(descr)
            if con:
                return con.buffer_free_space()
            return 0

    def descr_time(self, descr):
        with self.lock:
            con = self.descriptors.get(descr)
            if con:
                return con.time_connected()
            return -1

    def descr_idle(self, descr):
        with self.lock:
            con = self.descriptors.get(descr)
            if con:
                return con.idle_time()
            return -1

    def descr_host(self, descr):
        with self.lock:
            con = self.descriptors.get(descr)
            if con:
                return con.get_remote_host()
            return ""

    def descr_user(self, descr):
        with self.lock:
            con = self.descriptors.get(descr)
            if con:
                return con.get_remote_user()
            return ""

    def descr_dbref(self, descr):
        with self.lock:
            con = self.descriptors.get(descr)
            if con:
                return con.user
            return -1

    def descr_read_line(self, descr):
        with self.lock:
            con = self.descriptors.get(descr)
            if con:
                return con.get_line()
            return None

    def descr_flush(self, descr):
        with self.lock:
            con = self.descriptors.get(descr)
            if con:
                con.flush()

    def flush_all_descrs(self):
        with self.lock:
            for descr in self.descriptors:
                self.descr_flush(descr)

    def descr_mcp_connection(self, descr):
        with self.lock:
            con = self.descriptors.get(descr)
            if con:
                return con.get_mcp_connection()
            return None

    def user_descrs(self, who):
        with self.lock:
            if who not in self.user_descriptors:
                return []
            return self.user_descriptors[who]

    def user_cons(self, who):
        with self.lock:
            descrs = self.get_descriptors()
            return [
                i + 1
                for i, d in enumerate(descrs)
                if self.descriptors[d].user == who
            ]

    def is_user_online(self, who):
        with self.lock:
            return who in self.user_descriptors

    def get_users_online(self):
        with self.lock:
            return list(self.user_descriptors.keys())

    def descr_disconnect(self, descr):
        with self.lock:
            con = self.descriptors.get(descr)
            if not con:
                return
            con.close_connection()
            if con.user in self.user_descriptors:
                self.user_descriptors[con.user].remove(descr)
            del self.descriptors[descr]

    def poll(self, timeout=10):
        with self.lock:
            writers = self._writer_descrs()
            readers = self._reader_descrs()
            sockfd = self.serversocket.fileno()
            readers.append(sockfd)
        can_read, can_write, in_error = select.select(
            readers, writers, readers, timeout
        )
        with self.lock:
            if sockfd in can_read:
                self._accept_connection()
                can_read.remove(sockfd)
            for descr in can_read:
                con = self.descriptors[descr]
                con.read_available()
            for descr in can_write:
                con = self.descriptors[descr]
                con.write_available()
            for descr in in_error:
                self.descr_disconnect(descr)


network_interface = Server()


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
