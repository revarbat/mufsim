import os
import time
from ssl import SSLError
from threading import Thread, Lock
from collections import namedtuple

try:  # Python 2
    from Tkinter import *  # noqa
    from tkMessageBox import showerror, askyesno
    from ScrolledText import ScrolledText
    from urlparse import urlparse, quote_plus
except ImportError:  # Python 3
    from tkinter import *  # noqa
    from tkinter.messagebox import showerror, askyesno
    from tkinter.scrolledtext import ScrolledText
    from urllib.parse import urlparse, quote_plus

from belfrywidgets import (
    Wizard, ScrolledListbox,
    ProgressBar, DETERMINATE, INDETERMINATE
)

import appdirs
import ssltelnet
from belfrywidgets import ToolTip


global previous_progname
previous_progname = ''


UserInfo = namedtuple('UserInfo', ['user', 'password'])


class ServerInfo(object):
    def __init__(
            self, uri=None,
            name=None, host=None,
            port=8888, use_ssl=False
            ):
        username = None
        password = None
        if uri is not None:
            info = urlparse(uri)
            host = info.hostname
            if info.port:
                port = int(info.port)
            name = info.path[1:]
            use_ssl = bool(info.scheme in ['ssl', 'tls', 'mucks'])
            username = info.username
            password = info.password
        if not host:
            raise ValueError("Host required!")
        self.name = name
        self.host = host
        self.port = port
        self.ssl = use_ssl
        self.users = []
        if username:
            self.add_user(user=username, password=password)

    def __str__(self):
        if self.name:
            return self.name
        return "%s:%s" % (self.host, self.port)

    def __repr__(self):
        return "ServerInfo(%s)" % self.get_uris()

    def get_users(self):
        return self.users

    def get_uris(self):
        out = []
        name = self.name if self.name else ''
        proto = "ssl" if self.ssl else "telnet"
        if not self.users:
            uri = '{proto}://{host}:{port}/{muck}'.format(
                proto=proto, host=self.host, port=self.port, muck=name
            )
            out.append(uri)
        for user in self.users:
            username = quote_plus(user.user, encoding='utf8', errors='ignore')
            if user.password:
                username += ":" + quote_plus(
                    user.password, encoding='utf8', errors='ignore')
            uri = '{proto}://{user}@{host}:{port}/{muck}'.format(
                proto=proto,
                host=self.host,
                port=self.port,
                muck=name,
                user=username
            )
            out.append(uri)
        return out

    def matches_host_and_port(self, host, port):
        if host.lower() != self.host.lower():
            return False
        if int(port) != int(self.port):
            return False
        return True

    def matches_uri(self, uri):
        info = urlparse(uri)
        host = info.hostname
        port = int(info.port)
        if host.lower() != self.host.lower():
            return False
        if port != int(self.port):
            return False
        return True

    def find_user(self, username):
        for user in self.users:
            if user.user == username:
                return user
        return None

    def add_user(self, user=None, password=None, uri=None):
        if uri is not None:
            info = urlparse(uri)
            user = info.username
            password = info.password
        self.del_user(user)
        self.users.append(UserInfo(user=user, password=password))
        self.users = sorted(self.users, key=lambda x: x.user.lower())

    def del_user(self, user):
        self.users = [x for x in self.users if x.user != user]


