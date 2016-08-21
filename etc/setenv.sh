#!/usr/bin/env bash
# coding: utf-8
# (c) 2016 Dalton Serey, UFCG
#
# Configure bash environment for TST. 

# constants
TST_DIR=~/.tst
USER_DOT_PROFILE=~/.profile
USER_DOT_BASH_PROFILE=~/.bash_profile
TST_PATH_INCLUDE=$TST_DIR/etc/tst.path.inc
TST_PYTHONPATH_INCLUDE=$TST_DIR/etc/tst.pythonpath.inc

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

function update_dot_profile {
    echo >> $USER_DOT_PROFILE
    echo "# The next line sets up the PATH for tst" >> $USER_DOT_PROFILE
    echo "source '$TST_PATH_INCLUDE'" >> $USER_DOT_PROFILE
    echo >> $USER_DOT_PROFILE
    echo "# The next line sets up the PYTHONPATH for tst" >> $USER_DOT_PROFILE
    echo "source '$TST_PYTHONPATH_INCLUDE'" >> $USER_DOT_PROFILE
}

function update_dot_bash_profile {
    echo >> $USER_DOT_BASH_PROFILE
    echo "# Added by tst install script" >> $USER_DOT_BASH_PROFILE
    echo "# Source both .profile and .bashrc for login shells" >> $USER_DOT_BASH_PROFILE
    echo "if [ -f ~/.profile ]; then . ~/.profile; fi # Added by tst install script" >> $USER_DOT_BASH_PROFILE
    echo "if [ -f ~/.bashrc ]; then . ~/.bashrc; fi # Added by tst install script" >> $USER_DOT_BASH_PROFILE
}

function create_dot_profile {
    echo "# This file was created by the TST install procedure." >> $USER_DOT_PROFILE
    echo "# However, it is not part of TST itself and you can" >> $USER_DOT_PROFILE
    echo "# edit this file however you need." >> $USER_DOT_PROFILE
    echo "# Keep the tst section below or move them to the" >> $USER_DOT_PROFILE
    echo "# appropriate rc file, to make tst easier to use." >> $USER_DOT_PROFILE
}

function create_dot_bash_profile {
    echo "# This file was created by the TST install script." >> $USER_DOT_BASH_PROFILE
    echo "# However, it is not part of TST itself and you can" >> $USER_DOT_BASH_PROFILE
    echo "# edit this file however you need." >> $USER_DOT_BASH_PROFILE
}

# MAIN

if [ "$1" == "--non-interactive" ]; then
    INTERACTIVE="false"
else
    INTERACTIVE="true"
fi

# configure .profile
CHANGES_MADE="false"
if [ ! -f $USER_DOT_PROFILE ]; then
    create_dot_profile
    update_dot_profile
    CHANGES_MADE="true"
    print "File ~/.profile created.\n" $IMPORTANT
else
    # .profile DOES exist: check if it is configured
    CHECK=$(grep -E "source.*tst.path.inc" $USER_DOT_PROFILE 2> /dev/null)
    if [ "$?" == "0" ]; then
        # .profile looks ok
        if [ "INTERACTIVE" == "true" ]; then
            print "$USER_DOT_PROFILE looks ok. Not modified.\n" $NORMAL
        fi
    else
        # .profile does not look ok: create backup
        print "* $USER_DOT_PROFILE" $NORMAL
        print " => " $WARNING
        print "$USER_DOT_PROFILE.bak\n" $NORMAL
        cp $USER_DOT_PROFILE $USER_DOT_PROFILE.bak
        update_dot_profile
        CHANGES_MADE="true"
        print "File ~/.profile updated.\n" $IMPORTANT
    fi
fi

# configure .bash_profile
if [ ! -f $USER_DOT_BASH_PROFILE ]; then
    create_dot_bash_profile
    update_dot_bash_profile
    CHANGES_MADE="true"
    print "File ~/.bash_profile created.\n" $IMPORTANT
else
    CHECK=$(grep -E ".profile.*\. .*profile" $USER_DOT_BASH_PROFILE 2> /dev/null)
    if [ "$?" == "0" ]; then
        # .bash_profile looks ok
        if [ "INTERACTIVE" == "true" ]; then
            print "$USER_DOT_BASH_PROFILE looks ok. Not modified.\n" $NORMAL
        fi
    else
        # .bash_profile does not look ok
        print "* $USER_DOT_BASH_PROFILE" $NORMAL
        print " => " $WARNING
        print "$USER_DOT_BASH_PROFILE.bak\n" $NORMAL
        cp $USER_DOT_BASH_PROFILE $USER_DOT_BASH_PROFILE.bak
        update_dot_bash_profile
        CHANGES_MADE="true"
        print "File ~/.bash_profile updated.\n" $IMPORTANT
    fi
fi

if [ "$CHANGES_MADE" == "false" ]; then
    print "Environment seems ok. No changes made.\n" $IMPORTANT
fi
