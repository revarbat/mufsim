: main[ arg -- ]
    1462572502 dup timesplit "%03i %i %04i %02i %02i %02i %02i %02i" fmtstring
    "%j %w %Y %m %d %H %M %S" rot timefmt
    stringcmp pop
;
