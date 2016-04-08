#!/bin/sh

for f in *.muf ; do
    echo $f
    outfile=$(basename $f .muf).out
    cmpfile=$(basename $f .muf).cmp
    ../mufsim $f -u -r -t >$outfile 2>&1
    if [[ ! -e $cmpfile ]]; then
	echo "Installing results as $cmpfile"
	mv -f $outfile $cmpfile
    else
	diff -u $cmpfile $outfile
    fi
    rm -f $outfile
done

