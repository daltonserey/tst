from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import tst
import sys

from tst.colors import *
from tst.utils import cprint
from tst.jsonfile import JsonFile

def main():
    ls(sys.argv)


def ls(args):
    """list files in activity"""

    tstjson = JsonFile('.tst/tst.json')
    files = tstjson.setdefault('files', {})
    for fn in sorted(files.keys()):
        visibility = files[fn].get('category', 'private')
        print(fn, ("(%s)" % visibility if visibility == 'public' else ''))
