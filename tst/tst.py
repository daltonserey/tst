from __future__ import print_function

import sys
import os
import codecs
import datetime as dt

from jsonfile import JsonFile
from colors import *
from data2json import *
from utils import cprint

TSTCONFIG = os.path.expanduser('~/.tst/config.json')

def get_config(writable=False):
    return JsonFile(TSTCONFIG, writable=writable)


def get_context(filename=None):
    if filename:
        _assert(os.path.exists(filename), "File %s not found" % filename) 
        spec_filename = filename

    elif os.path.exists('tst.yaml'):
        spec_filename = 'tst.yaml'

    elif os.path.exists('tst.json'):
        spec_filename = 'tst.json'

    else:
        return None

    return JsonFile(spec_filename)


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
