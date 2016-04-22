$def foobar 100
: main
    $ifdef supercalifragilist
        "FAIL"
    $else
        "Pass"
    $endif
    $ifdef foobar
        "Pass"
    $else
        "FAIL"
    $endif
    $ifdef foobar=100
        "Pass"
    $else
        "FAIL"
    $endif
    $ifdef foobar=099
        "FAIL"
    $else
        "Pass"
    $endif
    $ifdef foobar>099
        "Pass"
    $else
        "FAIL"
    $endif
    $ifdef foobar>101
        "FAIL"
    $else
        "Pass"
    $endif
    $ifdef foobar<099
        "FAIL"
    $else
        "Pass"
    $endif
    $ifdef foobar<101
        "Pass"
    $else
        "FAIL"
    $endif
;
