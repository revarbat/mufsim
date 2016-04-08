# mufsim
An offline command-line simulator and debugger for the MUF language.

## usage
Usage: `mufsim [-h] [-m] [-u] [-r] [-t] [-d] [-c COMMAND] infile`

    positional arguments:
      infile                Input MUF sourcecode filename.

    optional arguments:
      -h, --help            show this help message and exit
      -m, --muv             Use muv to compile the sources.
      -u, --uncompile       Show compiled MUF tokens.
      -r, --run             Run compiled MUF tokens.
      -t, --trace           Show stacktrace for each instrution.
      -d, --debug           Show stacktrace for each instrution.
      -c COMMAND, --command COMMAND
			    Specify command to push onto the stack for run.
