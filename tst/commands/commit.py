import hashlib
import codecs
import os
import sys

import tst
from tst.utils import data2json, _assert
from tst.jsonfile import JsonFile

def main():
    _assert(len(sys.argv) == 3, 'Usage: tst commit <filename>')
    _assert(os.path.exists('.tst/assignment.json'), 'No tst assignment found')
    filename = sys.argv[2]
    assignment_id = JsonFile('.tst/assignment.json')['iid']
    site = tst.get_site('prog1')
    commit(filename, assignment_id, site)


def read_mode(filename):
    return "rw"


def read_content(filename):
    with codecs.open(filename, encoding='utf-8') as f:
        content = f.read()

    return content


def commit(filename, key, site):
    content = read_content(filename)
    data = {
        "files": [
            {
                "name": filename,
                "content": content,
                "mode": read_mode(filename),
                "category": "public",
                "hash": hashlib.sha1(content).hexdigest()
            }
        ],
        "hash": hashlib.sha1(content).hexdigest()
    }

    response = site.send_answer(data, key)
    if response.ok:
        cprint(LGREEN, 'File saved successfully')
    else:
        cprint(LRED, 'Commit failed (%s)' % response.status_code)
