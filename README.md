# MufSim
An offline command-line simulator and debugger for the MUF language.

This is NOT a perfect simulator of a full MUCK.
This does NOT accurately simulate all permissions and behaviours.
It IS, however, a useful way to debug and test programs that don't
need some of the more unusual primitives.


## Usage
Usage: `mufsim [-h] [-m] [-u] [-r] [-t] [-d] [-c COMMAND] infile`

Positional argument   | What it is.
----------------------|-----------------------------------------------
infile                | Input MUF sourcecode filename.

Optional argument        | What it does.
-------------------------|-----------------------------------------------
-h, --help               | Show help message and exit.
-m, --muv                | Use muv to compile from MUV sources.
-u, --uncompile          | Show compiled MUF tokens.
-r, --run                | Run compiled MUF tokens.
-t, --trace              | Show stacktrace for each instrution.
-d, --debug              | Run MUF program in interactive debugger.
-c STR, --command STR    | Specify string to push onto the stack for run.
-e TXT, --textentry TXT  | Text line to feed to READs. (multiple allowed)
-f FILE, --textfile FILE | File of text lines to feed to READs.


## Interactive Debugger
The interactive MUF debugger accepts the following commands:

Command               | What it does
----------------------|--------------------------------------------
where                 | Display the call stack.
stack                 | Show all data stack items.
stack DEPTH           | Show top DEPTH data stack items.
list                  | List next few source code lines.
list LINE             | List source code line.
list LINE,LINE        | List source code between LINEs.
list FUNC             | List source code at beginning of FUNC.
break LINE            | Set breakpoint at line.
break FUNC            | Set breakpoint at func.
delete BREAKNUM       | Delete a breakpoint.
show breakpoints      | Show current breakpoints.
show functions        | List all declared functions.
show globals          | Show all global variables.
show vars             | Show all current function variables.
step                  | Step one line, going into calls.
step COUNT            | Step COUNT lines, going into calls.
next                  | Step one line, skipping over calls.
next COUNT            | Step COUNT lines, skipping over calls.
finish                | Finish the current function.
cont                  | Continue until next breakpoint.
pop                   | Pop top data stack item.
dup                   | Duplicate top data stack item.
swap                  | Swap top two data stack items.
rot                   | Rot top three data stack items.
push VALUE            | Push VALUE onto top of data stack.
print VARIABLE        | Print the value in the given variable.
trace                 | Turn on tracing of each instr.
notrace               | Turn off tracing if each instr.
run COMMANDARG        | Re-run program, with COMMANDARG.


## The Simulated MUCK Database
A small database is simulated to be able to support various property and
database related primitives.  This database is as follows:

    Room: Global Environment Room(#0R)
        Owner: Wizard(#1PWM3)
        Properties:
            _defs/.tell: "me @ swap notify"
            _reg/cmd/test: #4

    Player: Wizard(#1PWM3)
        Location: Global Environment Room(#0R)
        Home: Global Environment Room(#0R)
        Descriptor: 3 (First online.)
        Properties:
            sex: "male"

    Room: Main Room(#2R)
        Owner: Wizard(#1PWM3)

    Exit: test(#3E)
        Owner: Wizard(#1PWM3)
        Location: Main Room(#2R)
        Linked to: cmd-test(#4FM3)

    Program: cmd-test(#4FM3)
        Owner: Wizard(#1PWM3)
        Location: Wizard(#1PWM3)
        Registered: $cmd/test

    Player: John_Doe(#5PM3)
        Location: Main Room(#2R)
        Home: Main Room(#2R)
        Descriptor: 11 (Second online.)
        Properties:
            sex: "male"
            test#: 5
            test#/1: "This is line one."
            test#/2: "This is line two."
            test#/3: "This is line three."
            test#/4: "This is line four."
            test#/5: "This is line five."
            abc: "prop_abc"
            abc/def: "prop_def"
            abc/efg: "prop_efg"
            abc/efg/hij: "prop_hij"
            abc/efg/klm: "prop_klm"
            abc/nop/qrs: "prop_qrs"
            abc/nop/tuv: "prop_tuv"

    Player: Jane_Doe(#6PM1)
        Location: Main Room(#2R)
        Home: Main Room(#2R)
        Descriptor: 13 (Third online.)
        Properties:
            sex: "female"

    Thing: My Thing(#7)
        Location: Main Room(#2R)


