#!/bin/sh

refresh_only=0
if [[ $# -gt 0 ]]; then
    case $1 in
        --refresh) refresh_only=1 ;;
    esac
fi
for f in *.muf ; do
    outfile=$(basename $f .muf).out
    cmpfile=$(basename $f .muf).cmp
    if [ "$refresh_only" -eq 0 -o ! -e "$cmpfile" ]; then
        echo $f
        ../mufsim $f -u -r -t >$outfile 2>&1
        if [ ! -e "$cmpfile" ]; then
            echo "Installing results as $cmpfile"
            mv -f $outfile $cmpfile
            else
            diff -u $cmpfile $outfile
        fi
    fi
    rm -f $outfile
done

