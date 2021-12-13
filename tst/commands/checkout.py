import sys

from tst.colors import *
from tst.utils import cprint

def main():
    cprint(LRED, "tst: checkout command is deprecated")
    sys.exit(1)
