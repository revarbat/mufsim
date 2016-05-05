import mufsim.stackitems as si
import mufsim.utils as util


sysparms_list = []
sysparms = {}


class SysParm(object):
    def __init__(self, typ, group, name, rlev, wlev, label, mod, dflt):
        self.valtype = typ
        self.name = name
        self.group = group
        self.rlev = rlev
        self.wlev = wlev
        self.label = label
        self.module = mod
        self.value = dflt
        sysparms[name] = self
        sysparms_list.append(self)


def get_sysparm_info(name):
    if name not in sysparms:
        return None
    parm = sysparms[name]
    out = {
        "name": name,
        "group": parm.group,
        "type": parm.valtype,
        "mlev": parm.rlev,
        "value": parm.value,
    }
    if parm.valtype == "dbref":
        out["objtype"] = "any"
    return out


def get_sysparm_names(pat):
    return [
        parm.name
        for parm in sysparms_list
        if util.smatch(pat, parm.name)
    ]


def get_sysparm_type(name):
    if name not in sysparms:
        return None
    return sysparms[name].valtype


def get_sysparm_value(name):
    if name not in sysparms:
        return None
    return sysparms[name].value


def get_sysparm_label(name):
    if name not in sysparms:
        return None
    return sysparms[name].label


def set_sysparm_value(name, value):
    if name not in sysparms:
        return False
    sysparms[name].value = value


SysParm("string", "Commands", "autolook_cmd", 0, 4, "Room entry look command", "", 'look')
SysParm("string", "Currency", "cpennies", 0, 4, "Currency name, capitalized, plural", "", 'Pennies')
SysParm("string", "Currency", "cpenny", 0, 4, "Currency name, capitalized", "", 'Penny')
SysParm("string", "Currency", "pennies", 0, 4, "Currency name, plural", "", 'pennies')
SysParm("string", "Currency", "penny", 0, 4, "Currency name", "", 'penny')
SysParm("string", "DB Dumps", "dumpdone_mesg", 0, 4, "Database dump finished message", "", '## Save complete. ##')
SysParm("string", "DB Dumps", "dumping_mesg", 0, 4, "Database dump started message", "", '## Pausing to save database. This may take a while. ##')
SysParm("string", "DB Dumps", "dumpwarn_mesg", 0, 4, "Database dump warning message", "", '## Game will pause to save the database in a few minutes. ##')
SysParm("string", "Idle Boot", "idle_boot_mesg", 0, 4, "Boot message given to users idling out", "", 'Autodisconnecting for inactivity.')
SysParm("string", "Misc", "huh_mesg", 0, 4, "Unrecognized command warning", "", 'Huh?  (Type "help" for help.)')
SysParm("string", "Misc", "leave_mesg", 0, 4, "Logoff message for QUIT", "", 'Come back later!')
SysParm("string", "Misc", "muckname", 0, 4, "Name of the MUCK", "", 'MufSim')
SysParm("string", "Player Max", "playermax_bootmesg", 0, 4, "Max. players connection error message", "", "Sorry, but there are too many players online.  Please try reconnecting in a few minutes.")
SysParm("string", "Player Max", "playermax_warnmesg", 0, 4, "Max. players connection login warning", "", "You likely won't be able to connect right now, since too many players are online.")
SysParm("string", "Properties", "gender_prop", 0, 4, "Property name used for pronoun substitutions", "", "sex")
SysParm("string", "Registration", "register_mesg", 0, 4, "Login registration denied message", "", "Sorry, you can get a character by e-mailing XXXX@machine.net.address with a charname and password.")
SysParm("string", "SSL", "ssl_cert_file", 5, 5, "Path to SSL certificate .pem", "SSL", "data/server.pem")
SysParm("string", "SSL", "ssl_key_file", 5, 5, "Path to SSL private key .pem", "SSL", "data/server.pem")
SysParm("string", "SSL", "ssl_keyfile_passwd", 5, 5, "Password for SSL private key file", "SSL", "")
SysParm(
    "string", "SSL", "ssl_cipher_preference_list", 5, 5,
    "Allowed OpenSSL cipher list", "SSL",
    ":".join([
        "ECDHE-RSA-AES128-GCM-SHA256",
        "ECDHE-ECDSA-AES128-GCM-SHA256",
        "ECDHE-RSA-AES256-GCM-SHA384",
        "ECDHE-ECDSA-AES256-GCM-SHA384",
        "DHE-RSA-AES128-GCM-SHA256",
        "DHE-DSS-AES128-GCM-SHA256",
        "kEDH+AESGCM",
        "ECDHE-RSA-AES128-SHA256",
        "ECDHE-ECDSA-AES128-SHA256",
        "ECDHE-RSA-AES128-SHA",
        "ECDHE-ECDSA-AES128-SHA",
        "ECDHE-RSA-AES256-SHA384",
        "ECDHE-ECDSA-AES256-SHA384",
        "ECDHE-RSA-AES256-SHA",
        "ECDHE-ECDSA-AES256-SHA",
        "DHE-RSA-AES128-SHA256",
        "DHE-RSA-AES128-SHA",
        "DHE-DSS-AES128-SHA256",
        "DHE-RSA-AES256-SHA256",
        "DHE-DSS-AES256-SHA",
        "DHE-RSA-AES256-SHA",
        "AES128-GCM-SHA256",
        "AES256-GCM-SHA384",
        "AES128-SHA256",
        "AES256-SHA256",
        "AES128-SHA",
        "AES256-SHA",
        "AES",
        "CAMELLIA",
        "DES-CBC3-SHA",
        "!aNULL",
        "!eNULL",
        "!EXPORT",
        "!DES",
        "!RC4",
        "!MD5",
        "!PSK",
        "!aECDH",
        "!EDH-DSS-DES-CBC3-SHA",
        "!EDH-RSA-DES-CBC3-SHA",
        "!KRB5-DES-CBC3-SHA",
    ])
)
SysParm("string", "SSL", "ssl_min_protocol_version", 5, 5, "Min. allowed SSL protocol version for clients", "SSL", "None")
SysParm("string", "Database", "pcreate_flags", 0, 4, "Initial flags for newly created players", "", "B")
SysParm("string", "Database", "reserved_names", 0, 4, "String-match list of reserved names", "", "")
SysParm("string", "Database", "reserved_player_names", 0, 4, "String-match list of reserved player names", "", "")

