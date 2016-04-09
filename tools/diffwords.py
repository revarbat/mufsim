#!/usr/bin/env python

import argparse

parser = argparse.ArgumentParser(prog='mufsim')
parser.add_argument('file1', help='Filename 1.')
parser.add_argument('file2', help='Filename 2.')
args = parser.parse_args()

inlines = []
with open(args.file1, "r") as f:
    inlines = f.readlines() 

delwords = []
with open(args.file2, "r") as f:
    delwords = f.readlines() 

delwords = frozenset([word.strip() for word in delwords])

for line in inlines:
    key = line.strip()
    if " " in key:
        key = key.strip().rsplit(" ", )[1]
    if key not in delwords:
        print(line.rstrip("\n"))

