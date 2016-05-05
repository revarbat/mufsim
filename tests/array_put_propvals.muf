: main
    me @ "abc" array_get_propvals
    "quxqux" swap "foob" ->[]
    "feefie" swap "bamboom" ->[]
    me @ "abc" rot array_put_propvals
    me @ "abc" array_get_propvals pop
;

