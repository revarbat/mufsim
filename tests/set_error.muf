: main
    "DIV_ZERO" is_set? pop
    "FBOUNDS" is_set? pop

    "DIV_ZERO" set_error
    "DIV_ZERO" is_set? pop
    "FBOUNDS" is_set? pop

    "FBOUNDS" set_error
    "DIV_ZERO" is_set? pop
    "FBOUNDS" is_set? pop
;
