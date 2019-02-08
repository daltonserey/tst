from __future__ import print_function

import sys

from colors import *

def cprint(color, msg, file=sys.stdout):
    print(color + msg + RESET, file=file)


def _assert(condition, msg):
    if condition:
        return

    cprint(LRED, msg)
    sys.exit(1)
