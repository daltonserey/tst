# TST

TST is a set of command line tools used to create and run
automated tests of programming assignments in introductory
programming courses. TST supports both input/output and script
based tests. While TST is primarily focused on python
programming, we have used it for Java and Javascript (node.js)
programming assignments as well.

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

These scripts depend on Python 2.7. The scripts were developed to
be used in a bash shell. While they have been developed with a
unix like environment in mind (Linux or OSX), users have reported
they have been able to use TST in Windows, using Cygwin.


## Installation

TST is a simple set of scripts. All you need is to copy all
scripts in a directory in your system and puth the directory in
the PATH. The command below, downloads and installs tst command
line tools. It also helps you to configure your shell environment
to make it easier to use tst.

    $ curl -q -sSL https://raw.githubusercontent.com/daltonserey/tst/master/etc/install.sh | bash
    $ curl -q -sSL http://bit.ly/tst-install | bash

To download a development pre-release, use the command below.

    $ curl -q -sSL https://raw.githubusercontent.com/daltonserey/tst/develop/etc/install.sh | bash -s --development-version
    $ curl -q -sSL http://bit.ly/tst-dev-install | bash -s --development-version
