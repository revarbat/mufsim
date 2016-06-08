import time
import heapq

import mufsim.utils as util
import mufsim.commands as cmds
from mufsim.logger import log, warnlog
from mufsim.errors import MufRuntimeError
from mufsim.process import MufProcess
from mufsim.interface import network_interface as netifc

STATE_ACTIVE = ''
STATE_PENDING = 'PENDING'
STATE_DEAD = 'DEAD'
STATE_DEBUG = 'DEBUG'
STATE_SLEEP = 'SLEEP'
STATE_READ = 'READ'
STATE_EVENT = 'EVENT'


class ProcessList(object):
    def __init__(self):
        self.max_pid = 1
        self.processes = {}
        self.current_process = None
        self.timer_queue = []
        self.pending_processes = []
        self.sleeping_processes = []
        self.waiting_processes = {}
        self.reading_processes = {}
        self.process_watch_cbs = []
        self.read_handler = None

    def __len__(self):
        return len(self.processes)

    def __getitem__(self, pid):
        return self.processes[pid]

    def get(self, pid, dflt=None):
        return self.processes.get(pid, dflt)

    def process(self, level=-1):
        self.process_sleeping()
        self.process_reads()
        self.handle_events()
        self.process_active_queue(level=level)

    def next_time(self):
        if self.pending_processes:
            return 0.0
        return min(
            self.timer_queue[0][0],
            self.sleeping_processes[0][0],
        )

    def queue_process(self, process):
        if not process:
            return
        if self.current_process == process:
            self.current_process = None
        process.wait_state = STATE_PENDING
        self.pending_processes.append(process.pid)

    def process_active_queue(self, level=-1):
        if self.current_process is not None:
            return
        if not self.pending_processes:
            return
        process = self.get(self.pending_processes.pop(0))
        self.current_process = process
        log("Switching to process PID=%d" % process.pid)
        for callback in self.process_watch_cbs:
            callback()
        process.execute_code(level=level)

    def watch_process_change(self, callback):
        self.process_watch_cbs.append(callback)

    def set_read_handler(self, callback):
        self.read_handler = callback

    def process_sleeping(self):
        now = time.time()
        while self.sleeping_processes and self.sleeping_processes[0][0] < now:
            when, pid = heapq.heappop(self.sleeping_processes)
            ofr = self.processes.get(pid)
            self.queue_process(ofr)

    def poll_network(self):
        for descr in netifc.get_descriptors():
            cmd = netifc.descr_read_line(descr)
            if cmd is None:
                continue
            user = netifc.descr_dbref(descr)
            if user not in self.reading_processes:
                cmds.process_command(self, descr, user, cmd)
                continue
            pid = self.reading_processes[user]
            ofr = self.processes.get(pid)
            if not ofr:
                continue
            ofr.text_entry.append(cmd)

    def process_reads(self):
        self.poll_network()
        for pid in list(self.reading_processes.values()):
            ofr = self.processes.get(pid)
            if not ofr:
                continue
            while True:
                if ofr.text_entry:
                    cmd = ofr.text_entry.pop(0)
                elif not netifc.user_descrs(ofr.user.value):
                    cmd = self.read_handler()
                else:
                    break
                if cmd is None or cmd == '@Q':
                    log("Aborting program.")
                    del self.reading_processes[ofr.user.value]
                    self.process_complete(ofr.pid)
                    break
                if not cmd and not ofr.read_wants_blanks:
                    warnlog("Blank line ignored.")
                    continue
                ofr.data_push(cmd)
                ofr.pc_advance(1)
                del self.reading_processes[ofr.user.value]
                self.queue_process(ofr)
                break

    def handle_events(self):
        self.trigger_timers()
        for pid in list(self.waiting_processes.keys()):
            ofr = self.processes.get(pid)
            if not ofr:
                del self.waiting_processes[pid]
                continue
            for idx, event in enumerate(list(ofr.events)):
                pats = self.waiting_processes[pid]
                matches = [util.smatch(pat, event.name) for pat in pats]
                if not pats or any(matches):
                    ofr.data_push(event.data)
                    ofr.data_push(event.name)
                    del ofr.events[idx]
                    del self.waiting_processes[pid]
                    self.queue_process(ofr)

    def trigger_timers(self):
        now = time.time()
        while self.timer_queue and self.timer_queue[0][0] < now:
            when, pid, name = heapq.heappop(self.timer_queue)
            ofr = self.processes.get(pid)
            if ofr:
                ofr.events.add_event("TIMER." + name[:32], when)

    def alloc_new_pid(self):
        attempts = 1024
        while self.max_pid in self.processes:
            self.max_pid += 1
            self.max_pid %= 1024
            attempts -= 1
            if attempts < 0:
                raise MufRuntimeError("Process list full.")
        pid = self.max_pid
        self.max_pid += 1
        return pid

    def assign_pid(self, process):
        process.pid = self.alloc_new_pid()
        self.processes[process.pid] = process
        return process.pid

    def new_process(self):
        newproc = MufProcess(self)
        newproc.wait_state = STATE_ACTIVE
        self.assign_pid(newproc)
        log("New process: pid=%d" % newproc.pid)
        if not self.current_process:
            self.current_process = newproc
            for callback in self.process_watch_cbs:
                callback()
        return newproc

    def get_pids(self):
        return list(self.processes.keys())

    def timer_add(self, secs, pid, name):
        self.timer_del(pid, name)
        when = time.time() + secs
        heapq.heappush(self.timer_queue, (when, pid, name))

    def timer_del(self, pid, name):
        for idx, timer in enumerate(self.timer_queue):
            when, tpid, tname = timer
            if (tpid, tname) == (pid, name):
                del self.timer_queue[idx]
                break

    def wait_for_events(self, pid, pats):
        ofr = self.processes.get(pid)
        if not ofr:
            return
        if ofr == self.current_process:
            self.current_process = None
        ofr.wait_state = STATE_EVENT
        self.waiting_processes[pid] = pats

    def wait_for_read(self, user, pid):
        # TODO: do something if a process is already awaiting a user's text line
        ofr = self.processes.get(pid)
        if not ofr:
            return
        if ofr == self.current_process:
            self.current_process = None
        ofr.wait_state = STATE_READ
        self.reading_processes[user] = pid

    def kill_process(self, pid):
        self.process_complete(pid)

    def watch_pid(self, watcher, pid):
        wfr = self.processes.get(watcher)
        ofr = self.processes.get(pid)
        if ofr:
            if pid not in ofr.watchers:
                ofr.watchers.append(watcher)
        elif wfr:
            wfr.events.add_event("PROC.EXIT.%d" % pid, pid)

    def process_complete(self, pid):
        ofr = self.processes.get(pid)
        if not ofr:
            return
        ofr.wait_state = STATE_DEAD
        log("Process exited: pid=%d" % ofr.pid)
        for wpid in ofr.watchers:
            wfr = self.processes.get(wpid)
            if wfr:
                wfr.events.add_event("PROC.EXIT.%d" % pid, pid)
        if ofr == self.current_process:
            self.current_process = None
        # Keep processes in proc list for inspection
        # del self.processes[pid]

    def sleep(self, secs, pid):
        ofr = self.processes.get(pid)
        if not ofr:
            return
        if ofr == self.current_process:
            self.current_process = None
        ofr.wait_state = STATE_SLEEP
        when = time.time() + secs
        heapq.heappush(self.sleeping_processes, (when, pid))

    def killall(self, prog):
        for pid in self.get_pids():
            proc = self.get(pid)
            if proc:
                if proc.uses_prog(prog):
                    self.kill_process(pid)


process_list = ProcessList()


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
