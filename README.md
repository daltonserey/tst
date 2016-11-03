# TST

TST is a set of command line tools used to create and test
programming assignments in introductory programming courses. TST
supports both input/output and script based tests. While TST is
primarily focused on python programming, we have successfully
used it for Java and Javascript (node.js) programming
assignments.

TST command line tools also serves as the CLI client for the TST
Online service --- a service that supports the cooperative study
and learn of programming.


## License

This software is licensed under the terms of the AGPL 3.0
license. Please read the LICENSE file.


## Documentation

To be written.


## Dependencies

These scripts depend on Python 2.7 and on Bash. The scripts were
developed to be used primarily within a bash shell. While they
have been developed to be used in unix like environment in mind
(mostly Linux and OSX), some users have reported they were able
to use TST in Windows, using Cygwin.


## Installation

TST is a simple set of scripts. The commands below download and
run an interactive script that installs and configures tst. These
scripts are supposed to be run by the end user and not by root.
The scripts also assist the user to configure shell environment
variables and completion facilities to make tst more friendly.

### Latest release and pre-release

To install the latest stable release, run the following command.

    $ bash -c "$(curl -q -sSL http://bit.ly/tst-install)"

To install the latest development pre-release, first install
`tst` using the command above and update to the latest
pre-release (see below)

### Update

After tst is installed you can update your installation running
the `tst update` command to update to the latest stable release:

    $ tst update

Use the `--pre-release` option to update to the latest
development pre-release:

    $ tst update --pre-release

