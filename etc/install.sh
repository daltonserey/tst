#!/usr/bin/env bash
# coding: utf-8
# (c) 2016 Dalton Serey, UFCG
#
# Interactive TST Installer script. Run this script to download
# and install TST CLI tools. This script can be invoked with
# these options:
#
# --pre-release
#       Download the latest pre-release version available.
#
# --update
#       Update existing installation. In this mode, the install
#       script runs in non-interactive mode. It prints less
#       evolution messages, it doesn't ask whether or not to
#       overwrite previous installations, it doesn't configure
#       the enviroment and doesn't delete old installations of
#       tst.  This mode is used by the tst update command.
#
# --installation-dir <dir>
#       Install the new version into <dir>.

# constants
INSTALL_DIR=~/.tst.install
TST_DIR=~/.tst
CONFIG_FILE=~/.tst/config.json

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
        read -s -n 1 answer
        [[ "$answer" == "y" ]] && break
        [[ "$answer" == "n" ]] && break
    done
    echo $answer
}

# print with color
function print {
    COLOR=$2
    if [ "$COLOR" == "" ]; then
        COLOR=$NORMAL
    fi

    echo -n -e $COLOR"$1"$RESET
}

# locate command or abort
function require_command {
    local command_name=$1
    locate_command=$(command -v $command_name)
    if [ $? != 0 ]; then
        print "The installation script requires the $command_name command\n" $WARNING
        print "Aborting installation\n"
        exit 1
    fi
}

# MAIN
if [[ "$EUID" == "0" ]]; then
   print "This script cannot be run as root\n" $WARNING
   exit 1
fi

# require curl and unzip
require_command curl
require_command unzip

# process options
mode="install"
verbose="true"
while (( $# > 0 )); do
    case "$1" in
        --pre-release)
            GET_PRE_RELEASE="true"
            ;;
        --update)
            mode="update"
            verbose="false"
            ;;
        --installation-dir)
            INSTALLATION_DIR="true"
            TST_DIR=$2
            shift
            ;;
        --*)
            print "invalid option $1\n" $WARNING
            exit 1
            ;;
    esac
    shift
done

# set releases url
print "Starting tst install/update\n"
if [ "$GET_PRE_RELEASE" == "true" ]; then
    releases_url='https://api.github.com/repos/daltonserey/tst/releases'
    [[ "$verbose" == "true" ]] && print "* fetching development pre-release information\n"
else
    releases_url='https://api.github.com/repos/daltonserey/tst/releases/latest'
    [[ "$verbose" == "true" ]] && print "* fetching latest release information\n"
fi

# download releases info and parse tag_name and zipball_url
releases=$(curl -q $releases_url 2> /dev/null)
if [[ $? != 0 ]]; then
    print "Couldn't download release information\n" $WARNING
    print "Installation aborted\n"
    exit 1
fi
tag_name=$(echo -e "$releases" | grep "tag_name" | cut -f 4 -d '"' | head -1)
zipball_url=$(echo -e "$releases" | grep "zipball_url" | cut -f 4 -d '"' | head -1)

# cancel installation if there's no release available
if [ "$tag_name" == "" ]; then
    print "No release available\n" $WARNING
    print "Installation canceled\n" $IMPORTANT
    exit 1
fi

# in install mode, check for previous installation
if [[ "$mode" == "install" ]] && [[ -d "$TST_DIR" ]]; then
    print "An installation of tst was found\n" $IMPORTANT
    print "Overwrite? (y/n) " $QUESTION
    get_yes_or_no
    if [ "$answer" == "n" ]; then
        print "Installation cancelled by user\n"
        exit 0
    fi
fi

# create and cd to new installation dir
if [[ -d "$INSTALL_DIR" ]]; then
    [[ "$verbose" == "true" ]] && print "* deleting files from previous installation attempt\n" $WARNING
    rm -rf $INSTALL_DIR
fi
mkdir -p $INSTALL_DIR
cd $INSTALL_DIR

# download latest release into INSTALL_DIR
[[ "$verbose" == "true" ]] && print "* downloading release zip\n"
curl -q -Lko tst.zip $zipball_url &> $INSTALL_DIR/log
if [[ $? != 0 ]]; then
    rm -rf $INSTALL_DIR
    echo $zipball_url
    print "Couldn't download release zip\n" $WARNING
    print "Temporary files deleted\n"
    print "Installation aborted\n"
    exit 1
fi

# unzip tst scripts
[[ "$verbose" == "true" ]] && print "* unzipping and installing tst scripts\n"
unzip -q tst.zip

# create TST_DIR if it doesn't exist
mkdir -p $TST_DIR

# install tst files
mkdir -p $TST_DIR/bin
mv daltonserey-tst*/bin/* $TST_DIR/bin/
mkdir -p $TST_DIR/commands
mv daltonserey-tst*/commands/* $TST_DIR/commands/
mkdir -p $TST_DIR/etc
mv daltonserey-tst*/etc/* $TST_DIR/etc/
mv daltonserey-tst*/CHANGELOG.md $TST_DIR/
mv daltonserey-tst*/README.md $TST_DIR/
mv daltonserey-tst*/LICENSE $TST_DIR/

# update release.json in TST_DIR
cd $TST_DIR
echo "{\"tag_name\": \"$tag_name\"}" > $TST_DIR/release.json

# finish installation
rm -rf $INSTALL_DIR
print "Installation finished\n" $IMPORTANT

# end script if this is an update
[[ "$mode" == "update" ]] && exit 0


# The remaining of this script is for full installations

# delete/rename previous installation
OLD_TST=~/tst
if [[ -d "$OLD_TST" ]]; then
    print "\nWe found what seems to be an older installation.\n" $IMPORTANT
    print "$OLD_TST\n" $WARNING
    print "Delete? (y/n) " $QUESTION
    get_yes_or_no
    [[ "$answer" == "y" ]] && rm -rf $OLD_TST
fi

# configure environment
print "\nConfigure environment? (y/n) " $QUESTION
get_yes_or_no
if [[ "$answer" == "y" ]]; then
    $TST_DIR/etc/setenv.sh
    print "\nRemember that to use tst immediately, you must, either:\n" $IMPORTANT
    print "- type the command:$IMPORTANT source ~/.bashrc\n"
    print "  or\n"
    print "- close the current shell and open a new one.\n"
else
    print "Environment was$WARNING not$NORMAL configured.\n"
    print "Remember to add $IMPORTANT$TST_DIR/bin$NORMAL to PATH and PYTHONPATH\n"
fi
