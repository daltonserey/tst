#!/usr/bin/env python
# coding: utf-8
# TST-Online Update
# (C) 2012 Dalton Serey
# This module contains helper functions and classes for TST scripts.

from __future__ import print_function
from __future__ import unicode_literals

import os
import sys
import json
import codecs
import signal
import re

from subprocess import Popen, PIPE, CalledProcessError

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
TSTDIR = os.path.expanduser("~/.tst/")
TSTCONFIG = os.path.expanduser(TSTDIR + "config.json")
TSTRELEASE = os.path.expanduser(TSTDIR + "release.json")
TSTJSON = os.path.expanduser("./.tst/tst.json")

LRED = '\033[1;31m'
LGREEN = '\033[1;32m'
GREEN="\033[9;32m"
WHITE="\033[1;37m"
LCYAN = '\033[1;36m'
RESET = '\033[0m'

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
        ensure_ascii=False)


def show(data):
    print(data2json(data).encode('utf-8'))
    sys.exit()
    

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


def pop_argument(args, index=0):
    if index >= len(args):
        return None
    
    return args.pop(0)


def pop_option(args, option, short=None, default=None, type=str):
    selectors = ['--' + option]
    if short is not None:
        selectors.append('-' + short)

    index = next((i for i in xrange(len(args)) if args[i] in selectors), None)
    if index is None or index == len(args) - 1:
        return default

    value = args.pop(index + 1)
    selector = args.pop(index)
    
    return type(value)


def pop_flag(args, flag, short=None):
    selectors = ['--' + flag]
    if short is not None:
        selectors.append('-' + short)

    index = next((i for i in xrange(len(args)) if args[i] in selectors), None)
    if index is None:
        return False

    args.pop(index)
    return True


class CorruptedFile(Exception): pass
class ConnectionFail(Exception): pass


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


    def pop(self, key):
        if self.data is None:
            self.load()

        self.data.pop(key, None)


    def load(self, exit_on_fail=False):
        if not os.path.exists(TSTCONFIG):
            self.data = {'url': 'http://tst-online.appspot.com', 'cookies': {}}
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
        if self.data is None:
            return

        with codecs.open(TSTCONFIG, mode="w", encoding='utf-8') as f:
            f.write(json.dumps(
                self.data,
                indent=2,
                separators=(',', ': ')
            ))


    def get(self, key, default=None):
        if self.data is None:
            self.load()

        return self.data.get(key, default)

    
