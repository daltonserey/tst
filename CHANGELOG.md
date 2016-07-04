# Change Log

All relevant changes to this project are documented in this file.


## 0.3.11 - 2015-11-23
### Added

- Added script tst (without '.py'); tst is a commander script
  that allows invoking tst commands as parameters, instead of
  running the scripts directly; it also supports internal
  commands.

## 0.3.10 - 2015-11-15
### Fixed
- tst-commit.py Only refuses to commit if code is equal to last
  commt. Otherwise, it sends the file again, even if it is equal
  to an older version.

## 0.3.9 - 2015-06-04
### Fixed
- tst-checkout.py doesn't register the name of the current file
  in the list of files to avoid testing;

## 0.3.8 - 2015-06-04
### Fixed
- tst_commit.py waits for tests, after warning user he has a
  non updated version of the assignment;

## 0.3.7 - 2015-06-04
### Added
- tst_checkout.py now stores downloaded files data; this allows
  tst_test.py avoid testing unnecessary files; is provided;

### Fixed
- tst_checkout.py now gives a nicer message when an invalid key
  is provided;

## 0.3.6 - 2015-06-04
### Changed

- tst_test.py improved support for script based tests; now the
  protocol requires the script to provide a summary first line,
  an empty second line, and then the feedback; alternatively, a
  json output can be produced, containing properties summary and
  feedback;
  
- tst_test.py verbosity level 0 now reports script subtests
  individually in the summary; io tests summaries are joined at
  the begining of the line, then the summaries for each script
  test is reported; it also reports success/fail; an
  interrogation mark is used as a summary for a test that didn't
  provide a summary report, meaning unknown result;


## 0.3.5 - 2015-05-29
### Added

- tst_checkout.py now downloads all files available in the
  assignment; this allows the user to run script tests, if the
  files are provided;

- tst_test.py now runs script tests if available;

## 0.3.4 - 2015-05-27
### Fixed

- tst_login.py now uses an oauth-like login; not actual oauth,
  however; this fixes the problem with the fact that Google has
  killed ClientLogin;

- tst_checkout.py and tst_commit.py were also updated to use the
  new authentication method;

## 0.3.3 - 2015-05-19
### Added

- tst_checkout.py now stores the stores the semantic version of
  the activity;

- tst_commit.py now uses the activity semantic versioning numbers
  to better inform both the user and the server; if the online
  version number is newer, the user will receive a warning;

### Fixed
- tst_test.py does not crash anymore, when test input is empty;

- tst_checkout.py does not crash anymore, when assignment is not
  open; it has also an improved treatment of the data saved to
  tst.json;

- tst_version.py correctly indicates the version installed;

## 0.3.1 - 2015-05-12
### Fixed
- tst_commit.py now requests test results if the program was
  already uploaded;

- tst_checkout.py now uses key provided in command line even if
  there is a key stored in tst.json;

## 0.3.0 - 2015-05-08
### Added
- tst_test.py Improved command line arguments use --help. Now tst_test.py
  receives filenames as positional arguments. If a single filename is used
  and that file is not found, it is considered as a pattern and all files
  that match that pattern will be tested. This allows the use of wildcard
  expansion by the shell. The 'tst.json' file is never tested.

### Removed

- tst_test.py does not support "-a"/"--all" and "-"/"--stdin" arguments.


## 0.2.0 - 2015-05-03
### Added
- tst_commit.py After commiting file, checks for test results.
- tst_commit.py Shows saved results, if the same program is commited.
- tst_test.py Added a worker verbosity level to reports.

### Fixed
- tst_login.py Doesn't break when there's no internet connection.

### Removed

- tst_test.py Pyunit tests and code analysis support has been
  disabled in this version because they are under redesign. They
  will be enabled in a future version.

## 0.1.2 - 2015-04-29
### Fixed
- tst_commit.py Bug fixed: unicode error when sending unicode.

## 0.1.1 - 2015-04-27
### Fixed
- tst_commit.py Fixed msg show when response indicates error.

## 0.1.0 - 2015-04-27
### Added
- tst_login.py Script that logs users into TST Online.
- tst_checkout.py Script to download problems.
- tst_test.py Script to run TST tests on local directory.
- tst_commit.py Script to commit code to TST Online.
- tst_version.py Script to see version of TST CLI Tools.
- tstlib.py Common facilities for TST CLI tools.
