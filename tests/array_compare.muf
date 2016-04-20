: main
    { "a" 3 "b" 4 "c" 5 }dict
    { "c" 5 "b" 4 "a" 3 }dict
    array_compare pop
    { "a" 3 "b" 4 "c" 5 }dict
    { "c" 5 "b" 6 "a" 3 }dict
    array_compare pop
;

