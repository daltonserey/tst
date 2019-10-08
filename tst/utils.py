from __future__ import print_function

import sys
import string
import json
import logging

from colors import *


def is_posix_filename(name, extra_chars=""):
    CHARS = string.letters + string.digits + "._-" + extra_chars
    return all(c in CHARS for c in name)


def cprint(color, msg, file=sys.stderr, end='\n'):
    if type(msg) is unicode:
        data = msg
    elif type(msg) is str:
        data = msg.__str__()
    else:
        data = str(msg)

    print(color + data + RESET, file=file, end=end)


def _assert(condition, msg):
    if condition:
        return

    cprint(LRED, msg)
    logging.error(msg)
    sys.exit(1)


def to_unicode(obj, encoding='utf-8'):
    assert isinstance(obj, basestring), type(obj)
    if isinstance(obj, unicode):
        return obj

    for encoding in ['utf-8', 'latin1']:
        try:
            obj = unicode(obj, encoding)
            return obj
        except UnicodeDecodeError:
            pass

    assert False, "tst: non-recognized encoding"


def data2json(data):
    def date_handler(obj):
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        elif hasattr(obj, 'email'):
            return obj.email()

        return obj

    return json.dumps(
        data,
        default=date_handler,
        indent=2,
        separators=(',', ': '),
        sort_keys=True,
        ensure_ascii=False)
