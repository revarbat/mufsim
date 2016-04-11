: main
    { 0 1 }list foreach swap pop
        if
            #0 "foo"
            "C" setprop
        else
            #0 "foo"
            remove_prop
        then
        { 0 1 }list foreach swap pop
            if
                me @ location "foo"
                "B" setprop
            else
                me @ location "foo"
                remove_prop
            then
            { 0 1 }list foreach swap pop
                if
                    me @ "foo"
                    "A" setprop
                else
                    me @ "foo"
                    remove_prop
                then
                me @ "foo" envprop pop
            repeat
        repeat
    repeat
;

