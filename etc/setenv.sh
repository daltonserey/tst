#!/usr/bin/env bash
# coding: utf-8
# (c) 2016 Dalton Serey, UFCG
#
# Interactive script to configure bash environment for TST. 

# constants
TST_DIR=~/.tst
DOT_PROFILE=~/.profile
DOT_BASHRC=~/.bashrc
INC_FILE=~/.tst/etc/tst.inc
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
NEWLINE="source '$INC_FILE' # $TIMESTAMP"

# colors
RESET="\033[0m"
BLACK="\033[0;30m"
BLUE="\033[0;34m"
BROWN="\033[0;33m"
CYAN="\033[0;36m"
DGRAY="\033[1;30m"
GREEN="\033[0;32m"
LBLUE="\033[1;34m"
LCYAN="\033[1;36m"
LGRAY="\033[0;37m"
LGREEN="\033[1;32m"
LPURPLE="\033[1;35m"
LRED="\033[1;31m"
PURPLE="\033[0;35m"
RED="\033[0;31m"
WHITE="\033[1;37m"
YELLOW="\033[1;33m"

# semantic colors
NORMAL=$LGRAY
WARNING=$LRED
IMPORTANT=$LBLUE
QUESTION=$LGREEN

# print with color
function print {
    echo -n -e $2"$1"$RESET
}

function create_backup {
    FILE=$1
    if [ -f "$FILE" ]; then
        TIMESTAMP=$(date "+%Y-%m-%dT%H:%M:%S")
        cp $FILE $FILE.bak.$TIMESTAMP
    fi
}

function replace_refs_to_old_installation {
    FILE=$1
    OLD_TST=$HOME/tst
    if [ -d "$OLD_TST" ]; then
        sed -i -e "s|$OLD_TST|$TST_DIR|g" $FILE
    fi
}

function add_source_line {
    FILE=$1
    PATTERN="source.*tst.inc.*"
    CHECK=$(grep -E "$PATTERN" $FILE 2> /dev/null)
    if [ "$?" == "0" ]; then
        # FILE has the tst pattern: update
        sed -i -e "s|$PATTERN|$NEWLINE|" $FILE
        print "File $FILE updated.\n"
    else
        # FILE doesn't have the tst pattern: add NEWLINE
        echo -e "\n# Next line configures environment for the TST CLI" >> $FILE
        echo "$NEWLINE" >> $FILE
        print "Lines added to $FILE.\n"
    fi
}

# MAIN

# configure .profile if it exists
if [ -f $DOT_PROFILE ]; then
    create_backup $DOT_PROFILE
    replace_refs_to_old_installation $DOT_PROFILE
    add_source_line $DOT_PROFILE
fi

# create .bashrc if it doesn't exist
if [ -f $DOT_BASHRC ]; then
    touch $DOT_BASHRC
fi

# backup .bashrc
create_backup $DOT_BASHRC

# configure .bashrc
replace_refs_to_old_installation $DOT_BASHRC
add_source_line $DOT_BASHRC
