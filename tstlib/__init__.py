#!/usr/bin/env python
# coding: utf-8
# TST-Online Update
# (C) 2012 Dalton Serey
# This module contains helper functions and classes for TST scripts.

from __future__ import print_function
from __future__ import unicode_literals

from config import Config
from colors import *
from utils import to_unicode
from popargs import *
from server import Server

import os
import sys
import json
import codecs
import re

# optionally import requests
try:
    import requests
    we_have_requests = True
except ImportError:
    we_have_requests = False

# optionally import yaml, md5 and difflib
try:
    import yaml
    import md5
    import difflib
    we_have_yaml = True
except ImportError:
    we_have_yaml = False

# Constants
TSTJSON = os.path.expanduser("./.tst/tst.json")

def _assert(condition, msg):
    if condition:
        return

    cprint(LRED, msg)
    sys.exit(1)

    
def cprint(color, msg, file=sys.stdout):
    print(color + msg + RESET, file=file)


def date_handler(obj):
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    elif hasattr(obj, 'email'):
        return obj.email()

    return obj


def data2json(data):
    return json.dumps(
        data,
        default=date_handler,
        indent=2,
        separators=(',', ': '),
        sort_keys=True,
        ensure_ascii=False)


def show(data):
    print(data2json(data).encode('utf-8'))
    sys.exit()
    

class CorruptedFile(Exception): pass


def load_required(method):
    def load(self, *args, **kwargs):
        if self.data is None:
            self.load()

        method(self, *args, **kwargs)

    return load


def boolean(value):
    if value in [True, 'True', 'true', 'yes', 'on']:
        return True
    else:
        return False


def read_tstjson(file=TSTJSON, exit=False, quit_on_fail=False):

    if not os.path.exists(file):
        if quit_on_fail:
            msg = "This is not a tst directory"
            cprint(LRED, msg, file=sys.stderr)
            sys.exit(1)
        return None

    try:
        with codecs.open(file, mode='r', encoding='utf-8') as f:
            tstjson = json.loads(to_unicode(f.read()))

    except ValueError:
        msg = "tst: %s is corrupted" % file
        if exit or quit_on_fail:
            print(msg, file=sys.stderr)
            sys.exit(1)

        raise CorruptedFile(msg)

    return tstjson


def save_tstjson(tstjson):
    dirname = os.path.dirname(TSTJSON)
    if not os.path.exists(dirname):
        os.makedirs(dirname)

    with codecs.open(TSTJSON, mode="w", encoding='utf-8') as f:
        f.write(json.dumps(
            tstjson,
            indent=2,
            separators=(',', ': ')
        ))


def requests_required(method):
    def check_requests(self, *args):
        if not we_have_requests:
          print("tst: this command requires requests")

        return method(self, *args)

    return check_requests


def hashify(data):

    if isinstance(data, basestring):
        return md5.md5(data.encode('utf-8')).hexdigest()
    elif type(data) == list and all(type(e) == dict for e in data):
        return [md5.md5(json.dumps(t, sort_keys=True)).hexdigest() for t in data]
    elif type(data) == dict:
        return {key:hashify(data[key]) for key in data}

    # hashify works only with strings, objects and lists of objects
    raise ValueError('tst: invalid data to hashify')


def read_assignment(tstjson):

    def abort(msg):
        msg = "tst: invalid assignment\n" + msg
        _assert(False, msg)
        
    # gather assignment data
    assignment = {}
    
    # read files
    files = {}
    unknown_files = []
    for filename in os.listdir("."):
        if filename == 'tst.json':
            # tests file
            continue

        if filename[0] == '.':
            # hidden file
            continue

        if os.path.isdir(filename):
            # directory
            continue

        if filename not in tstjson['files'].keys():
            # unknown file
            unknown_files.append(filename)
            continue

        with codecs.open(filename, mode='r', encoding='utf-8') as f:
            contents = f.read()
            files[filename] = {
                'data': contents,
                'category': tstjson['files'][filename].get('category', 'secret')
            }
            if files[filename]['category'] == 'answer':
                assignment['checksum'] = md5.md5(contents.encode('utf-8')).hexdigest()

    assignment['files'] = files
    assignment['unknown_files'] = unknown_files
        
    return assignment


