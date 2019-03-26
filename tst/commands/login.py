from __future__ import print_function

import tst
import sys
import os
import webbrowser

import requests
from cachecontrol import CacheControl
from cachecontrol.caches.file_cache import FileCache

from tst.colors import *
from tst.utils import cprint, data2json, _assert
from tst.jsonfile import JsonFile

def main():
    sitename = sys.argv[2] if len(sys.argv) > 2 else '_DEFAULT'
    login(sitename)


def post(url, data):
    s = requests.session()
    s = CacheControl(s, cache=FileCache(os.path.expanduser('~/.tst/cache')))

    try:
        response = s.post(url, data=data2json(data), allow_redirects=True)
    except requests.ConnectionError:
        _assert(False, "Connection failed... check your internet connection")

    if not response.ok:
        print(response.text)
    _assert(response.ok, "Login failed.")

    response.encoding = 'utf-8'
    try:
        token = response.json()

    except ValueError:
        _assert(False, "Server didn't send json")

    return token


def login(sitename):
    """login in site"""

    # fetch site urls
    site = tst.get_site(sitename)
    login_url = site.login_url()
    _assert(login_url, "Site %s has no login" % site.name)
    token_url = site.token_url()
    _assert(token_url, "Site %s has no login" % site.name)

    # open login url to user
    webbrowser.open(login_url)
    code = raw_input("Code? ")

    # exchange code for token
    print("Validating code: %s" % code)
    token = post(token_url, {"code": code})
    print("Code validated")

    # save token
    tokens = JsonFile(os.path.expanduser('~/.tst/tokens.json'))
    tokens[site.name] = token['tst_token']
    tokens.writable = True
    tokens.save()

    print("Logged in %s as %s" % (site.name, token['email']))
