: main[ arg -- ]
    prog 1 2 program_getlines pop
    prog 0 0 program_getlines var! lines
    "Copy" newprogram var! newobj
    newobj @ compiled? pop
    newobj @ 0 0 program_getlines pop
    newobj @ lines @ program_setlines
    newobj @ compiled? pop
    newobj @ 1 compile pop
    newobj @ compiled? pop
    newobj @ uncompile
    newobj @ compiled? pop
    newobj @ 0 0 program_getlines pop
;