def sync_activity(response, tstjson):
    json_response = response.json()

    if json_response is None:
        tstjson['state'] = 'deleted'
        fields2delete = [
            'version_token',
            'last_update_datetime',
            'checkout',
            'create_datetime',
            'collaborators',
            'iid',
            'version',
            'owner',
            'type',
            'last_update_user'
        ]
        for field in fields2delete:
            tstjson.pop(field, None)
        save_tstjson(tstjson)
    else:
        _assert('error' not in json_response, 'tst: fatal: server reported error:\n' + str(json_response.get('messages', 'no server messages')))

        # post/patch worked: save using proper save function
        save = get_save_function('activity')
        save(json_response, is_checkout=False)
        


def read_activity(tstjson=None):

    def abort(msg):
        msg = "tst: invalid activity\n" + msg
        _assert(False, msg)
        
    tstjson = tstjson or read_tstjson()

    # gather activity data
    activity = {}
    
    # read activity yaml
    yamlfilename = tstjson['name'] + '.yaml'
    with codecs.open(yamlfilename, mode='r', encoding='utf-8') as y:
        try:
            yamlfile = yaml.load(y.read())
        except:
            msg = "tst: failed loading activity yaml\n"
            msg += "Is your yaml well formed?\n"
            msg += "Operation aborted."
            _assert(False, msg)

    # read name, label, tests and files
    activity['name'] = yamlfile.get('name')
    activity['label'] = yamlfile.get('label')
    activity['type'] = yamlfile.get('type')
    activity['text'] = yamlfile.get('text')
    activity['tests'] = yamlfile.get('tests', [])

    # add default category and type to tests
    for test in activity.get('tests') or []:
        test.setdefault('category', 'secret')
        test.setdefault('type', 'io')

    # add activity files
    #ignore = ['tst.json', activity['name'] + '.yaml']
    ignore = ['tst.json']
    textfile = activity['name'] + '.md' if tstjson.get('text_in_file') else None
    if textfile:
        ignore.append(textfile)
    activity_files = [f for f in os.listdir('.') if f not in ignore and f[0] != '.' and os.path.isfile(f)]

    # identify unknown files
    unknown_files = [f for f in activity_files if f not in tstjson.get('files', [])]
    activity_files = [f for f in activity_files if f not in unknown_files]

    # read file contents
    activity['files'] = {}
    for filename in activity_files:
        try:
            with codecs.open(filename, mode='r', encoding='utf-8') as f:
                activity['files'][filename] = {
                    'data': f.read(),
                    'category': tstjson['files'][filename].get('category', 'secret')
                }

        except UnicodeError as e:
            print("tst: warning: ignoring '%s' due to encoding problems" % filename, file=sys.stderr)

    # read activity text
    if textfile:
        try:
            with codecs.open(textfile, mode='r', encoding='utf-8') as md:
                activity['text'] = md.read()
        except:
            print("tst: fatal: couldn't read %s" % textfile, file=sys.stderr)
    else:
        activity['text'] = yamlfile.get('text')
    
    # validate activity or abort
    validate_activity(activity)

    return activity, unknown_files


