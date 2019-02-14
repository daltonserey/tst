from __future__ import print_function

import tst
import sys

from tst.colors import *
from tst.utils import cprint
from jsonfile import JsonFile

def main():
    print("Script executed: " + sys.argv[0])
    ls(sys.argv)

def ls(args):
    """list files in activity"""

    tstjson = JsonFile('.tst/tst.json')
    files = tstjson.setdefault('files', {})
    for fn in sorted(files.keys()):
        visibility = files[fn].get('category', 'private')
        print(fn, ("(%s)" % visibility if visibility == 'public' else ''))


