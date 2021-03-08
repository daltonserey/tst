from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import hashlib
import io
import os
import sys

import tst
from tst.utils import data2json, _assert, cprint
from tst.colors import *
from tst.jsonfile import JsonFile

def main():
    _assert(len(sys.argv) in [3, 4], 'Usage: tst commit [--support-file|-s] <filename>')
    _assert(os.path.exists('.tst/assignment.json'), 'No tst assignment found')
    filetype = 'support' if sys.argv[2] in ['--support-file', '-s'] else 'answer'
    filename = sys.argv[3 if filetype == 'support' else 2]
    assignment_id = JsonFile('.tst/assignment.json')['iid']
    site = tst.get_site('_DEFAULT')
    commit(filename, filetype, assignment_id, site)


def read_mode(filename):
    return "rw"


def read_content(filename):
    with io.open(filename, encoding='utf-8') as f:
        content = f.read()

    return content


def commit(filename, filetype, key, site):
    content = read_content(filename)
    checksum = hashlib.sha1(content.encode('utf-8')).hexdigest()
    data = {
        "files": [{
                "name": filename,
                "content": content,
                "mode": read_mode(filename),
                "category": "public",
                "type": filetype,
                "hash": checksum
            }],
        "hash": checksum
    }

    response = site.send_answer(data, key)
    if response.ok:
        cprint(LGREEN, 'File saved successfully')
    elif response.status_code == 401:
        cprint(LRED, 'Commit failed (%s)' % response.status_code)
        cprint(LRED, 'run: tst login')
    elif response.status_code == 412:
        cprint(LRED, 'Commit failed (%s)' % response.status_code)
        cprint(LRED, 'Error: %s' % response.json()['messages'][0])
    else:
        cprint(LRED, 'Commit failed (%s)' % response.status_code)
        cprint(LRED, 'Error: %s' % response.json()['messages'][0])
