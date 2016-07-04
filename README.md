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

This software is licensed under the terms of the MIT license.
Please read the LICENSE.md file.


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
the PATH. Running command below, TST will be downloaded
and installed in the `~/.tst` directory and put that directory in
your `~/.profile`.

    $ curl -sSL http://tst-online.appspot.com/tst | bash
