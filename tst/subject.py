# This module imports all properties of the file undertest and makes them
# available under a common name. This is usefull when subjects have different
# designs and (python) script tests rely on specific elements (like functions)
# being present in the subject. A Python script test can use "from tst.subject
# import <something>" to access functions within the module, for instance.

import os
import sys

filename = sys.argv[-1]
if os.path.exists(filename):
    module = sys.argv[-1].split(".py")[0]
    undertest = __import__(module)
    for e in dir(undertest):
        if not e.startswith('__'):
            globals()[e] = getattr(undertest, e, None)
