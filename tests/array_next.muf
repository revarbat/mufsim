: main
    0 array_make 0 array_next pop pop

    0 array_make_dict 0 array_next pop pop

    { 5 4 3 }list
    dup array_first
    begin
        while
        over swap array_next
    repeat
    pop pop

    { "c" 5 "b" 4 "a" 3 }dict
    dup array_first
    begin
        while
        over swap array_next
    repeat
    pop pop
;