def validate_activity(activity):

    # generic message base
    msg = 'tst: invalid activity\n'

    # check name
    _assert(activity.get('name'), msg + "missing 'name' field")
    _assert(re.findall(r'[^a-z0-9._\-]', activity['name']) == [], msg + "name chars must be in [a-z0-9._-]")
    _assert(activity['name'][0] not in '.-', msg + "name cannot start with [.-]")

    # check label
    _assert(activity.get('label'), msg + "missing 'label' field")
    _assert(isinstance(activity['label'], basestring), 'label must be string')
    _assert('\n' not in activity['label'], "label cannot have '\\n'")

    # check type: no requirement wrt activity type
    _assert(activity.get('type'), msg + "missing 'type' field")
    _assert(isinstance(activity['type'], basestring), msg + "type must be single line string")
    _assert('\n' not in activity['type'], msg + "type must be single line string")

    # check files
    _assert(activity.get('files'), msg + "activity has no files property")
    _assert(type(activity['files']) == dict, msg + "files must be a dictionary")
    _assert(all(type(f) == dict for f in activity['files'].values()), msg + "every file must be a dictionary")

    # check author: no requirement wrt activity author

    # check text
    _assert(activity.get('text'), msg + "missing 'text' field")
    _assert(isinstance(activity['text'], basestring), msg + 'text must be string')
    _assert(activity['text'][-1] == '\n', msg + "text must end in '\\n' (POSIX)")

    # check tests
    if activity.get('tests'):
        _assert(type(activity['tests']) == list, msg + "tests must be a list of dictionaries")
        _assert(all(type(t) == dict for t in activity['tests']), msg + "every test must be a dictionary")
        _assert(all('type' in t for t in activity['tests']), msg + "every test must have a type")
        _assert(all(t['type'] in ('io', 'script') for t in activity['tests']), msg + "test types must be either io or script")
        _assert(all(not t['type'] == 'script' or 'script' in t for t in activity['tests']), msg + "every script test must have script")
        _assert(all(not t['type'] == 'io' or 'output' in t for t in activity['tests']), msg + "every io test must have output")
        _assert(all(not t['type'] == 'io' or 'input' in t for t in activity['tests']), msg + "every io test must have input")


def get_save_function(kind):
    return globals()["save_" + kind]


def indent(text, level=1):
    lines = text.splitlines()
    text = "\n".join([level * "    " + "%s" % l for l in lines])
    return text + '\n'


def save_yaml(yamlfile, data):

    with codecs.open(yamlfile, mode='w', encoding='utf-8') as y:
        
        # save comment
        y.write("# This file is automatically created at each checkout.\n")
        y.write("# Any comments and unkwnown properties will be discarded.\n\n")

        # save name, type and label
        y.write("name: %s\n" % data['name'])
        y.write("type: %s\n" % data['type'])
        y.write("label: %s\n" % data['label'])

        # save text
        if 'text' in data:
            y.write("text: |\n")
            y.write("%s\n" % indent(data['text']))

        # save tests
        if 'tests' in data:
            y.write('tests:\n')
            for test in data['tests']:
                is_first = True
                for test_field, field_value in test.items():
                    prefix = '-   ' if is_first else '    '
                    if field_value is None:
                        y.write(prefix + '%s: null\n' % test_field)
                        cprint(LGREEN, "WARNING: '%s' field is null" % test_field, file=sys.stderr)
                    elif '\n' in field_value:
                        y.write(prefix + '%s: |\n' % test_field)
                        y.write(indent(field_value, 2))
                    else:
                        y.write(prefix + '%s: %s\n' % (test_field, field_value))
                    is_first = False
                y.write('\n')

        # save files
        if 'files' in data:
            y.write('\nfiles:\n')
            for file in data['files']:
                is_first = True
                for file_field, field_value in file.items():
                    prefix = '-   ' if is_first else '    '
                    if file_field == 'data': continue
                    if '\n' in field_value:
                        y.write(prefix + '%s: |+\n' % file_field)
                        y.write(indent(field_value, 2))
                    else:
                        y.write(prefix + '%s: %s\n' % (file_field, field_value))
                    is_first = False


