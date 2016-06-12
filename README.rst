######
MufSim
######

An offline simulator, debugger, and IDE for the MUF language, with GUI
and command-line interfaces.

This is *not* a perfect simulator of a full MUCK.  This does *not*
simulate all permissions and behaviours.  It *is*, however, a useful
way to make sure that you are manipulating the stack properly, and to
debug and test programs that don't need some of the more unusual
parts of MUF.


Installation
============

Windows
-------
Unpack the ``dist\MufSimWin64.zip`` archive and place the resulting
``MufSim.exe`` binary someplace useful.

OS X
----
Unpack the ``dist/MufSimOSX.zip`` archive and place the resulting
``MufSim.app`` application bundle in the ``/Applications`` folder.

Linux
-----
Install using PyPi::

    pip install mufsim

Installing from sources::

    python3 setup.py build install


Using the GUI Debugger
======================

Windows
-------
Run the ``MufSim.exe`` binary to launch the GUI Debugger/IDE.

OS X
----
Open the ``MufSim.app`` application bundle to launch the GUI
Debugger/IDE.

Linux
-----
Run the ``mufsimgui`` binary to launch the GUI Debugger/IDE.


Using the Command-Line Debugger
===============================

Usage
-----
::

    mufsim [-h] [-u] [-r] [-t] [-d] [-c COMMAND]
           [-e TEXTENTRY] [-f TEXTFILE] [-p REGNAME FILE]
           infile

Positional Arguments
--------------------

+-------------------------+---------------------------------------------------+
| infile                  | Name of MUF source file to use as input.          |
+-------------------------+---------------------------------------------------+


Optional Arguments
------------------

+----------------------------+------------------------------------------------+
| -h, --help                 | Show help message and exit.                    |
+----------------------------+------------------------------------------------+
| -u, --uncompile            | Show compiled MUF tokens.                      |
+----------------------------+------------------------------------------------+
| -r, --run                  | Run compiled MUF program.                      |
+----------------------------+------------------------------------------------+
| -t, --trace                | Show stacktrace for each instruction.          |
+----------------------------+------------------------------------------------+
| -d, --debug                | Run MUF program in interactive debugger.       |
+----------------------------+------------------------------------------------+
| -c TEXT, --command TEXT    | Specify text to push onto the stack for run.   |
+----------------------------+------------------------------------------------+
| -e TEXT, --textentry TEXT  | Text line to feed to READs. (multiple allowed) |
+----------------------------+------------------------------------------------+
| -f FILE, --textfile FILE   | File of text lines to feed to READs.           |
+----------------------------+------------------------------------------------+
| -p NAME FILE,              | Create extra prog from FILE, registered as     |
| --program NAME FILE        | $NAME.                                         |
+----------------------------+------------------------------------------------+
| --timing                   | Show run execution timing.                     |
+----------------------------+------------------------------------------------+


Interactive Debugger
====================
The interactive MUF debugger (in both the command-line and GUI) accepts
the following commands:

+-----------------------+-------------------------------------------+
| where                 | Display the call stack.                   |
+-----------------------+-------------------------------------------+
| stack                 | Show all data stack items.                |
+-----------------------+-------------------------------------------+
| stack DEPTH           | Show top DEPTH data stack items.          |
+-----------------------+-------------------------------------------+
| list                  | List next few source code lines.          |
+-----------------------+-------------------------------------------+
| list LINE             | List source code line.                    |
+-----------------------+-------------------------------------------+
| list LINE,LINE        | List source code between LINEs.           |
+-----------------------+-------------------------------------------+
| list FUNC             | List source code at beginning of FUNC.    |
+-----------------------+-------------------------------------------+
| break LINE            | Set breakpoint at line.                   |
+-----------------------+-------------------------------------------+
| break FUNC            | Set breakpoint at func.                   |
+-----------------------+-------------------------------------------+
| delete BREAKNUM       | Delete a breakpoint.                      |
+-----------------------+-------------------------------------------+
| show breakpoints      | Show current breakpoints.                 |
+-----------------------+-------------------------------------------+
| show functions        | List all declared functions.              |
+-----------------------+-------------------------------------------+
| show globals          | Show all global variables.                |
+-----------------------+-------------------------------------------+
| show vars             | Show all current function variables.      |
+-----------------------+-------------------------------------------+
| step                  | Step one line, going into calls.          |
+-----------------------+-------------------------------------------+
| step COUNT            | Step COUNT lines, going into calls.       |
+-----------------------+-------------------------------------------+
| next                  | Step one line, skipping over calls.       |
+-----------------------+-------------------------------------------+
| next COUNT            | Step COUNT lines, skipping over calls.    |
+-----------------------+-------------------------------------------+
| finish                | Finish the current function.              |
+-----------------------+-------------------------------------------+
| cont                  | Continue until next breakpoint.           |
+-----------------------+-------------------------------------------+
| pop                   | Pop top data stack item.                  |
+-----------------------+-------------------------------------------+
| dup                   | Duplicate top data stack item.            |
+-----------------------+-------------------------------------------+
| swap                  | Swap top two data stack items.            |
+-----------------------+-------------------------------------------+
| rot                   | Rot top three data stack items.           |
+-----------------------+-------------------------------------------+
| push VALUE            | Push VALUE onto top of data stack.        |
+-----------------------+-------------------------------------------+
| print VARIABLE        | Print the value in the given variable.    |
+-----------------------+-------------------------------------------+
| trace                 | Turn on tracing of each instr.            |
+-----------------------+-------------------------------------------+
| notrace               | Turn off tracing if each instr.           |
+-----------------------+-------------------------------------------+
| run COMMANDARG        | Re-run program, with COMMANDARG.          |
+-----------------------+-------------------------------------------+


