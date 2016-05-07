: main[ arg -- ]
    "jane_doe" pmatch
    dup player? pop
    dup thing? pop
    dup name pop
    dup owner pop
    #1 over toadplayer
    dup player? pop
    dup thing? pop
    dup name pop
    dup owner pop
    pop
;

