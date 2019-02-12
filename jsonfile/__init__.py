# jsonfile
# (C) Dalton Serey - UFCG
# gist url: https://gist.github.com/daltonserey/8fc9644cfb9dda7fdfb09a3e006587b3
# r4

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

from jsonfile import JsonFile