class ServerList(object):
    def __init__(self):
        self.config_dir = appdirs.user_data_dir('MufSim', 'BelfryDevWorks')
        self.config_file = os.path.join(self.config_dir, "servers.txt")
        self.servers = []
        self.load()

    def get_servers(self):
        return self.servers

    def add_server(self, server):
        self.servers.append(server)
        self.servers = sorted(self.servers, key=lambda x: str(x).lower())

    def del_server(self, num):
        del self.servers[num]

    def find_by_host_and_port(self, host, port):
        for serv in self.servers:
            if serv.matches_host_and_port(host, port):
                return serv
        return None

    def find_by_uri(self, uri):
        for serv in self.servers:
            if serv.matches_uri(uri):
                return serv
        return None

    def add_server_by_uri(self, uri):
        server = self.find_by_uri(uri)
        if server:
            server.add_user(uri=uri)
        self.servers.append(ServerInfo(uri=uri))

    def save(self):
        try:
            os.makedirs(self.config_dir)
        except os.error:
            pass
        filename = self.config_file
        try:
            with open(filename, "w") as f:
                f.write("# Servers list for uploads\n")
                for server in self.servers:
                    for uri in server.get_uris():
                        f.write("%s\n" % uri)
        except IOError as e:
            showerror(
                "Saving Favorite Servers",
                "Cannot open file '%s': %s" % (filename, e)
            )

    def load(self):
        filename = self.config_file
        try:
            with open(filename, "r") as f:
                lines = f.readlines()
            uris = [
                uri for uri in [line.strip() for line in lines]
                if uri and not uri.startswith('#')
            ]
            for uri in uris:
                self.add_server_by_uri(uri)
        except IOError:
            pass


SERV_CONNECT = "SERVCON"
WELCOME_WAIT = "WELCWAIT"
USER_LOGIN = "USERCON"
UPLOADING = "UPLOADING"
UPLOAD_FAIL = "FAIL"
UPLOAD_SUCCESS = "SUCCESS"


class UploadThread(Thread):
    def __init__(self, host, port, ssl, user, password, progname, data):
        self.host = host
        self.port = port
        self.ssl = ssl
        self.user = user
        self.password = password
        self.progname = progname
        self.data = data.split('\n')
        self.bytes_uploaded = 0
        self.total_bytes = len(data)
        self.status = ""
        self.state = ""
        self.good = True
        self.telnet = None
        self.connection_log = ''
        self.access_lock = Lock()
        super(UploadThread, self).__init__()

    def _log(self, line):
        with self.access_lock:
            self.connection_log += line + "\n"

    def get_log_text(self):
        with self.access_lock:
            out = self.connection_log
            self.connection_log = ''
            return out

    def _write_line(self, s):
        # self._log("<- %s" % s)
        return self.telnet.write(bytes(s + '\r\n', 'utf8'))

    def _consume_until(self, pats, timeout=10):
        buf_line = ''
        countdown = timeout
        comp_pats = [re.compile(pat) for pat in pats]
        while countdown:
            txt = self.telnet.read_until(b'\n', 1)
            txt = txt.decode('utf8', errors='ignore')
            buf_line += txt
            if '\n' not in buf_line:
                if not txt:
                    countdown -= 1
                    time.sleep(1)
                else:
                    countdown = timeout
                continue
            txt, buf_line = buf_line.split('\n')
            txt = txt.rstrip('\r')
            self._log(txt)
            for comp_pat in comp_pats:
                if comp_pat.search(txt):
                    return txt
        return ''

    def run(self):
        self.good = True
        self.state = SERV_CONNECT
        self.status = "Connecting to %s:%s..." % (self.host, self.port)
        try:
            self.telnet = ssltelnet.SslTelnet(
                force_ssl=self.ssl,
                telnet_tls=False,
                host=self.host,
                port=self.port,
            )
            self.state = WELCOME_WAIT
            self.status = "Waiting for Welcome Message..."
            self._consume_until([r'^\s*$'])
            self.state = USER_LOGIN
            self.status = "Connecting to user '%s'..." % self.user
            self._write_line("connect %s %s" % (self.user, self.password))
            self._write_line("@Q")
            self._write_line("score")
            line = self._consume_until(
                [
                    '^Either that player',
                    '^Sorry, but the game',
                    '^You have [0-9]+',
                    '^\*\*\*  You are currently inserting MUF program text.',
                ]
            )
            if 'Either that player' in line:
                self.good = False
                self.state = UPLOAD_FAIL
                self.status = "Incorrect playername or password."
                self.telnet.close()
                return
            if 'Sorry, but the game' in line:
                self.good = False
                self.state = UPLOAD_FAIL
                self.status = "Server unavailable.  Try again later."
                self.telnet.close()
                return
            if 'inserting MUF' in line:
                self._write_line(".")
                self._write_line("q")
                self._consume_until(['^Editor exited.'])
            self.state = UPLOADING
            self.status = "Entering editor for '%s'..." % (self.progname)
            self._write_line('@program %s' % self.progname)
            self._write_line('1 999999 d')
            self._write_line('1 i')
            txt = self._consume_until(
                [
                    '^Entering insert mode.',
                    '^Huh?',
                    "^You're no programmer!",
                    "^I don't know which one you mean!",
                    "^Only programmers are allowed to ",
                    "^Guests are not allowed to ",
                    "^Permission denied!",
                    "^No program name given.",
                    "^Sorry, this program is currently being edited ",
                ]
            )
            if not txt.startswith("Entering "):
                self.good = False
                self.state = UPLOAD_FAIL
                self.status = "Failed to enter editor: %s" % txt
                self.telnet.close()
                return
            self.bytes_uploaded = 0
            while self.data:
                self.status = "Uploading '%s'...  (%.1f%%)" % (
                    self.progname,
                    (float(self.bytes_uploaded) / self.total_bytes)
                )
                line = self.data.pop(0)
                self._write_line(line)
                self.bytes_uploaded += len(line) + 1
            self._write_line(".")
            self._write_line("c")
            self._write_line("q")
            self._consume_until(['^Editor exited.'])
            self.telnet.close()
            self.status = "Upload complete."
            self.state = UPLOAD_SUCCESS

        except EOFError as e:
            self.good = False
            self.state = UPLOAD_FAIL
            self.status = "Server unexpectedly disconnected."

        except (OSError, SSLError, ConnectionError) as e:
            self.good = False
            self.state = UPLOAD_FAIL
            errstr = re.sub(r'\[SSL.*\](.*)\([^)]*\)$', r'\1', e.strerror)
            self.status = "Could not connect to server: %s" % errstr


