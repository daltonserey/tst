# This module imports all properties of the file undertest and makes them
# available under a uniform name. Of course, this is useful only for python
# code and for script based testing (in particular, to unittest and pytest
# script tests). Python scripts can use this module to access the module
# undertest or a chosen member of the module. The commands below demonstrate
# how to use this module:
#
# - the filename of the module: `from tst.undertest import __filename`
# - the module undertest itself: `from tst.undertest import __module`
# - a named member: `from tst.undertest import <some member>`

import os
import sys
import importlib
import importlib.util
import glob

from tst.utils import data2json as __data2json
from tst.utils import __is_test_file


def __get_filename(candidates):
    global __error, __cline_target

    try:
        i_tst_option = sys.argv.index("--tst")
    except ValueError:
        i_tst_option = None

    if i_tst_option is not None \
       and i_tst_option < len(sys.argv) - 1 \
       and os.path.exists(sys.argv[i_tst_option + 1]):
        __cline_target = True
        return sys.argv[i_tst_option + 1]

    elif len(candidates) == 0:
        __error = "no file to test"
        return None

    elif len(candidates) > 1:
        __error = "multiple files to test"
        return None

    __cline_target = False
    return candidates[0]


def __import__module(filename):
    global __error

    if not filename:
        return None

    module_name = filename.split(".py")[0].replace("/", ".")
    try:
        #module0 = importlib.import_module(module_name)
        spec = importlib.util.spec_from_file_location(module_name, filename)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

    except ModuleNotFoundError as e:
        print(f"ERROR: cannot import {module_name}", file=sys.stderr) 
        print(e, file=sys.stderr) 
        print(os.getcwd(), file=sys.stderr) 
        __error = f"cannot import {module_name}"
        return None
        #raise Exception(f"oops: cannot import {module_name}")
        
    except Exception as e:
        print(f"ERROR: cannot import {module_name}", file=sys.stderr) 
        print(e, file=sys.stderr) 
        print(os.getcwd(), file=sys.stderr) 
        __error = f"cannot import {module_name}: {e}"
        return None
        #raise Exception(f"oops: cannot import {module_name}")

    for e in dir(module):
        if not e.startswith('__'):
            globals()[e] = getattr(module, e, None)

    return module


__error = None
__cline_target = False
__candidates = [fn for fn in glob.glob("*.py") if not __is_test_file(fn)]
__filename = __get_filename(__candidates)
__module = __import__module(__filename)
__test_files = [fn for fn in glob.glob("*") if __is_test_file(fn)]
__cline_files = [fn for fn in sys.argv[1:] if os.path.exists(fn)]

if __name__ == '__main__':
    data = {
        "__cline_target": __cline_target,
        "__candidates": __candidates,
        "__filename": __filename,
        "__test_files": __test_files,
        "__error": __error,
        "__cline_target": __cline_target,
        "__candidates": __candidates,
        "__filename": __filename,
        "__module": bool(__module),
        "__test_files": __test_files,
        "__cline_files": __cline_files,
    }

    print(__data2json(data))
