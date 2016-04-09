: main
    { "d" "h" "G" "B" "j" "E" "a" "i" "F" "c" }list
    var! arr
    {
        0
        sorttype_caseinsens
        sorttype_descending
        sorttype_caseinsens sorttype_descending bitor
    }list foreach var! mode pop
        arr @ mode @ array_sort pop
    repeat
;
