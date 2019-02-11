from __future__ import print_function

import sys
import os
import codecs
import glob
import datetime as dt

from jsonfile import JsonFile
from colors import *
from data2json import *
from utils import cprint, _assert

TSTCONFIG = os.path.expanduser('~/.tst/config.json')

def get_config(writable=False):
    return JsonFile(TSTCONFIG, writable=writable)


def read_specification(filename=None, verbose=False):
    # deal with a custom specification file name
    if filename:
        _assert(os.path.exists(filename), "File %s not found" % filename)
        cprint(LCYAN, "Reading specification file: %s" % filename)
        return JsonFile(filename, array2map="tests")

    # deal with default specification file names
    tstyaml_exists = os.path.exists('tst.yaml')
    tstjson_exists = os.path.exists('tst.json')
    if verbose and tstyaml_exists and tstjson_exists:
        cprint(YELLOW, "Using tst.yaml as specification file")

    if tstyaml_exists:
        try:
            specification = JsonFile('tst.yaml', array2map="tests")
        except:
            _assert(False, "Invalid tst.yaml file")
        return specification

    elif tstjson_exists:
        try:
            specification = JsonFile('tst.json', array2map="tests")
        except:
            _assert(False, "Invalid tst.json file")
        return specification

    # neither tst.yaml, nor tst.json exist
    candidates = glob.glob("*.yaml")
    if len(candidates) == 0:
        candidates = glob.glob("*.json")

    if len(candidates) == 1:
        cprint(YELLOW, "Using %s as specification file" % candidates[0])
        try:
            specification = JsonFile(candidates[0], array2map="tests")
        except:
            _assert(False, "Invalid specification file")
        return specification

    cprint(YELLOW, "Cannot determine specification file")
    _assert(False, "Use --spec-file to indicate specification file")
    


def save_assignment(activity, dir_name, etag, url, repo):

    # move into directory
    os.chdir(dir_name)

    # save the original activity data
    dirname = './.tst' 
    if not os.path.exists(dirname):
        os.makedirs(dirname)

    with codecs.open('./.tst/activity.json', mode='w', encoding='utf-8') as f:
        f.write(data2json({
            "url": url,
            "name": activity.get('name'),
            "activity": activity,
            "etag": etag,
            "repo": repo,
            "updated_at": dt.datetime.utcnow().isoformat().split(".").pop(0) + "Z"
        }))

    # save activity files
    files = activity['files']
    for file in files:
        if os.path.exists(file['name']):
            contents = open(file['name']).read().decode('utf-8')
            if contents != file['data']:
                cprint(LRED, "skipping modified file: '%s' (use --overwrite)" % file['name'])
            else:
                cprint(RESET, "skipping unmodified file: '%s'" % file['name'])
            continue

        try:
            with codecs.open(file['name'], mode='w', encoding='utf-8') as f:
                f.write(file['data'])
            cprint(LCYAN, "Adding file '%s'" % file['name'])
        except:
            print("tst: fatal: Can't save file '%s'" % file['name'], file=sys.stderr)
            sys.exit(1)
