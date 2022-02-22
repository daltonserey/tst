# jsonfile
# (C) Dalton Serey - UFCG

"""
# usage

Use it as a simple dict with a save method that saves the data to the file. If
the file exists it will be read at instantiation. If you create more than one
object for the same filename, the same object will be returned by the
constructor (it is a singleton). See the example below.

```
from jsonfile import JsonFile

f = JsonFile('/Users/dalton/somefile.json', writable=True)
f['name'] = 'dalton'
f['data'] = [1, 2, 3]
f.save()
f2 = JsonFile('/Users/dalton/somefile.json')
f2 is f # True
```
"""

from builtins import str

import io
import sys
import os
import json
import yaml

def to_unicode(obj, encoding='utf-8'):
    # 2to3: assert isinstance(obj, basestring), type(obj)
    assert isinstance(obj, str), type(obj)
    if isinstance(obj, str):
        return obj

    for encoding in ['utf-8', 'latin1']:
        try:
            obj = str(obj, encoding)
            return obj
        except UnicodeDecodeError:
            pass

    assert False, "jsonfile: non-recognized encoding"

class CorruptedJsonFile(Exception): pass

DEFAULT_FAIL_MESSAGE = "file is corrupted"

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
        self.isjson = filename.endswith("json")
        
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
        if self.isjson:
            try:
                with io.open(self.filename, mode='r', encoding='utf-8') as f:
                    self.data = json.loads(to_unicode(f.read()))

            except ValueError as e:
                if exit_on_fail or failmsg:
                    print(failmsg or DEFAULT_FAIL_MESSAGE, file=sys.stderr)
                    sys.exit(1)

                raise CorruptedJsonFile("corrupted specification file")

        else:
            try:
                with open(self.filename, mode='r', encoding='utf-8') as f:
                    self.data = yaml.load(f.read(), Loader=yaml.FullLoader)
                    if self.data is None:
                        raise ValueError()

            except (yaml.parser.ParserError, yaml.scanner.ScannerError, ValueError) as e:
                if exit_on_fail or failmsg:
                    print(failmsg or DEFAULT_FAIL_MESSAGE, file=sys.stderr)

                raise CorruptedJsonFile("unrecognized file")


    def get(self, key, default=None):
        return self.data.get(key, default)
