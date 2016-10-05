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
TSTJSON = os.path.expanduser("./tst.json")

LRED = '\033[1;31m'
LGREEN = '\033[1;32m'
GREEN="\033[9;32m"
WHITE="\033[1;37m"
LCYAN = '\033[1;36m'
RESET = '\033[0m'

def date_handler(obj):
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    elif hasattr(obj, 'email'):
        return obj.email()

    return obj


def get_release():
    config = read_config()
    return config.get('release', 'unknown')


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


def pop_option(args, option):
    opt_select = '--' + option
    index = next((i for i in xrange(len(args)) if args[i] == opt_select), None)
    if index is None or index == len(args) - 1:
        return None

    value = args.pop(index + 1)
    selector = args.pop(index)
    
    return value


class CorruptedConfigFile(Exception): pass
class ConnectionFail(Exception): pass


class Server:
    
    def __init__(self, token=None):
        if token == None:
            config = read_config() 
            if 'access_token' not in config:
                print("You are not logged in.")
                print("Use `tst login` to log in to the server.")
                sys.exit(1)

            token = config['access_token']

        self.token = token


    class Response:

        def __init__(self):
            self._json = None

        def json(self):
            if not self._json:
                self._json = json.loads(self.text)

            return self._json


    def get(self, url, headers={}):
        curl_command = ['curl', '-v', '-sL']
        headers['Authorization'] = 'Bearer %s' % self.token
        for hname, hvalue in headers.items():
            curl_command.append('-H')
            curl_command.append('%s: %s' % (hname, hvalue))

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
        headers = {}
        headers['Authorization'] = 'Bearer %s' % self.token
        headers['TST-CLI-Release'] = get_release()
        for hname, hvalue in headers.items():
            curl_command.append('-H')
            curl_command.append('%s: %s' % (hname, hvalue))

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


def read_tstjson(exit=False, quit_on_fail=False):

    if not os.path.exists(TSTJSON):
        if quit_on_fail:
            msg = "This is not a tst directory."
            print(msg, file=sys.stderr)
            sys.exit(1)
        return None

    try:
        with codecs.open(TSTJSON, mode='r', encoding='utf-8') as f:
            tstjson = json.loads(to_unicode(f.read()))

    except ValueError:
        msg = "tst: %s is corrupted" % TSTJSON
        if exit or quit_on_fail:
            print(msg, file=sys.stderr)
            sys.exit(1)

        raise CorruptedConfigFile(msg)

    return tstjson


__config = None
def read_config(exit=False):
    global __config

    if __config is not None:
        return __config

    # create config file if it doesn't exist
    if os.path.exists(TSTCONFIG):
        try:
            with codecs.open(TSTCONFIG, mode='r', encoding='utf-8') as f:
                config = json.loads(to_unicode(f.read()))

        except ValueError:
            msg = "tst: %s is corrupted" % TSTCONFIG
            if exit:
                print(msg, file=sys.stderr)
                sys.exit()

            raise CorruptedConfigFile(msg)

    else:
        if not os.path.exists(TSTDIR):
            os.mkdir(TSTDIR)

        config = {
            'url': 'http://tst-online.appspot.com',
            'cookies': {}
        }
        save_config(config)

    __config = config
    return __config


def save_config(config):
    with codecs.open(TSTCONFIG, mode="w", encoding='utf-8') as f:
        f.write(json.dumps(
            config,
            indent=2,
            separators=(',', ': ')
        ))


def save_tstjson(tstjson):
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


def read_activity(tstjson=None):

    if tstjson is None:
        tstjson = read_tstjson()

    # gather activity data
    activity = {}
    
    # read activity yaml
    yamlfilename = tstjson['name'] + '.yaml'
    with codecs.open(yamlfilename, mode='r', encoding='utf-8') as y:
        yamlfile = yaml.load(y.read())

    # read name, label, tests and files
    activity['name'] = yamlfile['name']
    activity['label'] = yamlfile['label']
    activity['type'] = yamlfile['type']
    activity['text'] = yamlfile['text']
    activity['tests'] = yamlfile.get('tests', [])

    # add default category to tests
    for test in activity['tests']:
        if 'category' not in test:
            test['category'] = 'secret'
        if 'type' not in test:
            test['type'] = 'io'

    # add activity files
    ignore = ['tst.json', activity['name'] + '.yaml']
    textfile = activity['name'] + '.md' if tstjson.get('text_in_file') else None
    if textfile:
        ignore.append(textfile)
    activity_files = [f for f in os.listdir('.') if f not in ignore and os.path.isfile(f)]

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


def get_save_function(kind):
    return globals()["save_" + kind]


def indent(text, level=1):
    lines = text.splitlines()
    text = "\n".join([level * "    " + "%s" % l for l in lines])
    return text + '\n'


def save_yaml(yamlfile, data):

    with codecs.open(yamlfile, mode='w', encoding='utf-8') as y:

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
                    if '\n' in field_value:
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


def save_activity(data, text_in_file, is_checkout=True):

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

    if not text_in_file:
        tstyaml['text'] = data['text']

    if is_checkout:
        save_yaml(data['name'] + '.yaml', tstyaml)

    # save text in file
    if is_checkout and text_in_file:
        textfile = tstjson['name'] + '.md'
        with codecs.open(textfile, mode='w', encoding='utf-8') as f:
            f.write(data['text'])

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
    tstjson['text_in_file'] = text_in_file
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
