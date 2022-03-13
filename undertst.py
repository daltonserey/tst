# This module identifies the module undertest, imports all its members and
# makes them available under a uniform name. Of course, this is useful only
# when both the code under test and the tests themselves are written in python
# (in particular, this is useful in unittest and pytest script tests). Script
# tests can use this module to access members of the module undertest.
# Members can be imported as shown below:
#
# - import the filename of the module: `from undertst import __filename`
# - the module undertest itself: `from undertst import __undertest`
# - a named member: `from undertst import <a member>`

import sys
import os

def __is_test_file(fn):
    return fn.startswith("test_") and fn.endswith(".py") \
           or fn.endswith("_test.py") \
           or fn.endswith("_tests.py")


def __import_from_filename(filename):
    from importlib.util import spec_from_file_location, module_from_spec
    module_name = filename.split(".py")[0]
    if not os.path.isfile(filename):
        return False
    spec = spec_from_file_location(module_name, filename)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


try:
    tst_option_index = sys.argv.index("--tst")
except ValueError:
    #raise Exception("undertst: no --tst in command line")
    tst_option_index = None

try:
    assert tst_option_index
    __filename = sys.argv[tst_option_index + 1]
    assert os.path.isfile(__filename)
except (IndexError, AssertionError):
    candidates = [f for f in os.listdir() if f.endswith(".py") and not __is_test_file(f)]
    if len(candidates) == 0:
        raise Exception("undertst: no candidate module to test")
    elif len(candidates) > 1:
        raise Exception("undertst: multiple modules to test; use --tst <module>")
    __filename = candidates[0]

__undertest = __import_from_filename(__filename)
if __undertest:
    for member in dir(__undertest):
        globals()[member] = getattr(__undertest, member, None)
