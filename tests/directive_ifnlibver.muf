$lib-version 3.14
: main
    $ifnlibver this 3.00
        "FAIL"
    $else
        "Pass"
    $endif
    $ifnlibver this 3.14
        "FAIL"
    $else
        "Pass"
    $endif
    $ifnlibver this 3.15
        "Pass"
    $else
        "FAIL"
    $endif
;

