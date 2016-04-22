: main
    {
        {
            "username" "Johnny"
            "count" 4
            "object" #6
            "foo"  pi
        }dict
        {
            "username" "Ghaladahsk_Fadja"
            "count" 123
            "object" #5
        }dict
    }list
    "%-21.20[username]s %4[count]i %15[object]D %5.3[foo]g"
    array_fmtstrings
    { me @ }list array_notify
;

