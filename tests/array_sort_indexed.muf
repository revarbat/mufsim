: main
    {
        { "name" "John" "age" 23 }dict
        { "name" "Jane" "age" 25 }dict
        { "name" "Mary" "age" 37 }dict
        { "name" "Raul" "age" 17 }dict
        { "name" "Faun" "age" 26 }dict
        { "name" "Mike" "age" 35 }dict
    }list var! items
    items @ sorttype_nocase_ascend "age" array_sort_indexed pop
    items @ sorttype_nocase_descend "age" array_sort_indexed pop
    items @ sorttype_nocase_ascend "name" array_sort_indexed pop
    items @ sorttype_nocase_descend "name" array_sort_indexed pop
;

