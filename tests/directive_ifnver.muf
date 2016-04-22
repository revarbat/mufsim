$version 3.14
: main
    $ifnver this 3.00
        "FAIL"
    $else
        "Pass"
    $endif
    $ifnver this 3.14
        "FAIL"
    $else
        "Pass"
    $endif
    $ifnver this 3.15
        "Pass"
    $else
        "FAIL"
    $endif
;

