import sys

from tst.colors import *
from tst.utils import cprint

def main():
    cprint(LRED, "tst: commit command is deprecated")
    sys.exit(1)
