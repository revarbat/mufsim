: bar
    0 pop
;
: main[ arg -- ]
    {
        { 1 { 'bar }list "a" }list
        { 0 { 1 }list "a" }list
        { 1 { #4 }list "D" }list
        { 0 { #-1 }list "D" }list
        { 0 { 1 }list "D" }list
        { 1 { #4 }list "d" }list
        { 1 { #-1 }list "d" }list
        { 0 { 1 }list "d" }list
        { 1 { 1 }list "i" }list
        { 0 { #-1 }list "i" }list
        { 1 { "foo" }list "s" }list
        { 1 { "" }list "s" }list
        { 0 { 1 }list "s" }list
        { 1 { "foo" }list "S" }list
        { 0 { "" }list "S" }list
        { 0 { 1 }list "S" }list
        { 1 { "a" "b" "c" }list "s3" }list
        { 0 { "a" "b" "c" }list "s4" }list
        { 0 { "a" "b" "c" }list "i3" }list
        { 0 { 1 "b" "c" }list "s3" }list
        { 1 { 1 "b" "c" }list "is2" }list
        { 0 { 1 2 "c" }list "is2" }list
        { 1 { "a" "b" "c" 3 }list "{S}" }list
        { 1 { "a" "b" "c" 3 "a" }list "{S}s" }list
        { 1 { #4 "a" "b" "c" 3 }list "d{S}" }list
        { 1 { "foo" 42 #3 #4 #5 3 'bar }list "si{d}a" }list
        { 0 { "foo" 42 #3 #4 #5 3 'bar }list "di{d}a" }list
        { 1 { "foo" 42 #3 "a" #4 "b" #5 "c" 3 'bar }list "si{ds}a" }list
        { 0 { "foo" 42 #3 "a" #4 3 #5 "c" 3 'bar }list "si{ds}a" }list
    }list
    foreach swap pop
        array_vals pop
        var! fmt var! args var! res
        0 try
            args @ array_vals pop
            fmt @ checkargs
        catch
            res @ not res !
        endcatch
        depth popn
        {
            res @ if "Pass" else "FAIL" then
            ": fmt='"
            fmt @
            "'  args="
            args @ ", " array_join
        }list array_interpret
        me @ swap notify
    repeat
;

