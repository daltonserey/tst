import tst
import sys

from tst.colors import *
from tst.utils import cprint

def main():
    cprint(LGREEN, tst.dirtype() or "no tst directory")
    print "Script executed: " + sys.argv[0]
