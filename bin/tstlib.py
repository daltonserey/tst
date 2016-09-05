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

# Constants
TSTDIR = os.path.expanduser("~/.tst/")
TSTCONFIG = os.path.expanduser(TSTDIR + "config.json")
TSTRELEASE = os.path.expanduser(TSTDIR + "release.json")
TSTJSON = os.path.expanduser("./tst.json")


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


class CorruptedConfigFile(Exception): pass
class ConnectionFail(Exception): pass


class TSTOnline:
    
    def __init__(self, token):
        self.token = token


    class Response:

        def json(self):
            return json.loads(self.text)


    def get(self, url, headers={}):
        curl_command = ['curl', '-v', '-s']
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
        if response.headers[0:4] == "HTTP":
            status_line = response.headers.splitlines()[0]
            response.status_code = int(status_line.split()[1])
        else:
            response.status_code = None
            
        if response.status_code:
            response.text = stdout
        else:
            response.text = None
        
        return response


    def patch(self, url, payload):
        curl_command = ['curl', '-X', 'PATCH', '-v', '-s']
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
        if response.headers[0:4] == "HTTP":
            status_line = response.headers.splitlines()[0]
            response.status_code = int(status_line.split()[1])
        else:
            response.status_code = None
            
        if response.status_code:
            response.text = stdout
        else:
            response.text = None
        
        return response


def read_json(jsonfile, exit_on_fail=False):

    if not os.path.exists(jsonfile):
        return {}

    try:
        with codecs.open(jsonfile, mode='r', encoding='utf-8') as f:
            tstjson = json.loads(to_unicode(f.read()))

    except ValueError:
        msg = "tst: %s is corrupted" % jsonfile
        if exit_on_fail:
            print(msg, file=sys.stderr)
            sys.exit()

        raise CorruptedConfigFile(msg)

    return tstjson


def read_tstjson(exit=False, quit_on_fail=False):

    if not os.path.exists(TSTJSON):
        if quit_on_fail:
            msg = "tst: not a tst directory"
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


def get_release():
    try:
        with codecs.open(TSTRELEASE, mode='r', encoding='utf-8') as f:
            release = f.read().split('"')[3]
    except:
        release = ''

    return release


def read_config(exit=False):

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

    return config


def save_config(config):
    with codecs.open(TSTCONFIG, mode="w", encoding='utf-8') as f:
        f.write(json.dumps(
            config,
            indent=2,
            separators=(',', ': ')
        ))


def save_json(jsondata, jsonfile):
    with codecs.open(jsonfile, mode="w", encoding='utf-8') as f:
        f.write(json.dumps(
            jsondata,
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