class Server(object):
    
    __instance = None

    class Response:

        def json(self):
            if '_json' not in dir(self):
                try:
                    self._json = json.loads(self.body)
                except:
                    self._json = None

            return self._json


    def __new__(cls):

        # instantiation
        if Server.__instance is not None:
            return Server.__instance

        Server.__instance = object.__new__(cls)
        self = Server.__instance

        # initialization
        self.config = Config()
        self.user = self.config.get('user')
        self.token = self.config.get('access_token')

        return self


    def request(self, method, path, headers={}, payload=None, exit_on_fail=False):
        curl_command = [
            'curl',
            '-q', # don't use ~/.curlrc (must be first arg)
            '-X', method.upper(), # http verb
            '-v', # be verbose: print report to stderr
            '-s', # don't print progress meter
            '-L'  # follow redirects
        ]

        headers['TST-CLI-Release'] = self.config.get('release', 'unknown')
        if 'Authorization' not in headers:
            headers['Authorization'] = 'Bearer %s' % self.token
        for hname, hvalue in headers.items():
            curl_command.append('-H')
            curl_command.append('%s: %s' % (hname, hvalue))

        url = self.config['url'] + path
        curl_command.append(url)
        if payload is not None:
            curl_command.append('-d')
            data = "%s" % json.dumps(payload)
            curl_command.append(data)

        signal.alarm(20000) # timeout in seconds
        process = Popen(curl_command, stdout=PIPE, stderr=PIPE) 
        try:
            stdout, stderr = map(to_unicode, process.communicate())
            signal.alarm(0) # reset alarm for future use...
            process.wait()
        except CutTimeOut: # timeout!!!
            process.terminate()
            raise ConnectionFail()

        # raw data
        response = self.Response()
        response.stderr = stderr
        response.stdout = stdout
        response.exit_status = process.returncode

        # curl messages
        lines = [l[2:] for l in stderr.splitlines() if l and l[0] == '*']
        response.curl_messages = "\n".join(lines)

        # request headers
        lines = [l[2:] for l in stderr.splitlines() if l and l[0] == '>']
        response.request_headers = "\n".join(lines)

        # response headers
        lines = [l[2:] for l in stderr.splitlines() if l and l[0] == '<']
        response.headers = "\n".join(lines)

        if not response.headers:
            if exit_on_fail:
                msg = "tst: can't connect to server"
                _assert(False, msg)
                
            raise ConnectionFail("can't connect to tst online")

        # body
        response_lines = response.headers.splitlines()
        response.status_code = None
        for i in xrange(len(response_lines)-1, -1, -1):
            if response_lines[i].startswith("HTTP"):
                status_line = response_lines[i]
                response.status_code = int(status_line.split()[1])
                break
            
        # exit_on_fail
        if exit_on_fail and not (200 <= response.status_code < 300):
            msg = 'Request to server failed'
            try:
                data = json.loads(response.stdout)
                if 'messages' in data and type(data['messages'] == list):
                    msg += "\nServer message: " + str(data['messages'][0])
            except:
                data = {}
                msg += ('\n' + "Couldn't parse server response")

            cprint(LRED, msg)
            if 'messages' in data and data['messages'][0] == 'invalid token':
                print("---")
                print("Use `tst login` to log in to the server")

            sys.exit(1)
        
        response.body = stdout if response.status_code else None
        
        return response


    def get(self, path, headers={}, exit_on_fail=False):
        return self.request('get', path, headers, exit_on_fail=exit_on_fail)


    def post(self, path, headers={}, payload='', exit_on_fail=False):
        return self.request('post', path, headers=headers, payload=payload, exit_on_fail=exit_on_fail)


    def patch(self, path, payload, headers={}, exit_on_fail=False):
        return self.request('patch', path, headers=headers, payload=payload, exit_on_fail=exit_on_fail)




class GitHub:
    
    class Response:

        def __init__(self):
            self._json = None

        def json(self):
            if not self._json:
                self._json = json.loads(self.text)

            return self._json


    def get(self, url, headers={}):
        curl_command = ['curl', '-q', '-v', '-sL']
        curl_command.append(url)
        signal.alarm(20000) # timeout in seconds
        process = Popen(curl_command, stdout=PIPE, stderr=PIPE) 
        try:
            stdout, stderr = map(to_unicode, process.communicate())
            signal.alarm(0) # reset alarm for future use...
            process.wait()
        except CutTimeOut: # timeout!!!
            process.terminate()
            raise ConnectionFail()

        # raw data
        response = self.Response()
        response.stderr = stderr
        response.stdout = stdout
        response.exit_status = process.returncode

        # curl messages
        lines = [l[2:] for l in stderr.splitlines() if l and l[0] == '*']
        response.curl_messages = "\n".join(lines)

        # request headers
        lines = [l[2:] for l in stderr.splitlines() if l and l[0] == '>']
        response.request_headers = "\n".join(lines)

        # response headers
        lines = [l[2:] for l in stderr.splitlines() if l and l[0] == '<']
        response.headers = "\n".join(lines)

        if not response.headers:
            raise ConnectionFail("can't connect to tst online")

        # text
        response_lines = response.headers.splitlines()
        response.status_code = None
        for i in xrange(len(response_lines)-1, -1, -1):
            if response_lines[i].startswith("HTTP"):
                status_line = response_lines[i]
                response.status_code = int(status_line.split()[1])
                break
            
        response.text = stdout if response.status_code else None
        
        return response


    def post(self, url, payload):
        return self.request('post', url, payload)


    def patch(self, url, payload):
        return self.request('patch', url, payload)


    def request(self, method, url, payload):
        assert method in ('post', 'patch')
        
        curl_command = ['curl', '-X', method.upper(), '-v', '-s']
        curl_command.append(url)
        curl_command.append('-d')
        data = "%s" % json.dumps(payload)
        curl_command.append(data)

        signal.alarm(20000) # timeout in seconds
        process = Popen(curl_command, stdout=PIPE, stderr=PIPE) 
        try:
            stdout, stderr = map(to_unicode, process.communicate())
            signal.alarm(0) # reset alarm for future use...
            process.wait()
        except CutTimeOut: # timeout!!!
            process.terminate()
            raise ConnectionFail()

        # raw data
        response = self.Response()
        response.stderr = stderr
        response.stdout = stdout
        response.exit_status = process.returncode

        # curl messages
        lines = [l[2:] for l in stderr.splitlines() if l and l[0] == '*']
        response.curl_messages = "\n".join(lines)

        # request headers
        lines = [l[2:] for l in stderr.splitlines() if l and l[0] == '>']
        response.request_headers = "\n".join(lines)

        # response headers
        lines = [l[2:] for l in stderr.splitlines() if l and l[0] == '<']
        response.headers = "\n".join(lines)

        if not response.headers:
            raise ConnectionFail("can't connect to tst online")

        # text
        response_lines = response.headers.splitlines()
        response.status_code = None
        for i in xrange(len(response_lines)-1, -1, -1):
            if response_lines[i].startswith("HTTP"):
                status_line = response_lines[i]
                response.status_code = int(status_line.split()[1])
                break
            
        response.text = stdout if response.status_code else None
        
        return response