SysParm("timespan", "Database", "aging_time", 0, 4, "When to considered an object old and unused", "", 90*86400)
SysParm("timespan", "DB Dumps", "dump_interval", 0, 4, "Interval between dumps", "", 4*3600)
SysParm("timespan", "DB Dumps", "dump_warntime", 0, 4, "Interval between warning and dump", "", 2*60)
SysParm("timespan", "Idle Boot", "idle_ping_time", 0, 4, "Server side keepalive time in seconds", "", 55)
SysParm("timespan", "Idle Boot", "maxidle", 0, 4, "Maximum idle time before booting", "", 2*3600)
SysParm("timespan", "Tuning", "clean_interval", 0, 4, "Interval between memory/object cleanups", "", 15*3600)

SysParm("integer", "Costs", "exit_cost", 0, 4, "Cost to create an exit", "", 1)
SysParm("integer", "Costs", "link_cost", 0, 4, "Cost to link an exit", "", 1)
SysParm("integer", "Costs", "lookup_cost", 0, 4, "Cost to lookup a player name", "", 0)
SysParm("integer", "Costs", "max_object_endowment", 0, 4, "Max. value of an object", "", 100)
SysParm("integer", "Costs", "object_cost", 0, 4, "Cost to create an object", "", 10)
SysParm("integer", "Costs", "room_cost", 0, 4, "Cost to create a room", "", 10)
SysParm("integer", "Currency", "max_pennies", 0, 4, "Max. pennies a player can own", "", 10000)
SysParm("integer", "Currency", "penny_rate", 0, 4, "Avg. moves between finding currency", "", 8)
SysParm("integer", "Currency", "start_pennies", 0, 4, "Player starting currency count", "", 50)
SysParm("integer", "Killing", "kill_base_cost", 0, 4, "Cost to guarantee kill", "", 100)
SysParm("integer", "Killing", "kill_bonus", 0, 4, "Bonus given to a killed player", "", 50)
SysParm("integer", "Killing", "kill_min_cost", 0, 4, "Min. cost to do a kill", "", 10)
SysParm("integer", "Listeners", "listen_mlev", 0, 4, "Mucker Level required for Listener programs", "", 3)
SysParm("integer", "Logging", "cmd_log_threshold_msec", 0, 4, "Log commands that take longer than X millisecs", "", 1000)
SysParm("integer", "Misc", "max_force_level", 5, 5, "Max. number of forces processed within a command", "", 1)
SysParm("integer", "MPI", "mpi_max_commands", 0, 4, "Max. number of uninterruptable MPI commands", "", 2048)
SysParm("integer", "MUF", "addpennies_muf_mlev", 0, 4, "Mucker Level required to create/destroy pennies", "", 2)
SysParm("integer", "MUF", "instr_slice", 0, 4, "Max. uninterrupted instructions per timeslice", "", 2000)
SysParm("integer", "MUF", "max_instr_count", 0, 4, "Max. MUF instruction run length for ML1", "", 20000)
SysParm("integer", "MUF", "max_ml4_preempt_count", 0, 4, "Max. MUF preempt instruction run length for ML4, (0 = no limit)", "", 0)
SysParm("integer", "MUF", "max_plyr_processes", 0, 4, "Concurrent processes allowed per player", "", 32)
SysParm("integer", "MUF", "max_process_limit", 0, 4, "Total concurrent processes allowed on system", "", 400)
SysParm("integer", "MUF", "mcp_muf_mlev", 0, 4, "Mucker Level required to use MCP", "MCP", 3)
SysParm("integer", "MUF", "movepennies_muf_mlev", 0, 4, "Mucker Level required to move pennies non-destructively", "", 2)
SysParm("integer", "MUF", "pennies_muf_mlev", 0, 4, "Mucker Level required to read the value of pennies, settings above 1 disable {money}", "", 1)
SysParm("integer", "MUF", "process_timer_limit", 0, 4, "Max. timers per process", "", 4)
SysParm("integer", "MUF", "userlog_mlev", 0, 4, "Mucker Level required to write to userlog", "", 3)
SysParm("integer", "Player Max", "playermax_limit", 0, 4, "Max. player connections allowed", "", 56)
SysParm("integer", "Spam Limits", "command_burst_size", 0, 4, "Max. commands per burst before limiter engages", "", 500)
SysParm("integer", "Spam Limits", "command_time_msec", 0, 4, "Millisecs per spam limiter time period", "", 1000)
SysParm("integer", "Spam Limits", "commands_per_time", 0, 4, "Commands allowed per time period during limit", "", 2)
SysParm("integer", "Spam Limits", "max_output", 0, 4, "Max. output buffer size", "", 131071)
SysParm("integer", "Tuning", "free_frames_pool", 0, 4, "Size of allocated MUF process frame pool", "", 8)
SysParm("integer", "Tuning", "max_loaded_objs", 0, 4, "Max. percent of proploaded database objects", "DISKBASE", 5)
SysParm("integer", "Tuning", "pause_min", 0, 4, "Min. millisecs between MUF input/output timeslices", "", 0)

