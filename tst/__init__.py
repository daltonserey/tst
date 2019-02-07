from __future__ import print_function
import sys
import os
import codecs
import datetime as dt
from jsonfile import JsonFile

from tstlib import data2json

YELLOW = '\033[1;33m'
LRED = '\033[1;31m'
LGREEN = '\033[1;32m'
GREEN="\033[9;32m"
WHITE="\033[1;37m"
LCYAN = '\033[1;36m'
RESET = '\033[0m'

def cprint(color, msg, file=sys.stdout):
    print(color + msg + RESET, file=file)


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
