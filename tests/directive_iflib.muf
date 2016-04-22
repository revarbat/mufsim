: main
    $iflib this
        "Pass"
    $else
        "FAIL"
    $endif
    $iflib $lib/supercalifragil
        "FAIL"
    $else
        "Pass"
    $endif
    $iflib $cmd/test
        "Pass"
    $else
        "FAIL"
    $endif
;