SysParm("dbref", "Database", "default_room_parent", 0, 4, "Place to parent new rooms to", "", si.DBRef(0))
SysParm("dbref", "Database", "lost_and_found", 0, 4, "Place for things without a home", "", si.DBRef(0))
SysParm("dbref", "Database", "player_start", 0, 4, "Home where new players start", "", si.DBRef(0))
SysParm("dbref", "Database", "toad_default_recipient", 0, 4, "Default owner for @toaded player's things", "", si.DBRef(1))

SysParm("boolean", "Charset", "7bit_thing_names", 4, 4, "Limit thing names to 7-bit characters", "", 1)
SysParm("boolean", "Charset", "7bit_other_names", 4, 4, "Limit exit/room/muf names to 7-bit characters", "", 0)
SysParm("boolean", "Commands", "enable_home", 4, 4, "Enable 'home' command", "", 1)
SysParm("boolean", "Commands", "enable_match_yield", 4, 4, "Enable yield/overt flags on rooms and things", "", 0)
SysParm("boolean", "Commands", "enable_prefix", 4, 4, "Enable prefix actions", "", 0)
SysParm("boolean", "Commands", "recognize_null_command", 4, 4, "Recognize null command", "", 0)
SysParm("boolean", "Commands", "verbose_clone", 4, 4, "Show more information when using @clone command", "", 0)
SysParm("boolean", "Dark", "dark_sleepers", 0, 4, "Make sleeping players dark", "", 0)
SysParm("boolean", "Dark", "exit_darking", 0, 4, "Allow players to set exits dark", "", 1)
SysParm("boolean", "Dark", "thing_darking", 0, 4, "Allow players to set things dark", "", 1)
SysParm("boolean", "Dark", "who_hides_dark", 4, 4, "Hide dark players from WHO list", "", 1)
SysParm("boolean", "Database", "compatible_priorities", 0, 4, "Use legacy exit priority levels on things", "", 1)
SysParm("boolean", "Database", "realms_control", 0, 4, "Enable support for realm wizzes", "", 0)
SysParm("boolean", "DB Dumps", "diskbase_propvals", 0, 4, "Enable property value diskbasing (req. restart)", "DISKBASE", 1)
SysParm("boolean", "DB Dumps", "dbdump_warning", 0, 4, "Enable warnings for upcoming database dumps", "", 1)
SysParm("boolean", "DB Dumps", "dumpdone_warning", 0, 4, "Notify when database dump complete", "", 1)
SysParm("boolean", "Encryption", "starttls_allow", 3, 4, "Enable TELNET STARTTLS encryption on plaintext port", "", 0)
SysParm("boolean", "Idle Boot", "idleboot", 0, 4, "Enable booting of idle players", "", 1)
SysParm("boolean", "Idle Boot", "idle_ping_enable", 0, 4, "Enable server side keepalive pings", "", 1)
SysParm("boolean", "Killing", "restrict_kill", 0, 4, "Restrict kill command to players set Kill_OK", "", 1)
SysParm("boolean", "Listeners", "allow_listeners", 0, 4, "Allow programs to listen to player output", "", 1)
SysParm("boolean", "Listeners", "allow_listeners_env", 0, 4, "Allow listeners down environment", "", 1)
SysParm("boolean", "Listeners", "allow_listeners_obj", 0, 4, "Allow objects to be listeners", "", 1)
SysParm("boolean", "Logging", "log_commands", 4, 4, "Log player commands", "", 1)
SysParm("boolean", "Logging", "log_failed_commands", 4, 4, "Log unrecognized commands", "", 0)
SysParm("boolean", "Logging", "log_interactive", 4, 4, "Log text sent to MUF", "", 1)
SysParm("boolean", "Logging", "log_programs", 4, 4, "Log programs every time they are saved", "", 1)
SysParm("boolean", "Misc", "allow_zombies", 0, 4, "Enable Zombie things to relay what they hear", "", 1)
SysParm("boolean", "Misc", "wiz_vehicles", 0, 4, "Only let Wizards set vehicle bits", "", 0)
SysParm("boolean", "Misc", "ignore_support", 3, 4, "Enable support for @ignoring players", "", 1)
SysParm("boolean", "Misc", "ignore_bidirectional", 3, 4, "Enable bidirectional @ignore", "", 1)
SysParm("boolean", "Misc", "m3_huh", 3, 4, "Enable huh? to call an exit named \"huh?\" and set M3, with full command string", "", 0)
SysParm("boolean", "Misc", "strict_god_priv", 5, 5, "Only God can touch God's objects", "GODPRIV", 1)
SysParm("boolean", "Misc", "autolink_actions", 0, 4, "Automatically link @actions to NIL", "", 0)
SysParm("boolean", "Movement", "teleport_to_player", 0, 4, "Allow using exits linked to players", "", 1)
SysParm("boolean", "Movement", "secure_teleport", 0, 4, "Restrict actions to Jump_OK or controlled rooms", "", 0)
SysParm("boolean", "Movement", "secure_thing_movement", 4, 4, "Moving things act like player", "", 0)
SysParm("boolean", "MPI", "do_mpi_parsing", 0, 4, "Parse MPI strings in messages", "", 1)
SysParm("boolean", "MPI", "lazy_mpi_istype_perm", 0, 4, "Enable looser legacy perms for MPI {istype}", "", 0)
SysParm("boolean", "MUF", "consistent_lock_source", 0, 4, "Maintain trigger as lock source in TESTLOCK", "", 1)
SysParm("boolean", "MUF", "expanded_debug_trace", 0, 4, "MUF debug trace shows array contents", "", 1)
SysParm("boolean", "MUF", "force_mlev1_name_notify", 0, 4, "MUF notify prepends username for ML1 programs", "", 1)
SysParm("boolean", "MUF", "muf_comments_strict", 0, 4, "MUF comments are strict and not recursive", "", 1)
SysParm("boolean", "MUF", "optimize_muf", 0, 4, "Enable MUF bytecode optimizer", "", 1)
SysParm("boolean", "Player Max", "playermax", 0, 4, "Limit number of concurrent players allowed", "", 0)
SysParm("boolean", "Properties", "lock_envcheck", 0, 4, "Locks check environment for properties", "", 0)
SysParm("boolean", "Properties", "look_propqueues", 0, 4, "Trigger _look/ propqueues when a player looks", "", 0)
SysParm("boolean", "Properties", "show_legacy_props", 0, 4, "Examining objects lists legacy props", "", 0)
SysParm("boolean", "Properties", "sync_legacy_props", 0, 4, "Setting properties also sets associated legacy props", "", 0)
SysParm("boolean", "Registration", "registration", 0, 4, "Require new players to register manually", "", 1)
SysParm("boolean", "SSL", "server_cipher_preference", 4, 4, "Honor server cipher preference order over client's", "SSL", 1)
SysParm("boolean", "Tuning", "periodic_program_purge", 0, 4, "Periodically free unused MUF programs", "", 1)
SysParm("boolean", "WHO", "secure_who", 0, 4, "Disallow WHO command from login screen and programs", "", 0)
SysParm("boolean", "WHO", "use_hostnames", 0, 4, "Resolve IP addresses into hostnames", "", 0)
SysParm("boolean", "WHO", "who_doing", 0, 4, "Show '_/do' property value in WHO lists", "", 1)


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
