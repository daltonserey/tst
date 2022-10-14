from builtins import str

import sys
import os
import io
import json
import pkg_resources
import logging
import subprocess

from .jsonfile import JsonFile, CorruptedJsonFile
from .colors import *
from .utils import cprint, _assert

CONFIGDIR = os.path.expanduser('~/.tst/')
LOG_FILE = os.path.expanduser('~/.tst/logs.txt')
CONFIGFILE = CONFIGDIR + 'config.yaml'

def coverit():
    return 1


def run_test(subjects, test_suite, include_stderr=True, timeout=120):
    command = f"tst -T {timeout} -f json -t {test_suite} -- {' '.join(subjects)}"
    try:
        if include_stderr:
            stderr = subprocess.STDOUT
        else:
            stderr = subprocess.DEVNULL
        output = subprocess.check_output(command.split(), stderr=stderr)
        results = json.loads(output)
        return [results.get(s, {}) for s in subjects]

    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        print("----- error running tst -----")
        print(e)
        print("-----------------------------")
        raise e
        

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


def read_specification():
    # default specification
    spec = {
        "extensions": ["py"], # deprecated
        "require": [],
        "filenames": "*.py",
        "subjects": "*.py",
        "ignore": ["tst.yaml", "tst.json", "*_tests.yaml", "*_tests.py", "test_*.py", "*_test.py"],
        "test-command": { ".py": "python3" }
    }

    config = get_config()
    spec.update(config.data)

    try:
        tstjson = JsonFile('tst.json', array2map="tests")
        spec.update(tstjson.data)
    except CorruptedJsonFile:
        _assert(False, "Corrupted specification file: tst.json")

    try:
        tstyaml = JsonFile('tst.yaml', array2map="tests")
        spec.update(tstyaml.data)
    except CorruptedJsonFile:
        _assert(False, "Corrupted specification file: tst.yaml")

    # validate spec
    _assert(type(spec["require"]) is list, "require must be a list of strings")
    _assert(all(type(e) is str for e in spec["require"]), "require elements must be strings")
    _assert(type(spec["subjects"]) is str, "subjects must be a glob pattern")
    _assert(type(spec["ignore"]) is list, "ignore must be a list of strings")
    _assert(all(type(e) is str for e in spec["ignore"]), "ignore elements must be strings")

    return spec
