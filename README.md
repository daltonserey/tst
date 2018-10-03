# TST

TST is a set of command line tools to automate testing and
verification of programming exercises. TST supports both
input/output and script based tests. While TST is primarily
focused on python programming, it has been successfully used with
Java and Javascript (node.js) programming assignments.

TST command line tools also help the creation of programming
exercises that can be deployed to the web.

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

TST is a simple set of Python modules and scripts. The source
code is kept in github and public packages are deployed to
pypi.org. To install tst, use `pip` according to the command
below -- observe that `tst` is supposed to be installed as a
normal user, not as root.

    $ pip install tst --user

### Uninstall an older version

If you have an older version of `tst` installed, you should
uninstall it before installing the current version. To do so, you
should: 1) remove the `~/.tst` directory; and 2) remove the
configuration lines from `~/.bashrc` or `~/.profile`. If you
don't know how to do it yourself, run the following command.It
uses `curl` to download a little script that does the two steps
above in bash (in fact, the configuration lines are not deleted;
they are only commented out).
 
```bash
$ bash -c "$(curl -q -sSL http://bit.ly/tst084-uninstall)"
```
