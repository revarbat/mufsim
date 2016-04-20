: main
    { 3 4 5 6 7 }list var! lst
    { "a" 3 "b" 8 "c" 4 "d" 9 "e" 7 }dict var! d
    lst @ 2 array_cut pop pop
    lst @ "foo" array_cut pop pop
    d @ 2 array_cut pop pop
    d @ "c" array_cut pop pop
;
