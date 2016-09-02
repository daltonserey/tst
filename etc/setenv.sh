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

# colors
LRED="\033[1;31m"
LGRAY="\033[0;37m"

# semantic colors
NORMAL=$LGRAY
WARNING=$LRED

# print with color
function print {
    COLOR=$2
    if [[ "$COLOR" == "" ]]; then
        COLOR=$NORMAL
    fi

    echo -n -e $COLOR"$1"$RESET
}

function create_backup {
    local file
    file=$1
    if [ -f "$file" ]; then
        cp $file "$file.bak.$TIMESTAMP"
        if [[ "$?" != "0" ]]; then
            print "error: couldn't create backup\n" $WARNING
            print "aborting setenv.sh\n" $WARNING
            exit 1
        fi
    fi
}

function comment_out_old_tst {
    local file old_tst
    file=$1
    old_tst=$HOME/tst
    sed -i~ "\|$old_tst| s/^/#/" $file
}

# MAIN

# process --quiet option
[[ "$1" == "--quiet" ]] && VERBOSE="false" || VERBOSE="true"

# backup .bashrc
[[ "$VERBOSE" == "true" ]] && print "* creating backup of .bashrc\n"
[[ -f $BASHRC ]] && create_backup $BASHRC || touch $BASHRC

# comment out lines with refs to old tst version
[[ "$VERBOSE" == "true" ]] && print "* updating .bashrc\n"
sed -i~ "\|$OLD_TST| s/^/#/" $BASHRC

# comment out lines with refs to pre-release tst.inc file
sed -i~ "/.*tst.inc.*/ s/^/#/" $BASHRC

# update/add source tst.paths.inc
pattern=".*source.*tst.paths.inc.*"
source_line="source '$PATHS_FILE'"
if grep -q -E "$pattern" $BASHRC; then
    # update source line
    sed -i~ "s|$pattern|$source_line # $TIMESTAMP|" $BASHRC
else
    # add source line
    echo -e "\n# The next line configures PATH and PYTHONPATH for TST" >> $BASHRC
    echo "$source_line # $TIMESTAMP" >> $BASHRC
fi

# update/add source tst.completion.inc
pattern=".*source.*tst.completion.inc.*"
source_line="source '$COMPLETION_FILE'"
if grep -q -E "$pattern" $BASHRC; then
    # update source line
    sed -i~ "s|$pattern|$source_line # $TIMESTAMP|" $BASHRC
else
    # add source line
    echo -e "\n# The next line configures completion for TST" >> $BASHRC
    echo "$source_line # $TIMESTAMP" >> $BASHRC
fi

# remove .bashrc bakcup created by sed (actual backup still exists)
rm -f $BASHRC~
