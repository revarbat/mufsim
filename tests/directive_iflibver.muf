$lib-version 3.14
: main
    $iflibver this 3.00
        "Pass"
    $else
        "FAIL"
    $endif
    $iflibver this 3.14
        "Pass"
    $else
        "FAIL"
    $endif
    $iflibver this 3.15
        "FAIL"
    $else
        "Pass"
    $endif
;

