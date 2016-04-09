: main
    "%n is in %p happy place by %r and it suits %o, as it is %a, and %s earned it." var! msg
    "%N is in %P happy place by %R and it suits %O, as it is %A, and %S earned it." var! msg2
    { "male" "female" "herm" "hermaphrodite" "none" }list
    foreach swap pop
        me @ "sex" rot setpropstr
        me @ dup msg @ pronoun_sub notify
        me @ dup msg2 @ pronoun_sub notify
    repeat
;
