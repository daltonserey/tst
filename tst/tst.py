# coding: utf-8
from __future__ import unicode_literals
from __future__ import print_function

import sys
import os
import codecs
import glob
import datetime as dt

import requests
from cachecontrol import CacheControl
from cachecontrol.caches.file_cache import FileCache

from jsonfile import JsonFile, CorruptedJsonFile
from colors import *
from utils import cprint, _assert, is_posix_filename, data2json

TSTDIR = os.path.expanduser('~/.tst/')
YAMLCONFIG = TSTDIR + 'config.yaml'
JSONCONFIG = TSTDIR + 'config.json'

def get_config():
    if not os.path.exists(YAMLCONFIG) and os.path.exists(JSONCONFIG):
        return JsonFile(JSONCONFIG)

    if not os.path.exists(YAMLCONFIG):
        if not os.path.isdir(TSTDIR):
            os.mkdir(TSTDIR)

        with codecs.open(YAMLCONFIG, encoding="utf-8", mode="w") as config_file:
            config_file.write(
                "sites:\n" 
                "- name: demo\n"
                "  url: http://www.dsc.ufcg.edu.br/~dalton/demo\n"
            )

    return JsonFile(YAMLCONFIG)


def dirtype(path=""):
    path = os.path.abspath(os.path.expanduser(path))

    # tst internal types of directories
    if path == os.path.expanduser('~/.tst'):
        return "config"

    elif os.path.basename(path) == '.tst':
        return "internal"

    # user content
    elif os.path.exists(path + '/.tst/assignment.json'):
        return "assignment"

    elif os.path.exists(path + '/.tst/activity.json'):
        return "activity"

    elif os.path.exists(path + '/.tst/collection.json'):
        return "collection"

    # user content (old format)
    elif os.path.exists(path + '/.tst/tst.json'):
        kind = JsonFile(path + "/.tst/tst.json").get("kind", "")
        return "old:" + kind

    # corrupted/incomplete content
    elif os.path.isdir(path + '/.tst') and not path == os.path.expanduser('~'):
        return "corrupted"

    # directory contains a file with tst tests
    elif os.path.exists(path + '/tst.json') or os.path.exists(path + '/tst.yaml'):
        return "tst-able"

    # not a tst directory
    return None


def validate_tst_object(json):
    def is_valid_mode(mode):
        return mode is None or\
               isinstance(mode, basestring) and\
               len(mode) <= 3 and\
               all(d in 'rwx' for d in mode.lower())

    assert 'files' in json, "missing files property"
    assert type(json) is dict, "json is not an object"
    assert 'kind' in json, "missing kind property"
    assert json['kind'] in ["assignment", "activity", "collection"], "unrecognized kind"

    files = json['files']
    assert all('content' in f for f in files), "missing content in file(s)"
    assert all('name' in f for f in files), "missing name in file(s)"
    assert all(is_posix_filename(f['name'], "/") for f in files), "non posix portable file(s) name(s)"
    assert all(is_valid_mode(f.get('mode')) for f in files), "invalid mode in file(s)"
    assert len(files) == len(set([f['name'] for f in files])), "repeated file names"


def save_file(filename, content, mode):
    def octal_mode(mode):
        return {
            (False , False): 0o444,
            (False ,  True): 0o555,
            (True  , False): 0o644,
            (True  ,  True): 0o755
        }["w" in mode, "x" in mode]

    subdirs = os.path.dirname(filename)
    if not os.path.isdir(subdirs):
        os.makedirs(subdirs)

    with codecs.open(filename, encoding="utf-8", mode="w") as f:
        f.write(content)

    os.chmod(filename, octal_mode(mode))


def save_files(files, basedir, verbose=True):
    saved = 0
    for f in files:
        filename = basedir + "/" + f['name']
        mode = f.get('mode', '644')

        try:
            if os.path.exists(filename):
                os.chmod(filename, 0o644)

            verbose and cprint(LGREEN, "W %s" % filename)
            save_file(filename, f['content'], mode)
            saved += 1

        except IOError as e:
            cprint(LRED, e)
            cprint(LRED, "Failed saving file: '%s'" % f['name'])

        except OSError as e:
            cprint(YELLOW, e)
            cprint(LRED, "Failed setting file mode: '%s'" % f['name'])

    return saved


