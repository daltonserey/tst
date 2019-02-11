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
