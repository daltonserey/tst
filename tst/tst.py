from builtins import str

import sys
import os
import io
import json
import glob
import pkg_resources
import logging

from .jsonfile import JsonFile, CorruptedJsonFile
from .colors import *
from .utils import cprint, _assert

CONFIGDIR = os.path.expanduser('~/.tst/')
LOG_FILE = os.path.expanduser('~/.tst/logs.txt')
CONFIGFILE = CONFIGDIR + 'config.yaml'

def coverit():
    return 1

def get_config():
    if not os.path.exists(CONFIGFILE):
        if not os.path.isdir(CONFIGDIR):
            os.mkdir(CONFIGDIR)

        with io.open(CONFIGFILE, encoding="utf-8", mode="w") as config_file:
            config_file.write(
                "run:\n"
                "  py: python3\n"
                "  py2: python2\n"
                "  js: node\n"
                "  mjs: node\n"
            )

    if not os.path.exists(LOG_FILE):
        open(LOG_FILE, 'w').close()
    logging.basicConfig(filename=LOG_FILE, level=logging.DEBUG, format='%(asctime)s (%(levelname)s@%(name)s) %(message)s', datefmt='%Y-%m-%dT%H:%M:%S')

    return JsonFile(CONFIGFILE)


def read_specification(verbose=False):
    # deal with default specification file names
    tstyaml_exists = os.path.exists('tst.yaml')
    tstjson_exists = os.path.exists('tst.json')
    if verbose and tstyaml_exists and tstjson_exists:
        cprint(YELLOW, "Found both tst.yaml and tst.json: using tst.yaml")

    if tstyaml_exists:
        try:
            specification = JsonFile('tst.yaml', array2map="tests")
        except CorruptedJsonFile:
            _assert(False, "Corrupted specification file")
        return specification

    elif tstjson_exists:
        try:
            specification = JsonFile('tst.json', array2map="tests")
        except CorruptedJsonFile:
            _assert(False, "Corrupted specification file")
        return specification

    return {}
