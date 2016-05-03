: main
    "Spike" "pointy" newplayer
    dup name pop
    dup player? pop
    "Wilma" "tsundere" copyplayer
    dup name pop
    dup player? pop
    pop

    loc @ "Another Room" newroom
    dup name pop
    dup room? pop
    recycle

    me @ "McGuffin" newobject
    dup name pop
    dup thing? pop
    dup copyobj
    swap recycle
    dup name pop
    dup thing? pop
    recycle

    me @ "poke" newexit
    dup name pop
    dup exit? pop
    recycle

    "cmd-poke" newprogram
    dup name pop
    dup program? pop
    recycle
;

