from __future__ import print_function

import sys

from colors import *


def cprint(color, msg, file=sys.stdout, end='\n'):
    print(color + msg + RESET, file=file, end=end)


def _assert(condition, msg):
    if condition:
        return

    cprint(LRED, msg)
    sys.exit(1)


def to_unicode(obj, encoding='utf-8'):
    assert isinstance(obj, basestring), type(obj)
    if isinstance(obj, unicode):
        return obj

    for encoding in ['utf-8', 'latin1']:
        try:
            obj = unicode(obj, encoding)
            return obj
        except UnicodeDecodeError:
            pass

    assert False, "tst: non-recognized encoding"