class Site:
    def __init__(self, name=None, url=None):
        self.name = name
        self.url = url
        sites = get_config()['sites']
        for s in sites:
            if s['name'] == name:
                self.url = s['url']


    def get(self, key):
        s = requests.session()
        s = CacheControl(s, cache=FileCache(os.path.expanduser('~/.tst/cache')))

        url = "%s/%s" % (self.url, key)
        try:
            response = s.get(url, headers={})
        except requests.ConnectionError:
            _assert(False, "Connection failed... check your internet connection")

        _assert(response.ok, "%s\nRequest failed: %s (%d)" % (url, response.reason, response.status_code))
        response.encoding = 'utf-8'
        try:
            resource = response.json()
            resource['_response'] = response
            validate_tst_object(resource)

        except ValueError:
            _assert(False, "Resource is not valid json")

        except AssertionError as e:
            _assert(False, "Not a TST Object: %s" % e.message)

        return resource


def get_site(name=None, url=None):
    assert name is None or url is None

    if url:
        return Site(url=url)

    elif name == "_DEFAULT":
        index = 0

    else:
        sites = get_config()['sites']
        index = next((i for i in range(len(sites)) if sites[i]['name'] == name), None)
        if index is None:
            return None

    return Site(name=get_config()['sites'][index]['name'])


def read_specification(filename=None, verbose=False):
    # deal with a custom specification file name
    if filename:
        _assert(os.path.exists(filename), "File %s not found" % filename)
        cprint(LCYAN, "Reading specification file: %s" % filename)
        return JsonFile(filename, array2map="tests")

    # deal with default specification file names
    tstyaml_exists = os.path.exists('tst.yaml')
    tstjson_exists = os.path.exists('tst.json')
    if verbose and tstyaml_exists and tstjson_exists:
        cprint(YELLOW, "Found both tst.yaml and tst.json: using tst.yaml")

    if tstyaml_exists:
        try:
            specification = JsonFile('tst.yaml', array2map="tests")
        except CorruptedJsonFile:
            _assert(False, "Corrupted specification file")
        return specification

    elif tstjson_exists:
        try:
            specification = JsonFile('tst.json', array2map="tests")
        except CorruptedJsonFile:
            _assert(False, "Corrupted specification file")
        return specification

    # neither tst.yaml, nor tst.json exist
    candidates = glob.glob("*.yaml")
    if len(candidates) == 0:
        candidates = glob.glob("*.json")

    if len(candidates) == 1:
        cprint(YELLOW, "Using %s as specification file" % candidates[0])
        try:
            specification = JsonFile(candidates[0], array2map="tests")
        except:
            _assert(False, "Invalid specification file")
        return specification

    cprint(YELLOW, "Cannot determine specification file")
    _assert(False, "Use --spec-file to indicate specification file")
    

def save_assignment(activity, dir_name, etag, url, repo):

    # move into directory
    os.chdir(dir_name)

    # save the original activity data
    dirname = './.tst' 
    if not os.path.exists(dirname):
        os.makedirs(dirname)

    with codecs.open('./.tst/activity.json', mode='w', encoding='utf-8') as f:
        f.write(data2json({
            "url": url,
            "name": activity.get('name'),
            "activity": activity,
            "etag": etag,
            "repo": repo,
            "updated_at": dt.datetime.utcnow().isoformat().split(".").pop(0) + "Z"
        }))

    # save activity files
    files = activity['files']
    for file in files:
        if os.path.exists(file['name']):
            contents = open(file['name']).read().decode('utf-8')
            if contents != file['data']:
                cprint(LRED, "skipping modified file: '%s' (use --overwrite)" % file['name'])
            else:
                cprint(RESET, "skipping unmodified file: '%s'" % file['name'])
            continue

        try:
            with codecs.open(file['name'], mode='w', encoding='utf-8') as f:
                f.write(file['data'])
            cprint(LCYAN, "Adding file '%s'" % file['name'])
        except:
            print("tst: fatal: Can't save file '%s'" % file['name'], file=sys.stderr)
            sys.exit(1)
