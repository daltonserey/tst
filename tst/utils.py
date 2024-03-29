from builtins import str

import sys
import string
import json
import logging

from .colors import *

def cprint(color, msg, file=sys.stderr, end='\n'):
    if type(msg) is str:
        data = msg
    # 2to3: elif type(msg) is str:
    elif isinstance(msg, str):
        data = msg.__str__()
    else:
        data = str(msg)

    print(color + data + RESET, file=file, end=end)


def _assert(condition, msg):
    if condition:
        return

    cprint(LRED, msg)
    logging.error(msg)
    sys.exit(1)


def to_unicode(obj, encoding='utf-8'):
    # 2to3: assert isinstance(obj, basestring), type(obj)
    #assert isinstance(obj, str), type(obj)
    if isinstance(obj, str):
        return obj

    for encoding in ['utf-8', 'latin1']:
        try:
            obj = str(obj, encoding)
            return obj
        except UnicodeDecodeError:
            pass

    assert False, "tst: non-recognized encoding"
