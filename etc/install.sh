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
UPDATE="false"

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
    COLOR=$2
    if [ "$COLOR" == "" ]; then
        COLOR=$NORMAL
    fi

    echo -n -e $COLOR"$1"$RESET
}


# MAIN
if [[ "$EUID" == "0" ]]; then
   print "This script cannot be run as root\n" $WARNING
   exit 1
fi

# process options
while (( $# > 0 )); do
    case "$1" in
        --pre-release)
            DOWNLOAD_DEV_VERSION="true"
            ;;
        --update)
            UPDATE="true"
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

# require curl or abort
CURL=$(command -v curl)
if [ $? != 0 ]; then
    print "The installation script requires the curl command" $WARNING
    print "Aborting installation"
    exit 1
fi

# require unzip or abort
UNZIP=$(command -v unzip)
if [ $? != 0 ]; then
    print "The installation script requires the unzip command" $WARNING
    print "Aborting installation";
    exit 1
fi

# identify releases url
if [ "$DOWNLOAD_DEV_VERSION" == "true" ]; then
    RELEASES_URL='https://api.github.com/repos/daltonserey/tst/releases'
    if [ "$UPDATE" == "false" ]; then
        print "* fetching development pre-release information\n"
    fi
else
    RELEASES_URL='https://api.github.com/repos/daltonserey/tst/releases/latest'
    if [ "$UPDATE" == "false" ]; then
        print "* fetching latest release information\n"
    fi
fi

# download releases info: identify tag_name and zipball_url
RELEASES=$(curl -q $RELEASES_URL 2> /dev/null)
if [ $? != 0 ]; then
    print "Couldn't download release information\n" $WARNING
    print "Installation aborted\n"
    exit 1
fi
TAG_NAME=$(echo -e "$RELEASES" | grep "tag_name" | cut -f 4 -d '"' | head -1)
ZIPBALL_URL=$(echo -e "$RELEASES" | grep "zipball_url" | cut -f 4 -d '"' | head -1)

# cancel installation if there's no release available
if [ "$TAG_NAME" == "" ]; then
    print "No release available\n" $WARNING
    print "Installation canceled\n" $IMPORTANT
    exit 1
fi

# create TST_DIR if it doesn't exist
mkdir -p $TST_DIR

# check for previous installation version
if [ -f "$TST_DIR/release.json" ]; then
    PREVIOUS_TAG_NAME=$(cat $TST_DIR/release.json | grep "tag_name" | cut -f 4 -d '"')

    # notify user about previous installation
    if [ "$PREVIOUS_TAG_NAME" == "$TAG_NAME" ]; then
        print "Installed tst is up-to-date (version $TAG_NAME)\n" $IMPORTANT
        exit
    else
        print "New version of tst available (version $TAG_NAME)\n" $IMPORTANT
    fi

    if [ "$UPDATE" == "false" ]; then
        # ask user whether to proceed and overwrite installation
        print "Proceed and overwrite? (y/n) " $QUESTION
        get_yes_or_no
        if [ "$ANSWER" == "n" ]; then
            print "Installation cancelled by user\n" $IMPORTANT
            exit 0
        fi
    fi
fi

# create new installation dir
if [ -d "$INSTALL_DIR" ]; then
    if [ "$UPDATE" == "false" ]; then
        print "* deleting failed attempt to install" $WARNING 
    fi
    rm -rf $INSTALL_DIR
fi
mkdir -p $INSTALL_DIR

# download latest release into INSTALL_DIR
cd $INSTALL_DIR
if [ "$UPDATE" == "false" ]; then
    print "* downloading release zip\n"
fi
curl -q -Lko tst.zip $ZIPBALL_URL 2> /dev/null
if [ $? != 0 ]; then
    rm -rf $INSTALL_DIR
    echo $ZIPBALL_URL
    print "Couldn't download release zip\n" $WARNING
    print "Installation aborted\n"
    print "Temporary files deleted\n"
    exit 1
fi

# unzip and install tst scripts within INSTALL_DIR
if [ "$UPDATE" == "false" ]; then
    print "* unzipping and installing tst scripts\n"
fi
unzip -q tst.zip
rm tst.zip

# install files in TST_DIR
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
echo "{\"tag_name\": \"$TAG_NAME\"}" > $TST_DIR/release.json

# end installation
rm -rf $INSTALL_DIR
print "Installation finished\n" $IMPORTANT

# configure environment if in interactive mode
if [ "$UPDATE" == "false" ]; then
    print "\nConfigure environment? (y/n) " $QUESTION
    get_yes_or_no
    if [ "$ANSWER" == "y" ]; then
        $TST_DIR/etc/setenv.sh
    else
        print "Environment was$WARNING not $NORMAL configured.\n"
        print "Remember to add $IMPORTANT$TST_DIR/bin $NORMAL to your PATH\n"
        exit
    fi
    print "\nRemember that to use tst immediately, you must, either:\n" $IMPORTANT
    print "- type the command:$IMPORTANT source ~/.bashrc\n"
    print "  or\n"
    print "- close the current shell and open a new one.\n"
fi

# delete/rename previous installation
if [ "$UPDATE" == "false" ]; then
    OLD_TST=~/tst
    if [ -d "$OLD_TST" ]; then
        print "\nWe found what seems to be an older installation.\n" $IMPORTANT
        print "$OLD_TST\n" $WARNING
        print "Delete? (y/n) " $QUESTION
        get_yes_or_no
        if [ "$ANSWER" == "y" ]; then
            mkdir -p ~/.old_tst
            mv $OLD_TST ~/.old_tst/
            print "The old directory was moved to ~/.old_tst\n" $IMPORTANT
        fi
    fi
fi
