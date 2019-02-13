from __future__ import print_function
from __future__ import unicode_literals

import json
import codecs
import os
import sys

from tst.utils import to_unicode

TSTDIR = os.path.expanduser("~/.tst/")
TSTCONFIG = os.path.expanduser(TSTDIR + "config.json")

class Config(object):

    __instance = None
    FLAGS = ['debug']

    def __new__(cls):
        if Config.__instance is not None:
            return Config.__instance

        Config.__instance = object.__new__(cls)
        self = Config.__instance

        # initialization
        self.data = None
        return self

    def __init__(self):
        self.load()

    def __setitem__(self, key, value):
        if self.data is None:
            self.load()

        if key in Config.FLAGS:
            value = boolean(value)
        
        self.data[key] = value

    def __getitem__(self, key):
        if self.data is None:
            self.load()

        return self.data[key]

    def __contains__(self, key):
        if self.data is None:
            self.load()

        return key in self.data

    def load(self, exit_on_fail=False):
        if not os.path.exists(TSTCONFIG):
            self.data = {
                "url": "http://backend.tst-online.appspot.com",
                "ignore_default": [
                    "public_tests.py",
                    "acceptance_tests.py"
                ],
                "run": {
                    "py": "python2.7",
                    "java": "runjava"
                }
            }
            self.save()
            return

        # actually read from file system
        try:
            with codecs.open(TSTCONFIG, mode='r', encoding='utf-8') as f:
                self.data = json.loads(to_unicode(f.read()))

        except ValueError:
            msg = "tst: %s is corrupted" % TSTCONFIG
            if exit_on_fail:
                print(msg, file=sys.stderr)
                sys.exit()

            raise CorruptedFile(msg)

    def save(self):
        if not os.path.exists(TSTDIR):
            os.mkdir(TSTDIR)

        with codecs.open(TSTCONFIG, mode="w", encoding='utf-8') as f:
            f.write(json.dumps(
                self.data,
                indent=2,
                separators=(',', ': ')
            ))

    def pop(self, key):
        if self.data is None:
            self.load()

        self.data.pop(key, None)

    def get(self, key, default=None):
        if self.data is None:
            self.load()

        return self.data.get(key, default)
