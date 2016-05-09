MAX_LOG_LINES = 10000
logged_lines = []
log_cmd = None


def set_output_command(cmd):
    global log_cmd
    log_cmd = cmd


def clear_log():
    global logged_lines
    logged_lines = []


def flush_logs():
    global log_cmd
    global logged_lines
    if log_cmd:
        for msgtype, msg in logged_lines:
            log_cmd(msgtype, msg)
        clear_log()


def log(msg, msgtype="normal"):
    global logged_lines
    if len(logged_lines) >= MAX_LOG_LINES:
        logged_lines.pop(0)
    logged_lines.append((msgtype, msg))
    flush_logs()


def warnlog(msg):
    log(msg, msgtype="warning")


def errlog(msg):
    log(msg, msgtype="error")


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
