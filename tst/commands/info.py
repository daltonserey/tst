from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import tst
import sys

from tst.colors import *
from tst.utils import cprint

def main():
    cprint(LGREEN, tst.dirtype() or "no tst directory")
    print("Script executed: " + sys.argv[0])
