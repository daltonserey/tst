#!/usr/bin/env bash
# coding: utf-8
# (c) 2016 Dalton Serey, UFCG
#
# Interactive script to configure bash environment for TST. 

# constants
DOT_PROFILE=~/.profile
DOT_BASHRC=~/.bashrc

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

function update_file {
    FILE=$1
    PATTERN_PATH="source.*tst.inc.*"
    PATH_FILE=~/.tst/etc/tst.inc
    TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
    LINE="source '$PATH_FILE' # $TIMESTAMP"

    CHECK=$(grep -E "$PATTERN_PATH" $FILE 2> /dev/null)
    if [ "$?" == "0" ]; then
        # FILE has the tst pattern
        if [ "$UPDATE" == "true" ]; then
            # update line in FILE 
            SED_COMMAND="s/$PATTERN_PATH/$LINE"
            sed -i.bak -e "s|source.*tst.inc.*|$LINE|" $FILE
            CHANGES_MADE="true"
            print "File $FILE updated.\n" $IMPORTANT
        else
            # don't update
            return 0
        fi
    else
        # FILE doesn't have the tst pattern: add LINE
        echo -e "\n# Next line configures environment for the TST CLI" >> $FILE
        echo "$LINE" >> $FILE
        print "Three lines added to $FILE.\n" $IMPORTANT
        CHANGES_MADE="true"
    fi
}

# MAIN
if [ "$1" == "--update" ]; then
    UPDATE="true"
fi

# configure .profile
if [ -f $DOT_PROFILE ]; then
    update_file $DOT_PROFILE
fi

# create .bashrc, if it doesn't exist
if [ ! -f $DOT_BASHRC ]; then
    touch .bashrc
fi

update_file $DOT_BASHRC

if [ "$CHANGES_MADE" != "true" ]; then
    print "Environment seems ok. No changes made.\n"
fi
