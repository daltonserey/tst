# TST

TST is a set of command line tools used to create and run
automated tests of programming assignments in introductory
programming courses. TST supports both input/output and script
based tests. While TST is primarily focused on python
programming, we have successfully used it for Java and Javascript
(node.js) programming assignments as well.

TST command line tools also serves as the CLI client for the TST
Online service --- a service that supports the cooperative study
and learn of programming.

These scripts are supposed to be installed and used by both
students and instructors.


## License

This software is licensed under the terms of the AGPL 3.0
license. Please read the LICENSE file.


## Documentation

To be written.


## Dependencies

These scripts depend on Python 2.7 and on Bash. The scripts were
developed to be used primarily in a bash shell. While they have
been developed with a unix like environment in mind (Linux or
OSX), some users have reported they have been able to use TST in
Windows, using Cygwin.


## Installation

TST is a simple set of scripts. The commands below run an
interactive script that downloads and install tst command line
tools. It also assists the user to configure the shell
environment to make it easier to use tst.

### Latest release

    $ bash -c "$(curl -q -sSL https://raw.githubusercontent.com/daltonserey/tst/master/etc/install.sh)"
    $ bash -c "$(curl -q -sSL http://bit.ly/tst-install)"


### Development pre-release

    $ bash -c "$(curl -q -sSL https://raw.githubusercontent.com/daltonserey/tst/develop/etc/install.sh)" -s --development-version
    $ bash -c "$(curl -q -sSL http://bit.ly/2bEBWho)" -s --development-version
