#!/bin/sh

refresh_only=0
if [[ $# -gt 0 ]]; then
    case $1 in
        --refresh) refresh_only=1 ;;
    esac
fi
for f in *.muf *.muv ; do
    base=$(basename $(basename $f .muv) .muf)
    outfile=$base.out
    cmpfile=$base.cmp
    if [ "$refresh_only" -eq 0 -o ! -e "$cmpfile" ]; then
        echo $f
        mufsim $f -u -r -t 2>&1 | sed 's/.\[?1034h//g' >$outfile
        if [ ! -e "$cmpfile" ]; then
            echo "Installing results as $cmpfile"
            mv -f $outfile $cmpfile
            else
            diff -u $cmpfile $outfile
        fi
    fi
    rm -f $outfile
done

