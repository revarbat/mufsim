: main
    0 try
      "foo" abort
    catch pop
    endcatch
    3 4 5
    2 try
      "bar" abort
    catch_detailed pop
    endcatch
    pop
    3 4 5
    2 try
      pop pop pop
    catch pop
    endcatch
    pop
;
