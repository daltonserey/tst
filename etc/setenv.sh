#!/usr/bin/env bash
# coding: utf-8
# (c) 2016 Dalton Serey, UFCG
#
# Script to configure bash environment for TST. 

# constants
OLD_TST=$HOME/tst
BASHRC=~/.bashrc
PATHS_FILE=~/.tst/etc/tst.paths.inc
COMPLETION_FILE=~/.tst/etc/tst.completion.inc
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")

function create_backup {
    local file
    file=$1
    if [ -f "$file" ]; then
        cp $file "$file.bak.$TIMESTAMP"
        if [[ "$?" != "0" ]]; then
            echo "error: couldn't create backup"
            echo "aborting setenv.sh"
            exit 1
        fi
    fi
}

function comment_out_old_tst {
    local file old_tst
    file=$1
    old_tst=$HOME/tst
    sed -i "\|$old_tst| s/^/#/" $file
}

# MAIN

# backup .bashrc
[[ -f $BASHRC ]] && create_backup $BASHRC || touch $BASHRC

# comment out lines with refs to old tst version
sed -i "\|$OLD_TST| s/^/#/" $BASHRC

# update/add source tst.paths.inc
pattern=".*source.*tst.paths.inc.*"
source_line="source '$PATHS_FILE'"
if grep -q -E "$pattern" $BASHRC; then
    # update source line
    echo "Updating .bashrc ($source_line)"
    sed -i "s|$pattern|$source_line # $TIMESTAMP|" $BASHRC
else
    # add source line
    echo "Adding "$source_line" to .bashrc"
    echo -e "\n# The next line configures PATH and PYTHONPATH for TST" >> $BASHRC
    echo "$source_line # $TIMESTAMP" >> $BASHRC
fi

# update/add source tst.completion.inc
pattern=".*source.*tst.completion.inc.*"
source_line="source '$COMPLETION_FILE'"
if grep -q -E "$pattern" $BASHRC; then
    # update source line
    echo "Updating .bashrc ($source_line)"
    sed -i "s|$pattern|$source_line # $TIMESTAMP|" $BASHRC
else
    # add source line
    echo "Adding "$source_line" to .bashrc"
    echo -e "\n# The next line configures completion for TST" >> $BASHRC
    echo "$source_line # $TIMESTAMP" >> $BASHRC
fi

rm -f $BASHRC-e
