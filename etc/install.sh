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
#       tst. This mode is used by the tst update command.
#
# --non-interactive
#       Install tst in non-interactive mode, configure the
#       environment and delete old installations of tst.
#
# --root
#       Force installation as root user.
#
# --installation-dir <dir>
#       Install the new version into <dir>.

# constants
INSTALL_DIR=~/.tst.install
TST_DIR=~/.tst
CONFIG_FILE=~/.tst/config.json

# colors
LGRAY="\033[0;37m"
LRED="\033[1;31m"
LBLUE="\033[1;34m"
LGREEN="\033[1;32m"

# semantic colors
RESET="\033[0m"
NORMAL=$LGRAY
WARNING=$LRED
IMPORTANT=$LBLUE
QUESTION=$LGREEN

# print with color
function print {
    COLOR=$2
    if [[ "$COLOR" == "" ]]; then
        COLOR=$NORMAL
    fi

    echo -n -e $COLOR"$1"$RESET
}

# read either 'y' or 'n' from keyboard
function get_yes_or_no {
    if [[ "$interactive" == "false" ]]; then
        answer="y"
        return
    fi

    while true; do 
        read -s -n 1 answer
        [[ "$answer" == "y" ]] && break
        [[ "$answer" == "n" ]] && break
    done
    echo $answer
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
if [[ "$EUID" == "0" ]] && [[ "$root" != "true" ]]; then
   print "This script cannot be run as root\n" $WARNING
   exit 1
fi

# require curl and unzip
require_command curl
require_command unzip

# process options
mode="installation"
verbose="true"
interactive="true"
while (( $# > 0 )); do
    case "$1" in
        --pre-release)
            GET_PRE_RELEASE="true"
            ;;
        --root)
            root="true"
            verbose="false"
            ;;
        --update)
            mode="update"
            verbose="false"
            ;;
        --non-interactive)
            interactive="false"
            verbose="false"
            ;;
        --*)
            print "invalid option $1\n" $WARNING
            exit 1
            ;;
    esac
    shift
done

# set releases url
print "Starting tst $mode\n" $IMPORTANT
if [ "$GET_PRE_RELEASE" == "true" ]; then
    releases_url='https://api.github.com/repos/daltonserey/tst/releases'
    [[ "$verbose" == "true" ]] && print "* cheking available releases\n"
else
    releases_url='https://api.github.com/repos/daltonserey/tst/releases/latest'
    [[ "$verbose" == "true" ]] && print "* fetching latest release information\n"
fi

# download releases info and parse tag_name and zipball_url
releases=$(curl -q $releases_url 2> /dev/null)
if [[ $? != 0 ]]; then
    print "Couldn't download release information\n" $WARNING
    print "$mode aborted\n"
    exit 1
fi
tag_name=$(echo -e "$releases" | grep "tag_name" | cut -f 4 -d '"' | head -1)
zipball_url=$(echo -e "$releases" | grep "zipball_url" | cut -f 4 -d '"' | head -1)

# cancel installation if there's no release available
if [[ "$tag_name" == "" ]]; then
    print "No release available\n" $WARNING
    print "$mode canceled\n" $IMPORTANT
    exit 1
else
    print "Latest available release: $tag_name\n" $IMPORTANT
fi

# if in installation mode, check for previous installation
if [[ "$mode" == "installation" ]] && [[ -d "$TST_DIR" ]]; then
    print "\nAn installation of tst was found\n" $WARNING
    print "Overwrite? (y/n) " $QUESTION
    get_yes_or_no
    if [ "$answer" == "n" ]; then
        print "$mode cancelled by user\n"
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
[[ "$verbose" == "true" ]] && print "* downloading $tag_name zip\n"
curl -q -Lko tst.zip $zipball_url &> $INSTALL_DIR/log
if [[ $? != 0 ]]; then
    rm -rf $INSTALL_DIR
    echo $zipball_url
    print "Couldn't download release zip\n" $WARNING
    print "Temporary files deleted\n"
    print "$mode aborted\n"
    exit 1
fi

# unzip tst scripts
[[ "$verbose" == "true" ]] && print "* unzipping installation files\n"
unzip -q tst.zip

# install tst
[[ "$verbose" == "true" ]] && print "* installing tst scripts\n"
mkdir -p $TST_DIR
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

# finish installation/update
rm -rf $INSTALL_DIR
print "Finished $mode\n" $IMPORTANT

# remove old abolished commands
rm -f $TST_DIR/commands/tst-commit2
rm -f $TST_DIR/commands/tst-checkout2
rm -f $TST_DIR/commands/tst-assign
rm -f $TST_DIR/commands/*~

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
    print "Finished environment configuration\n" $IMPORTANT
    print "\nTo make configuration take effect immediately, type the command:\n"
    print "*$IMPORTANT source ~/.bashrc$NORMAL\n"
else
    print "Environment was$WARNING not$NORMAL configured.\n"
    print "Remember to add $IMPORTANT$TST_DIR/bin$NORMAL to PATH and PYTHONPATH\n"
fi
