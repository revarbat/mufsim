MAX_LOG_LINES = 10000
logged_lines = []
log_is_updated = False


def log_updated():
    global log_is_updated
    return log_is_updated


def get_log():
    global logged_lines
    global log_is_updated
    log_is_updated = False
    return logged_lines


def clear_log():
    global logged_lines
    global log_is_updated
    log_is_updated = False
    logged_lines = []


def log(msg):
    global logged_lines
    global log_is_updated
    if len(logged_lines) >= MAX_LOG_LINES:
        logged_lines.pop(0)
    log_is_updated = True
    logged_lines.append(msg)

# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
