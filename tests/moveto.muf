: main
    me @ location var! oldloc
    #0 var! newloc
    oldloc @ contents_array pop
    newloc @ contents_array pop
    me @ location pop
    me @ newloc @ moveto
    oldloc @ contents_array pop
    newloc @ contents_array pop
    me @ location pop
;