Adding libraries
================
You can add extra library program objects, by using the ``-p`` command-
line argument, or by opening the extra library MUF files in the GUI app.
For example, if you have the following MUF files:

lib-foo.muf
-----------
::

    $version 1.000
    $lib-version 1.000
    : foo[ s -- ]
        me @ s @ "foo" strcat notify
    ;
    public foo
    $libdef foo

cmd-test.muf
------------
::

    $include $lib/foo
    : main[ arg -- ]
        "Blah" foo
    ;

You can run them in the command-line debugger like this::

    mufsim -r -p lib/foo lib-foo.muf cmd-test.muf


External Client Connections
===========================
You can connect and log into a player object from an external client, to
test things like MCP and MCPGUI programs. To do so, (assuming you're on
the same machine you're running MufSim on) simply connect to ``localhost``,
port ``8888``, and connect to the test user ``John_Doe`` with the password
``password``.  Or::

    telnet localhost 8888
    connect John_Doe password

There are a few simple building and chat MUCK commands like ``@dig``,
``@link``, ``say``, ``pose``, etc.  You can also interact with MUF
programs doing READs or using MCP.


The Simulated MUCK Database
===========================
A small database is simulated to be able to support various property and
database related primitives.  This database is as follows::

    Room: Global Environment Room(#0R)
        Owner: Wizard(#1PWM3)
        Properties:
            _defs/.tell: "me @ swap notify"

    Player: Wizard(#1PWM3)
        Location: Global Environment Room(#0R)
        Home: Global Environment Room(#0R)
        Descriptor: 3 (First online.)
        Password: potrzebie
        Properties:
            sex: "male"

    Room: Test Chamber #2(#2R)
        Owner: Wizard(#1PWM3)
        Registered: $mainroom
        Properties:
            _/de:<Description>

    Exit: test(#3E)
        Owner: Wizard(#1PWM3)
        Location: Test Chamber #2(#2R)
        Linked to: cmd-test(#4FM3)

    Program: cmd-test(#4FM3)
        Owner: Wizard(#1PWM3)
        Location: Wizard(#1PWM3)
        Registered: $cmd/test
        Note: The first program file is loaded into this program object.

    Player: John_Doe(#5PM3)
        Location: Test Chamber #2(#2R)
        Home: Test Chamber #2(#2R)
        Password: password
        Properties:
            _/de:<Description>
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
        Location: Test Chamber #2(#2R)
        Home: Test Chamber #2(#2R)
        Password: password
        Properties:
            _/de:<Description>
            sex: "female"

    Thing: Test Cube(#7)
        Location: Test Chamber #2(#2R)
        Properties:
            _/de:<Description>

As MUF programs are loaded into the GUI debugger/IDE, new programs will be
created for them.  The same applies for extra programs loaded via ``-p``
in the command-line debugger.  If you really need to, you can connect to a
one of the players in the DB using an external cnnection, and you can use
many of the standard MUCK building commands like ``@dig``, ``@action``,
``@pcreate``, ``@link`` or similar.