def read_tstjson(file=TSTJSON, exit=False, quit_on_fail=False):

    if not os.path.exists(file):
        if quit_on_fail:
            msg = "This is not a tst directory."
            print(msg, file=sys.stderr)
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

    assignment['checksum'] = md5.md5(contents).hexdigest()
    assignment['files'] = files
    assignment['unknown_files'] = unknown_files
        
    return assignment


def sync_activity(response, tstjson):
    # check response was positive
    json_response = response.json()
    _assert(response.exit_status == 0, 'tst: fatal: curl command failed\n')
    _assert('error' not in json_response, 'tst: fatal: server reported error:\n' + str(json_response.get('messages', 'no server messages')))

    # post/patch worked: save using proper save function
    save = get_save_function('activity')
    save(json_response, is_checkout=False)


def read_activity(tstjson=None):

    def abort(msg):
        msg = "tst: invalid activity\n" + msg
        _assert(False, msg)
        
    if tstjson is None:
        tstjson = read_tstjson()

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

    # add default category to tests
    for test in activity.get('tests', []):
        if 'category' not in test:
            test['category'] = 'secret'
        if 'type' not in test:
            test['type'] = 'io'

    # validate activity or abort
    validate_activity(activity)

    # add activity files
    ignore = ['tst.json', activity['name'] + '.yaml']
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
        activity['text'] = yamlfile['text']
    
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
    # check author: no requirement wrt activity author

    # check text
    _assert(activity.get('text'), msg + "missing 'text' field")
    _assert(isinstance(activity['text'], basestring), msg + 'text must be string')
    _assert(activity['text'][-1] == '\n', msg + "text must end in '\\n' (POSIX)")

    # it activity has tests...
    for i in xrange(len(activity.get('tests', []))):
        test = activity['tests'][i]
        if test['type'] == 'io':

            # require input in every io test
            _assert('input' in test, msg + "missing 'input' field in io test#%d" % i)
            _assert(isinstance(test['input'], basestring), msg + 'input must be text (test#%d)' % i)
            _assert(test['input'] and test['input'][-1] == '\n', msg + "input must end in '\\n' (test#%d)" % i)

            # require output in every io test
            _assert('output' in test, msg + "missing 'output' field in io test#%d" % i)
            _assert(isinstance(test['output'], basestring), msg + 'output must be text (test#%d)' % i)
            _assert(test['output'] and test['output'][-1] == '\n', msg + "output must end in '\\n' (test#%d)" % i)


        elif test['type'] == 'script':

            # require script in every script test
            _assert('script' in test, msg + "missing 'script' field in script test")


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
                        cprint(LYELLOW, "WARNING: '%s' field is null" % test_field, file=sys.stderr)
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
    tstjson['files'] = {k:{'category': data['files'][k]['category']} for k in data['files']}
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

    files_changed = any(f.split("/")[1:3] for f in diff['changed_fields'] if f.startswith('files'))

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
