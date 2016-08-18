#!/usr/bin/env bash
# coding: utf-8
# (c) 2016 Dalton Serey, UFCG
#
# Interactive TST Installer script. Download and install tst CLI scripts. 

# constants
INSTALL_DIR=~/.tst.install
TST_DIR=~/.tst
CONFIG_FILE=~/.tst/config.json
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
# process options
while (( $# > 0 )); do
    case "$1" in
        --del-previous)
            DELETE_PREVIOUS="true"
            ;;
        --development-version)
            DOWNLOAD_DEV_VERSION="true"
            ;;
        --*)
            print "invalid option $1\n" $WARNING
            exit 1
            ;;
    esac
    shift
done


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

# identify releases url
if [ "$DOWNLOAD_DEV_VERSION" == "true" ]; then
    RELEASES_URL='https://api.github.com/repos/daltonserey/tst/releases'
    print "* fetching development pre-release information\n" $NORMAL
else
    RELEASES_URL='https://api.github.com/repos/daltonserey/tst/releases/latest'
    print "* fetching latest release information\n" $NORMAL
fi

# download releases info; identify tag_name and zipball_url
RELEASES=$(curl -q $RELEASES_URL 2> /dev/null)
if [ $? != 0 ]; then
    print "Couldn't download release information\n" $WARNING
    print "Installation aborted\n" $NORMAL
    exit 1
fi
TAG_NAME=$(echo -e "$RELEASES" | grep "tag_name" | cut -f 4 -d '"' | head -1)
ZIPBALL_URL=$(echo -e "$RELEASES" | grep "zipball_url" | cut -f 4 -d '"' | head -1)

# cancel installation it there's no release available
if [ "$TAG_NAME" == "" ]; then
    print "No release available\n" $WARNING
    print "Installation canceled\n" $IMPORTANT
    exit 1
fi
print "> version available: $TAG_NAME\n" $NORMAL

# check for other installation
if [ -d $TST_DIR ]; then

    # check other installation version
    if [ -f "$TST_DIR/release.json" ]; then
        PREVIOUS_TAG_NAME=$(cat $TST_DIR/release.json | grep "tag_name" | cut -f 4 -d '"')
    fi

    # check if other installation is the same to be installed
    if [ "$PREVIOUS_TAG_NAME" == "$TAG_NAME" ]; then
        print "Version $PREVIOUS_TAG_NAME is already installed\n" $IMPORTANT
    else
        print "A different version ($PREVIOUS_TAG_NAME) of TST was found\n" $IMPORTANT
    fi

    print "Delete and proceed? (y/n) " $QUESTION
    get_yes_or_no
    if [ "$ANSWER" != "y" ]; then
        print "Installation cancelled by user\n" $IMPORTANT
        exit 0
    fi
    # delete existing installation
    rm -rf $TST_DIR

fi

# create installation dir
if [ -f "$INSTALL_DIR" ]; then
    print "* deleting failed attempt to install" $WARNING 
    rm -rf $INSTALL_DIR
fi

mkdir $INSTALL_DIR

# download latest release
cd $INSTALL_DIR
print "* downloading release zip\n" $NORMAL
curl -q -Lko tst.zip $ZIPBALL_URL 2> /dev/null
if [ $? != 0 ]; then
    rm -rf $INSTALL_DIR
    echo $ZIPBALL_URL
    print "Couldn't download release zip\n" $WARNING
    print "Installation aborted\n" $NORMAL
    print "Temporary files deleted\n" $NORMAL
    exit 1
fi

# unzip and install tst scripts
print "* unzipping and installing tst scripts\n" $NORMAL
unzip -q tst.zip
rm tst.zip
mv daltonserey-tst*/* $INSTALL_DIR
rm daltonserey-tst*/.gitignore
rmdir daltonserey-tst*

# add user configuration file
if [ -f $CONFIG_FILE ]; then
    cp $CONFIG_FILE $INSTALL_DIR/
fi

# add release.json
echo "{\"tag_name\": \"$TAG_NAME\"}" > release.json

# rename TST_DIR to definitive name
mv $INSTALL_DIR $TST_DIR
print "Installation finished.\n" $IMPORTANT

# configure environment
print "\nConfigure environment? (y/n) " $QUESTION
get_yes_or_no
if [ "$ANSWER" == "y" ]; then
    $TST_DIR/etc/setenv.sh
    print "Environment configured.\n" $IMPORTANT
    exit
else
    print "Environment was" $NORMAL
    print " not " $WARNING
    print "configured.\n" $NORMAL
    print "Remember to add " $NORMAL
    print "~/.tst/bin" $IMPORTANT
    print " to your PATH\n" $NORMAL
    print "To configure your environment, run:\n" $NORMAL
    print "    ~/.tst/etc/install.sh --set-environment\n" $IMPORTANT
    exit
fi