class UploadWizard(Wizard):
    def __init__(self, root, data):
        self.root = root
        self.data = data
        self.secure = False
        super(UploadWizard, self).__init__(
            width=450,
            height=300,
            cancelcommand=self._handle_cancel,
            finishcommand=self._handle_finish,
        )
        self.servers = ServerList()
        self.server_lbox = None
        self.upthread = None
        self.old_upload_state = None
        self.setup_gui()

    def setup_gui(self):
        self.title("Upload Wizard")
        self.protocol("WM_DELETE_WINDOW", self._handle_cancel)
        self.setup_gui_server_pane()
        self.setup_gui_user_pane()
        self.setup_gui_program_pane()
        self.setup_gui_upload_pane()

    def setup_gui_server_pane(self):
        fr = self.add_pane(
            'server', 'Select Server',
            entrycommand=self._enter_server_pane
        )
        fr.config(padx=20, pady=20)
        self.ssl_enable = IntVar()
        lbox_lbl = Label(fr, text="Select a Server to upload to:")
        self.server_lbox = ScrolledListbox(
            fr, horiz_scroll=False, width=20, highlightthickness=1)
        muck_lbl = Label(fr, text="Name")
        host_lbl = Label(fr, text="Host")
        port_lbl = Label(fr, text="Port")
        svalid = (self.register(self._serv_validate))
        pvalid = (self.register(self._port_validate), '%P')
        self.muck_entry = Entry(
            fr, width=30, validate=ALL, validatecommand=svalid)
        self.host_entry = Entry(
            fr, width=30, validate=ALL, validatecommand=svalid)
        self.port_entry = Entry(
            fr, width=10, validate=ALL, validatecommand=pvalid)
        self.port_entry.insert(END, '8888')
        self.ssl_cb = Checkbutton(
            fr, text="SSL",
            variable=self.ssl_enable,
            highlightthickness=3,
            command=self._update_server_buttons,
        )
        self.serv_del = Button(fr, text="-", width=1, command=self._del_server)
        self.serv_add = Button(fr, text="+", width=1, command=self._add_server)
        self.serv_save = Button(fr, text="Save", command=self._save_server)
        ToolTip(self.serv_del, "Delete selected Favorite Server")
        ToolTip(self.serv_add, "Enter a new Server")
        ToolTip(self.serv_save, "Save as a Favorite Server")
        self.server_lbox.bind('<<ListboxSelect>>', self._server_listbox_select)
        lbox_lbl.grid(row=0, column=0, sticky=N+W)
        self.server_lbox.grid(
            row=1, column=0, rowspan=8, padx=5, sticky=N+S+E+W)
        muck_lbl.grid(row=1, column=1, sticky=W, padx=5)
        self.muck_entry.grid(row=2, column=1, columnspan=3, sticky=E+W, padx=5)
        host_lbl.grid(row=3, column=1, sticky=W, padx=5)
        self.host_entry.grid(row=4, column=1, columnspan=3, sticky=E+W, padx=5)
        port_lbl.grid(row=5, column=1, sticky=W, padx=5)
        self.port_entry.grid(row=6, column=1, columnspan=2, sticky=E+W, padx=5)
        self.ssl_cb.grid(row=6, column=3, sticky=E, padx=5)
        self.serv_del.grid(row=8, column=1, sticky=N+W, padx=5)
        self.serv_add.grid(row=8, column=2, sticky=N+W, padx=5)
        self.serv_save.grid(row=8, column=3, sticky=N+E, padx=5)
        fr.grid_columnconfigure(2, weight=1, minsize=50)
        fr.grid_rowconfigure(7, weight=1)
        self.server_lbox.focus()
        return fr

    def setup_gui_user_pane(self):
        fr = self.add_pane(
            'user', 'Select a user',
            entrycommand=self._enter_user_pane
        )
        fr.config(padx=20, pady=20)
        lbox_lbl = Label(fr, text="Select a User to upload to:")
        self.user_lbox = ScrolledListbox(fr, horiz_scroll=False, width=20)
        user_lbl = Label(fr, text="UserName")
        pass_lbl = Label(fr, text="Password")
        uvalid = (self.register(self._user_validate))
        self.user_entry = Entry(
            fr, width=30, validate=ALL, validatecommand=uvalid)
        self.pass_entry = Entry(
            fr, width=30, show="*", validate=ALL, validatecommand=uvalid)
        self.user_del = Button(fr, text="-", width=1, command=self._del_user)
        self.user_add = Button(fr, text="+", width=1, command=self._add_user)
        self.user_save = Button(fr, text="Save", command=self._save_user)
        ToolTip(self.user_del, "Delete selected User")
        ToolTip(self.user_add, "Enter a new User")
        ToolTip(self.user_save, "Save User Info")
        self.user_lbox.bind('<<ListboxSelect>>', self._user_listbox_select)
        lbox_lbl.grid(row=0, column=0, sticky=N+W)
        self.user_lbox.grid(row=1, column=0, rowspan=8, padx=5, sticky=N+S+E+W)
        user_lbl.grid(row=1, column=1, sticky=W, padx=5)
        self.user_entry.grid(row=2, column=1, columnspan=3, sticky=E+W, padx=5)
        pass_lbl.grid(row=3, column=1, sticky=W, padx=5)
        self.pass_entry.grid(row=4, column=1, columnspan=3, sticky=E+W, padx=5)
        self.user_del.grid(row=6, column=1, sticky=N+W, padx=5)
        self.user_add.grid(row=6, column=2, sticky=N+W, padx=5)
        self.user_save.grid(row=6, column=3, sticky=N+E, padx=5)
        fr.grid_columnconfigure(2, weight=1, minsize=50)
        fr.grid_rowconfigure(5, weight=1)
        return fr

    def setup_gui_program_pane(self):
        fr = self.add_pane(
            'program', 'Program Info',
            entrycommand=self._enter_program_pane
        )
        pvalid = (self.register(self._program_validate))
        fr.config(padx=20, pady=20)
        prog_lbl = Label(fr, text="Program Name or DBRef")
        self.prog_entry = Entry(
            fr, width=30, validate=ALL, validatecommand=pvalid)
        global previous_progname
        self.prog_entry.insert(END, previous_progname)
        prog_lbl.grid(row=0, column=0, sticky=W+S)
        self.prog_entry.grid(row=1, column=0, sticky=N+E+W)
        fr.grid_columnconfigure(0, weight=1)
        fr.grid_rowconfigure(2, weight=1)
        return fr

    def setup_gui_upload_pane(self):
        fr = self.add_pane(
            'upload', 'Uploading',
            entrycommand=self._enter_upload_pane
        )
        fr.config(padx=20, pady=20)
        self.upload_lbl = Label(
            fr, text="", justify=LEFT, anchor=W, wraplength=400)
        self.progressbar = ProgressBar(
            fr, length=300,
            value=10.0, maximum=100.0,
            mode=INDETERMINATE,
        )
        self.console_log = ScrolledText(
            fr, font='TkFixedFont',
            relief=SUNKEN,
            borderwidth=2,
            background="black",
            foreground="white",
            width=1,
            height=1,
            insertontime=0,
            takefocus=0,
            cursor='arrow',
        )
        ro_binds = [
            "<Key>",
            "<<Cut>>",
            "<<Clear>>",
            "<<Paste>>",
            "<<PasteSelection>>",
            "<Double-Button-1>",
        ]
        for bind in ro_binds:
            self.console_log.bind(bind, lambda e: "break")
        self.upload_lbl.grid(row=0, column=0, sticky=W+S)
        self.progressbar.grid(row=1, column=0, sticky=N+E+W, padx=15, pady=5)
        self.console_log.grid(row=2, column=0, sticky=N+S+E+W)
        fr.grid_columnconfigure(0, weight=1)
        fr.grid_rowconfigure(2, weight=1)
        return fr

    def _enter_server_pane(self):
        self.set_finish_enabled(False)
        self.set_next_enabled(False)
        self.set_next_text()
        self.set_default_button("next")
        self.set_finish_text("Done")
        self._populate_server_listbox()
        if self.server_lbox.size() > 0:
            self.server_lbox.focus()
        else:
            self.muck_entry.focus()
        self._update_server_buttons()

    def _enter_user_pane(self):
        self.set_finish_enabled(False)
        self.set_next_enabled(False)
        self.set_next_text()
        self.set_default_button("next")
        self._populate_user_listbox()
        if self.user_lbox.size() > 0:
            self.user_lbox.focus()
        else:
            self.user_entry.focus()
        self._update_user_buttons()

    def _enter_program_pane(self):
        self.set_finish_enabled(False)
        self.set_next_enabled(False)
        self.set_next_text("Upload")
        self.set_default_button("next")
        self.prog_entry.focus()

    def _enter_upload_pane(self):
        self.set_default_button("finish")
        self.set_next_text()
        self.set_prev_enabled(False)
        self.set_finish_enabled(False)
        self._upload_start()
        global previous_progname
        previous_progname = self.prog_entry.get()

    def _populate_server_listbox(self):
        self.server_lbox.delete(0, END)
        for serv in self.servers.get_servers():
            self.server_lbox.insert(END, str(serv))

    def _update_server_listbox(self):
        sel = self.server_lbox.curselection()
        self._populate_server_listbox()
        if sel:
            self.server_lbox.selection_set(sel[0])
        self._update_server_buttons()

    def _server_listbox_select(self, event=None):
        try:
            sel = int(self.server_lbox.curselection()[0])
            servers = self.servers.get_servers()
            serv = servers[sel]
            self.muck_entry.delete(0, END)
            self.host_entry.delete(0, END)
            self.port_entry.delete(0, END)
            self.muck_entry.insert(END, serv.name)
            self.host_entry.insert(END, serv.host)
            self.port_entry.insert(END, serv.port)
            self.ssl_enable.set(serv.ssl)
            self._update_server_buttons()
        except (ValueError, IndexError):
            return

    def _update_server_buttons(self, event=None):
        add_state = 'normal'
        del_state = 'normal'
        save_state = 'normal'
        items = self.server_lbox.curselection()
        if not items:
            del_state = 'disabled'
            if not self.muck_entry.get():
                if not self.host_entry.get():
                    if self.port_entry.get() == '8888':
                        if not self.ssl_enable.get():
                            add_state = 'disabled'
        if not self.host_entry.get() or not self.port_entry.get():
            save_state = 'disabled'
        self.serv_del.config(state=del_state)
        self.serv_add.config(state=add_state)
        self.serv_save.config(state=save_state)
        self.set_next_enabled(
            bool(items or (self.host_entry.get() and self.port_entry.get()))
        )

    def _serv_validate(self):
        self.after_idle(self._update_server_buttons)
        return True

    def _port_validate(self, val):
        self.after_idle(self._update_server_buttons)
        if val == '':
            return True
        try:
            val = int(val)
            return True
        except ValueError:
            self.bell()
        return False

    def _add_server(self):
        self.server_lbox.selection_clear(0, END)
        self.muck_entry.delete(0, END)
        self.host_entry.delete(0, END)
        self.port_entry.delete(0, END)
        self.port_entry.insert(END, '8888')
        self.ssl_enable.set('0')
        self.muck_entry.focus()
        self._update_server_buttons()

    def _del_server(self):
        del_confirmed = askyesno(
            "Delete Server",
            "Are you sure you want to delete this server?",
            parent=self
        )
        if del_confirmed:
            try:
                sel = int(self.server_lbox.curselection()[0])
                self.servers.del_server(sel)
                self.servers.save()
                self._update_server_listbox()
            except (ValueError, IndexError):
                self.bell()

    def _save_server(self):
        sel = -1
        try:
            sel = int(self.server_lbox.curselection()[0])
            self.servers.del_server(sel)
            self._update_server_listbox()
        except (ValueError, IndexError):
            pass
        server = ServerInfo(
            name=self.muck_entry.get(),
            host=self.host_entry.get(),
            port=self.port_entry.get(),
            use_ssl=self.ssl_enable.get()
        )
        self.servers.add_server(server)
        self.servers.save()
        self._update_server_listbox()
        if sel >= 0:
            self.server_lbox.selection_set(sel)
        self._server_listbox_select()
        self._update_server_buttons()

    def _populate_user_listbox(self):
        host = self.host_entry.get()
        port = int(self.port_entry.get())
        serv = self.servers.find_by_host_and_port(host, port)
        self.user_lbox.delete(0, END)
        if not serv:
            return
        for user in serv.get_users():
            self.user_lbox.insert(END, user.user)

    def _update_user_listbox(self):
        sel = self.user_lbox.curselection()
        self._populate_user_listbox()
        if sel:
            self.user_lbox.selection_set(sel[0])
        self._update_user_buttons()

    def _user_listbox_select(self, event=None):
        host = self.host_entry.get()
        port = int(self.port_entry.get())
        serv = self.servers.find_by_host_and_port(host, port)
        if not serv:
            return
        try:
            sel = int(self.user_lbox.curselection()[0])
            users = serv.get_users()
            user = users[sel]
            self.user_entry.delete(0, END)
            self.pass_entry.delete(0, END)
            self.user_entry.insert(END, user.user)
            self.pass_entry.insert(END, user.password)
            self._update_server_buttons()
        except (ValueError, IndexError):
            return

    def _update_user_buttons(self, event=None):
        add_state = 'normal'
        del_state = 'normal'
        save_state = 'normal'
        host = self.host_entry.get()
        port = int(self.port_entry.get())
        serv = self.servers.find_by_host_and_port(host, port)
        if not serv:
            del_state = 'disabled'
            add_state = 'disabled'
            save_state = 'disabled'
        items = self.user_lbox.curselection()
        if not items:
            del_state = 'disabled'
            if not self.user_entry.get():
                if not self.pass_entry.get():
                    add_state = 'disabled'
        if not self.user_entry.get():
            save_state = 'disabled'
        self.user_del.config(state=del_state)
        self.user_add.config(state=add_state)
        self.user_save.config(state=save_state)
        self.set_next_enabled(
            bool(items or (self.user_entry.get() and self.pass_entry.get()))
        )

    def _user_validate(self):
        self.after_idle(self._update_user_buttons)
        return True

    def _add_user(self):
        self.user_lbox.selection_clear(0, END)
        self.user_entry.delete(0, END)
        self.pass_entry.delete(0, END)
        self._update_user_buttons()
        self.user_entry.focus()

    def _del_user(self):
        del_confirmed = askyesno(
            "Delete User",
            "Are you sure you want to delete this user?",
            parent=self
        )
        if del_confirmed:
            host = self.host_entry.get()
            port = int(self.port_entry.get())
            serv = self.servers.find_by_host_and_port(host, port)
            if not serv:
                return
            try:
                sel = int(self.server_lbox.curselection()[0])
                serv.del_user(sel)
                self.servers.save()
                self._update_user_listbox()
            except (ValueError, IndexError):
                self.bell()

    def _save_user(self):
        host = self.host_entry.get()
        port = int(self.port_entry.get())
        serv = self.servers.find_by_host_and_port(host, port)
        if not serv:
            return
        serv.add_user(
            user=self.user_entry.get(),
            password=self.pass_entry.get(),
        )
        self.servers.save()
        self._update_user_listbox()

    def _update_program_buttons(self, event=None):
        self.set_next_enabled(bool(self.prog_entry.get()))

    def _program_validate(self):
        self.after_idle(self._update_program_buttons)
        return True

    def _upload_start(self):
        force_ssl = bool(self.ssl_enable.get())
        host = self.host_entry.get()
        port = int(self.port_entry.get())
        user = self.user_entry.get()
        password = self.pass_entry.get()
        progname = self.prog_entry.get()
        self.upload_lbl.config(text="Connecting to %s:%s..." % (host, port))
        self.progressbar.start()
        self.upthread = UploadThread(
            host, port, force_ssl,
            user, password, progname,
            self.data,
        )
        self.upthread.start()
        self.old_upload_state = ''
        self._update_upload_state()

    def _update_upload_state(self):
        logtxt = self.upthread.get_log_text()
        if logtxt:
            self.console_log.insert(END, logtxt)
            self.console_log.see(END)
        state = self.upthread.state
        self.upload_lbl.config(text=self.upthread.status)
        if state in [UPLOAD_FAIL, UPLOAD_SUCCESS]:
            self.set_finish_enabled(True)
            self.set_cancel_enabled(False)
        else:
            self.after(100, self._update_upload_state)
        if state == UPLOADING:
            uploaded = self.upthread.bytes_uploaded
            total = self.upthread.total_bytes
            pcnt = float(uploaded) / total
            self.progressbar.config(value=pcnt)
        if state == self.old_upload_state:
            return
        self.old_upload_state = state
        if state == UPLOADING:
            self.progressbar.stop()
            self.progressbar.config(mode=DETERMINATE)
        elif state == UPLOAD_FAIL:
            self.progressbar.stop()
            self.progressbar.grid_forget()
        elif state == UPLOAD_SUCCESS:
            self.progressbar.stop()
            self.progressbar.config(mode=DETERMINATE)
            self.progressbar.config(value=100.0)

    def _handle_cancel(self):
        self.destroy()

    def _handle_finish(self):
        self.destroy()


if __name__ == "__main__":
    tk = Tk()
    wiz = UploadWizard(tk, """\
(Data to upload)
: main
    me @ "Hello World!" notify
;""")
    tk.wm_withdraw()
    tk.wait_window(wiz)


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
