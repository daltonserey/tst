#!/usr/bin/env bash
# coding: utf-8
# (c) 2016 Dalton Serey, UFCG
#
# Configure bash environment for TST. 

# constants
USER_DOT_PROFILE=~/.profile
USER_DOT_BASH_PROFILE=~/.bash_profile

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

# read either 'y' or 'n' from keyboard
function get_yes_or_no {
    while true; do 
        read -s -n 1 ANSWER
        if [ "$ANSWER" == 'y' ]; then break; fi
        if [ "$ANSWER" == 'n' ]; then break; fi
    done
    echo $ANSWER
}

# print with color
function print {
    echo -n -e $2"$1"$RESET
}

# MAIN

# assume .profile is not configured
DOT_PROFILE_CONFIGURED="false"
if [ ! -f $USER_DOT_PROFILE ]; then
    # create .profile
    print "* creating $USER_DOT_PROFILE\n" $NORMAL
    echo "# This file was created by the TST install procedure." >> $USER_DOT_PROFILE
    echo "# However, it is not part of TST itself and you can" >> $USER_DOT_PROFILE
    echo "# edit this file however you need." >> $USER_DOT_PROFILE
    echo "# Keep the tst section below or move them to the" >> $USER_DOT_PROFILE
    echo "# appropriate rc file, to make tst easier to use." >> $USER_DOT_PROFILE
else
    # .profile exists: check it is configured
    LINES=$(grep -E "source.*tst.path.inc" $USER_DOT_PROFILE 2> /dev/null)
    if [ "$?" == "0" ]; then
        DOT_PROFILE_CONFIGURED="true"
    fi

    # make a bakcup copy
    if [ "$DOT_PROFILE_CONFIGURED" != "true" ]; then
        print "* copying $USER_DOT_PROFILE" $NORMAL
        print " => " $WARNING
        print "$USER_DOT_PROFILE.bak\n" $NORMAL
        cp $USER_DOT_PROFILE $USER_DOT_PROFILE.bak
    fi
fi

# add source line to .profile
if [ "$DOT_PROFILE_CONFIGURED" == "true" ]; then
    print "$USER_DOT_PROFILE seems already configured.\n" $NORMAL
    print "No changes made.\n" $IMPORTANT
else
    TST_PATH_INCLUDE=$1/etc/tst.path.inc
    echo >> $USER_DOT_PROFILE
    echo "# The next line sets up the PATH for tst" >> $USER_DOT_PROFILE
    echo "source '$TST_PATH_INCLUDE'" >> $USER_DOT_PROFILE
    print "* configuring $USER_DOT_PROFILE\n" $NORMAL
fi

## setup .bash_profile
print "* configuring $USER_DOT_BASH_PROFILE\n" $NORMAL
DOT_BASH_PROFILE_CONFIGURED="false"
if [ ! -f $USER_DOT_BASH_PROFILE ]; then
    print "* creating $USER_DOT_BASH_PROFILE\n" $NORMAL
    echo "# This file was created by the TST install script." >> $USER_DOT_BASH_PROFILE
    echo "# However, it is not part of TST itself and you can" >> $USER_DOT_BASH_PROFILE
    echo "# edit this file however you need." >> $USER_DOT_BASH_PROFILE
else
    LINES=$(grep -E ".profile.*\. .*profile" $USER_DOT_BASH_PROFILE 2> /dev/null)
    if [ "$?" == "0" ]; then
        DOT_BASH_PROFILE_CONFIGURED="true"
    fi
    
    if [ "$DOT_BASH_PROFILE_CONFIGURED" != "true" ]; then
        print "* copying $USER_DOT_BASH_PROFILE" $NORMAL
        print " => " $WARNING
        print "$USER_DOT_BASH_PROFILE.bak\n" $NORMAL
        cp $USER_DOT_BASH_PROFILE $USER_DOT_BASH_PROFILE.bak
    fi
fi

if [ "$DOT_BASH_PROFILE_CONFIGURED" == "true" ]; then
    print "$USER_DOT_BASH_PROFILE seems already configured.\n" $NORMAL
    print "No changes made.\n" $IMPORTANT
else
    print "* configuring $USER_DOT_BASH_PROFILE configured.\n" $NORMAL
    echo >> $USER_DOT_BASH_PROFILE
    echo "# Source both .profile and .bashrc for login shells" >> $USER_DOT_BASH_PROFILE
    echo "if [ -f ~/.profile ]; then . ~/.profile; fi # Added by tst install script" >> $USER_DOT_BASH_PROFILE
    echo "if [ -f ~/.bashrc ]; then . ~/.bashrc; fi # Added by tst install script" >> $USER_DOT_BASH_PROFILE
fi
