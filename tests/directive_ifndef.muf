$def foobar 100
: main
    $ifndef supercalifragilist
        "Pass"
    $else
        "FAIL"
    $endif
    $ifndef foobar
        "FAIL"
    $else
        "Pass"
    $endif
    $ifndef foobar=100
        "FAIL"
    $else
        "Pass"
    $endif
    $ifndef foobar=099
        "Pass"
    $else
        "FAIL"
    $endif
    $ifndef foobar>099
        "FAIL"
    $else
        "Pass"
    $endif
    $ifndef foobar>101
        "Pass"
    $else
        "FAIL"
    $endif
    $ifndef foobar<099
        "Pass"
    $else
        "FAIL"
    $endif
    $ifndef foobar<101
        "FAIL"
    $else
        "Pass"
    $endif
;