def save_activity(data, is_checkout=True):

    # save yaml with editable fields
    tstyaml = {}
    tstyaml['name'] = data['name']
    tstyaml['type'] = data['type']
    tstyaml['label'] = data['label']
    tstyaml['tests'] = data['new_tests'][-1]

    # add default category to tests
    for test in tstyaml['tests']:
        if 'category' not in test:
            test['category'] = 'secret'
        if 'type' not in test:
            test['type'] = 'io'

    tstyaml['text'] = data['text']

    if is_checkout:
        save_yaml(data['name'] + '.yaml', tstyaml)

    # save files
    if is_checkout:
        for filename in data['files']:
            try:
                with codecs.open(filename, mode='w', encoding='utf-8') as f:
                    f.write(data['files'][filename]['data'])
            except:
                print("tst: fatal: Can't save file '%s'" % filename, file=sys.stderr)
                sys.exit(1)

    # prepare tst.json
    tstjson = {}

    # keep hashified tstyaml + files (for change detection)
    tstyaml['files'] = data['files']
    tstjson['checkout'] = hashify(tstyaml)

    # replicate some data from yaml (for easy lookup)
    tstjson['name'] = data['name']
    tstjson['type'] = data['type']
    tstjson['label'] = data['label']

    # activity data exclusively in tstjson
    tstjson['files'] = {k:{'category': data['files'][k].get('category', 'secret')} for k in data['files']}
    tstjson['iid'] = data['iid']
    tstjson['kind'] = 'activity'
    tstjson['version'] = "%s.%s.%s" % (data['major'], data['minor'], data['patch'])
    tstjson['version_token'] = data['version_token']
    tstjson['create_datetime'] = data['create_datetime']
    tstjson['collaborators'] = data['collaborators']
    tstjson['last_update_user'] = data['last_update_user']
    tstjson['last_update_datetime'] = data['last_update_datetime']
    tstjson['owner'] = data['owner']
    tstjson['state'] = data['state']

    # save it
    save_tstjson(tstjson)


def activity_changes(activity, tstjson):
    activity_hash = hashify(activity)
    checkout_hash = tstjson['checkout']
    diff = {
        'changed_fields': spot_changes(activity_hash, checkout_hash),
        'tests_diff': tests_differ(activity_hash['tests'], checkout_hash['tests']),
        'missing_files': [f for f in tstjson['files'].keys() if f not in activity['files'].keys()],
        'removed_files': [f for f in tstjson['checkout']['files'] if f not in tstjson['files']]
    }

    files_changed = [f.split("/")[1] for f in diff['changed_fields'] if f.startswith('files')]
    files_changed = [f for f in files_changed if f != tstjson['name'] + '.yaml']

    if files_changed or diff['tests_diff'] or diff['removed_files']:
        diff['bump_required'] = True

    return {k:diff[k] for k in diff if diff[k]}

    

def spot_changes(activity, checkout):
    
    assert type(activity) == dict, "spot_changes works only on objects"

    changed = []
    for key in activity:
        if activity[key] == checkout.get(key):
            continue

        if isinstance(activity[key], basestring) or type(activity[key]) == list:
            changed.append(key)

        elif type(activity[key]) == dict:
            if key in checkout:
                subkeys = spot_changes(activity[key], checkout[key])
                subkeys = ["%s/%s" % (key, subkey) for subkey in subkeys]
                changed.extend(subkeys)
            else:
                changed.append("%s/new" % key)

        else:
            sys.exit('tst: fatal: activity corrupted')

    return changed


def tests_differ(activity, checkout):

    delta = {}
    diffs = [d for d in difflib.ndiff(checkout, activity) if d[0] != '?']
    index = 0
    for i in xrange(len(diffs)):
        line = diffs[i]
        if line[0] == ' ':
            index += 1
        elif line[0] == '+':
            previous = diffs[i-1] if (i > 0) else None
            delta.setdefault('tests', []).append(('+', line[2:], index))
            index += 1
        elif line[0] == '-':
            delta.setdefault('tests', []).append(('-', line[2:], index))
            # index is not changed, because this line was removed
        elif line[0] == '?':
            # this line is added by ndiff for information only
            pass

    return delta.get('tests', [])


@requests_required
def get(url):
    session = requests.session()
    resp = session.get(url, cookies=config['cookies'])
    return resp.text


@requests_required
def post(url, data):
    url = config['baseurl'] + url
    session = requests.session()
    resp = session.post(url, cookies=config['cookies'], data=json.dumps(data))
    return resp.text


if __name__ == "__main__":
    print("tstlib is a helper module for tst commands")
