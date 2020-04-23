from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from builtins import str

import sys
import signal
import json

from subprocess import Popen, PIPE, CalledProcessError

import tst
from colors import *
from utils import to_unicode, cprint

class ConnectionFail(Exception): pass

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
        #self.config = Config()
        self.config = tst.get_config()
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
        except: # timeout!!!
            process.terminate()
            raise

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
        for i in range(len(response_lines)-1, -1, -1):
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


    def delete(self, path, payload='', headers={}, exit_on_fail=False):
        return self.request('delete', path, headers=headers, payload=payload, exit_on_fail=exit_on_fail)
