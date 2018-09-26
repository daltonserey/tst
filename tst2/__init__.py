from __future__ import print_function
import sys
import os
import codecs
import datetime as dt
from jsonfile import JsonFile

from tstlib import data2json
from tst import cprint, LRED, LCYAN, WHITE, RESET

def save_assignment(assignment, dir_name, etag, url, repo):

    # move into directory
    os.chdir(dir_name)

    # save the original assignment data
    dirname = './.tst' 
    if not os.path.exists(dirname):
        os.makedirs(dirname)

    with codecs.open('./.tst/assignment.json', mode='w', encoding='utf-8') as f:
        f.write(data2json({
            "url": url,
            "name": assignment.get('name'),
            "assignment": assignment,
            "etag": etag,
            "repo": repo,
            "updated_at": dt.datetime.utcnow().isoformat().split(".").pop(0) + "Z"
        }))

    # save assignment files
    files = assignment['files']
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
