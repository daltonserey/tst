from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from builtins import str

import sys
import string
import json
import logging

from .colors import *


def indent(text):
    lines = text.splitlines()
    text = "\n".join(["    %s" % l for l in lines])
    return text


def print_hints(hints):
    if hints:
        print(file=sys.stderr)
        for h in hints:
            cprint(LCYAN, indent("(%s)" % h), file=sys.stderr)
        print(file=sys.stderr)


def is_posix_filename(name, extra_chars=""):
    CHARS = string.ascii_letters + string.digits + "._-" + extra_chars
    return all(c in CHARS for c in name)


def cprint(color, msg, file=sys.stderr, end='\n'):
    if type(msg) is str:
        data = msg
    # 2to3: elif type(msg) is str:
    elif isinstance(msg, str):
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
    # 2to3: assert isinstance(obj, basestring), type(obj)
    #assert isinstance(obj, str), type(obj)
    if isinstance(obj, str):
        return obj

    for encoding in ['utf-8', 'latin1']:
        try:
            obj = str(obj, encoding)
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
