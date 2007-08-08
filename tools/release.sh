#!/bin/sh

# Run this from the root directory of Luminotes's source. Note: This will nuke your database!

ORIG_PYTHONPATH="$PYTHONPATH"
PYTHONPATH=.
python2.5 tools/initdb.py
PYTHONPATH="$ORIG_PYTHONPATH"
cd ..
rm -f luminotes.tar.gz
tar cvfz luminotes.tar.gz --exclude=session --exclude="*.log" --exclude="*.pyc" --exclude=".*" luminotes
cd -
