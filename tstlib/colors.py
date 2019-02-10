from __future__ import print_function

import sys

YELLOW = '\033[1;33m'
LRED = '\033[1;31m'
LGREEN = '\033[1;32m'
GREEN ="\033[9;32m"
WHITE ="\033[1;37m"
LCYAN = '\033[1;36m'
RESET = '\033[0m'

def cprint(color, msg, file=sys.stdout):
    print(color + msg + RESET, file=file)
