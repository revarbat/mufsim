$version 3.14
: main
    $ifver this 3.00
        "Pass"
    $else
        "FAIL"
    $endif
    $ifver this 3.14
        "Pass"
    $else
        "FAIL"
    $endif
    $ifver this 3.15
        "FAIL"
    $else
        "Pass"
    $endif
;

