: main
    me @ getlockstr pop
    me @ "me|*jane_doe" setlockstr pop
    me @ getlockstr pop
    me @ me @ locked? pop
    #1 me @ locked? pop
    "me|*jane_doe" parselock
    dup unparselock pop
    dup prettylock pop
    #1 over testlock pop
    "jane_doe" pmatch swap testlock pop
;


