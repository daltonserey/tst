#!/usr/bin/env bash
# coding: utf-8
# (c) 2016 Dalton Serey, UFCG
#
# TST Installer script. Download and install tst CLI scripts. 

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

# read a 'y' or 'n' from keyboard
function get_yes_or_no {
    while true; do 
        read -s -n 1 KEY
        if [ "$KEY" == 'y' ]; then break; fi
        if [ "$KEY" == 'n' ]; then break; fi
    done
    echo $KEY
}

# print with color
function print {
    echo -n -e $2"$1"$RESET
}

# set environment for tst CLI
function set_environment {

    # setup .profile
    DOT_PROFILE=~/.profile2

    # assume .profile is not configured
    DOT_PROFILE_CONFIGURED="false"
    if [ ! -f $DOT_PROFILE ]; then
        # create .profile
        print "* creating $DOT_PROFILE\n" $IMPORTANT
        echo "# This file was created by the TST install procedure." >> $DOT_PROFILE
        echo "# However, it is not part of TST itself and you can" >> $DOT_PROFILE
        echo "# edit this file however you need." >> $DOT_PROFILE
        echo "# Keep the tst section below or move them to the" >> $DOT_PROFILE
        echo "# appropriate rc file, to make tst easier to use." >> $DOT_PROFILE
    else
        # .profile exists: check if is configured
        LINES=$(grep -E "source.*tst.path.inc" $DOT_PROFILE 2> /dev/null)
        if [ "$?" == "0" ]; then
            DOT_PROFILE_CONFIGURED="true"
        fi

        # make a bakcup copy
        if [ "$DOT_PROFILE_CONFIGURED" != "true" ]; then
            print "* copying $DOT_PROFILE" $NORMAL
            print " => " $WARNING
            print "$DOT_PROFILE.bak\n" $NORMAL
            cp $DOT_PROFILE $DOT_PROFILE.bak
        fi
    fi

    # add source line to .profile
    if [ "$DOT_PROFILE_CONFIGURED" == "true" ]; then
        print "File $DOT_PROFILE already configured. No changes made.\n"
    else
        TST_PATH_INCLUDE=$TSTDIR/tst/etc/tst.path.inc
        echo >> $DOT_PROFILE
        echo "# The next line sets up the PATH for tst" >> $DOT_PROFILE
        echo "source '$TST_PATH_INCLUDE'" >> $DOT_PROFILE
        print "File $DOT_PROFILE configured.\n"
    fi

    ## setup .bash_profile
    DOT_BASH_PROFILE=~/.bash_profile2
    DOT_BASH_PROFILE_CONFIGURED="false"
    if [ ! -f $DOT_BASH_PROFILE ]; then
        print "* creating $DOT_BASH_PROFILE\n" $IMPORTANT
        echo "# This file was created by the TST install script." >> $DOT_BASH_PROFILE
        echo "# However, it is not part of TST itself and you can" >> $DOT_BASH_PROFILE
        echo "# edit this file however you need." >> $DOT_BASH_PROFILE
    else
        LINES=$(grep -E ".profile.*\. .*profile" $DOT_BASH_PROFILE 2> /dev/null)
        if [ "$?" == "0" ]; then
            DOT_BASH_PROFILE_CONFIGURED="true"
        fi
        
        if [ "$DOT_BASH_PROFILE_CONFIGURED" != "true" ]; then
            print "* copying $DOT_BASH_PROFILE" $NORMAL
            print " => " $WARNING
            print "$DOT_BASH_PROFILE.bak\n" $NORMAL
            cp $DOT_BASH_PROFILE $DOT_BASH_PROFILE.bak
        fi
    fi

    if [ "$DOT_BASH_PROFILE_CONFIGURED" == "true" ]; then
        print "File $DOT_BASH_PROFILE already configured. No changes made.\n"
    else
        echo >> $DOT_BASH_PROFILE
        echo "# Source both .profile and .bashrc for login shells" >> $DOT_BASH_PROFILE
        echo "if [ -f ~/.profile ]; then . ~/.profile; fi # Added by tst install script" >> $DOT_BASH_PROFILE
        echo "if [ -f ~/.bashrc ]; then . ~/.bashrc; fi # Added by tst install script" >> $DOT_BASH_PROFILE
        print "File $DOT_BASH_PROFILE configured.\n"
    fi
}


# MAIN
if [ "$1" == "--set-env" ]; then
    set_environment
    exit 0
fi

# DOWNLOAD AND INSTALL TST
print "Download and install tst command line tools\n" $IMPORTANT

# require curl or abort
CURL=$(command -v curl)
if [ $? != 0 ]; then
    echo "the installation script requires the curl command";
    echo "aborting installation";
    exit 1
fi

# require unzip or abort
UNZIP=$(command -v unzip)
if [ $? != 0 ]; then
    echo "the installation script requires the unzip command";
    echo "aborting installation";
    exit 1
fi

# create tst directory
TSTDIR=~/.tst3
if [ -d $TSTDIR ]; then
    # remove if required by '--del-previous' option
    if [ "$1" == '--del-previous' ]; then
        print "* deleting previous installation\n" $NORMAL
        OLD_INSTALLATION=~/.tst"-$(date +%Y-%m-%dT%H:%M:%S)"
        mv $TSTDIR $OLD_INSTALLATION
    else
        print "You already have tst installed\n" $WARNING
        print "* installation aborted\n" $NORMAL
        print "Use --del-previous option to delete previous installation\n" $NORMAL
        print "Use --set-env option to configure environment\n" $NORMAL
        exit 1
    fi
fi

# create new tst installation dir
mkdir $TSTDIR
if [ -f "$OLD_INSTALLATION/config.json" ]; then
    cp $OLD_INSTALLATION/config.json $TSTDIR
fi
cd $TSTDIR

# get zipball_url of latest release
print "* checking tst latest release\n" $NORMAL
LATEST_URL='https://api.github.com/repos/daltonserey/tst/releases/latest'
LATEST_RELEASE=$(curl -q $LATEST_URL 2> /dev/null)
if [ $? != 0 ]; then
    print "Couldn't download info about latest release\n" $WARNING
    print "Installation aborted\n" $NORMAL
    exit
fi
ZIPBALL_URL=$(echo -e "$LATEST_RELEASE" | grep "zipball_url" | cut -f 4 -d '"')

# download the latest release
print "* downloading tst latest release\n" $NORMAL
curl -q -Lko tst.zip $ZIPBALL_URL 2> /dev/null
if [ $? != 0 ]; then
    print "Couldn't download the latest release\n" $WARNING
    print "Installation aborted\n" $NORMAL
    exit
fi

# unzip tst
print "* unzipping and installing tst scripts\n" $NORMAL
unzip -q tst.zip

# move distribution contents to tst folder
mv daltonserey-tst*/* $TSTDIR
rmdir daltonserey-tst*

print "Installation finished.\n" $IMPORTANT
print "\nConfigure environment? (y/n) " $QUESTION
get_yes_or_no
if [ "$KEY" == "y" ]; then
    set_environment
    print "Environment successfully configured.\n" $IMPORTANT
else
    print "Environment was" $NORMAL
    print " not " $WARNING
    print "configured.\n" $NORMAL
    print "Remember to add " $NORMAL
    print "~/.tst/bin" $IMPORTANT
    print " to your PATH\n" $NORMAL
    print "Or run " $NORMAL
    print "~/.tst/assets/install.sh --set-env" $IMPORTANT
    print " to configure your environment.\n" $NORMAL
    exit
fi
