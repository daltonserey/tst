# jsonfile
# (C) Dalton Serey - UFCG
# gist url: https://gist.github.com/daltonserey/8fc9644cfb9dda7fdfb09a3e006587b3

from __future__ import print_function
from __future__ import unicode_literals

import codecs
import sys
import os
import json

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

class CorruptedJsonFile(Exception): pass

class JsonFile(object):

    __instances = {}

    def __new__(cls, filename, exit_on_fail=False, failmsg=None, array2map=None, writable=False):
        filename = os.path.expanduser(filename)
        if filename in JsonFile.__instances:
            return JsonFile.__instances[filename]

        JsonFile.__instances[filename] = object.__new__(cls)
        self = JsonFile.__instances[filename]
        self.filename = filename
        self.writable = writable
        self.isyaml = filename.endswith("yaml") or filename.endswith("yml")
        
        if os.path.exists(filename):
            self.load(failmsg=failmsg, exit_on_fail=exit_on_fail)
            if array2map and type(self.data) is list:
                self.data = { array2map: self.data }

        else:
            self.data = {}

        return self


    def __setitem__(self, key, value):
        self.data[key] = value


    def __getitem__(self, key):
        return self.data[key]


    def __contains__(self, key):
        return key in self.data


    def pop(self, key):
        self.data.pop(key, None)


    def setdefault(self, key, value):
        return self.data.setdefault(key, value)


    def load(self, exit_on_fail=False, failmsg=None):
        if not os.path.exists(self.filename):
            self.data = {}
            return

        # actually read data from file system
        try:
            if self.isyaml:
                import yaml
                with codecs.open(self.filename, mode='r', encoding='utf-8') as f:
                    self.data = yaml.load(to_unicode(f.read()))
                    if self.data is None:
                        raise ValueError()
            else:    
                with codecs.open(self.filename, mode='r', encoding='utf-8') as f:
                    self.data = json.loads(to_unicode(f.read()))

        except ValueError:
            if exit_on_fail or failmsg:
                failmsg = failmsg or "jsonfile: %s is corrupted" % self.filename
                print(failmsg, file=sys.stderr)
                sys.exit()

            raise CorruptedJsonFile("corrupted json file")


    def save(self):
        assert self.writable, "jsonfile: cannot save a non writable JsonFile"
        with codecs.open(self.filename, mode="w", encoding='utf-8') as f:
            f.write(json.dumps(
                self.data,
                indent=2,
                separators=(',', ': ')
            ))


    def get(self, key, default=None):
        return self.data.get(key, default)
