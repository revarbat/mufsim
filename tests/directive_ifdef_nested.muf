$def foobar 100
: main
    $ifdef supercalifragilist
        "FAIL"
    $else
        $ifdef foobar
            $ifdef foobar=100
                $ifdef foobar<101
                    $ifdef foobar>099
                        "Pass"
                    $else
                        "FAIL"
                    $endif
                $else
                    "FAIL"
                $endif
            $else
                "FAIL"
            $endif
        $else
            "FAIL"
        $endif
    $endif
;

