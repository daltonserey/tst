from __future__ import print_function

import sys
import os
import webbrowser
import logging

from requests import ConnectionError

import tst
from tst.colors import *
from tst.utils import cprint, data2json, _assert
from tst.jsonfile import JsonFile

def main():
    sitename = sys.argv[2] if len(sys.argv) > 2 else '_DEFAULT'
    login(sitename)


def login(sitename):
    """login in site"""

    # fetch site urls
    site = tst.get_site(sitename)
    _assert(site is not None, "Site %s not found in config.yaml" % sitename)

    login_url = site.login_url()
    token_url = site.token_url()
    _assert(login_url and token_url, "Site %s has no login urls" % site.name)

    # open login url to user
    cprint(LGREEN, "Get a code at: %s" % login_url)
    webbrowser.open(login_url)
    code = raw_input(LCYAN + "Code? " + RESET)

    # exchange code for token
    cprint(RESET, "Validating code: %s" % code)

    try:
        response = site.post(token_url, data={"code": code})
        _assert(response.ok, "Login failed")
    except ConnectionError:
        _assert(False, "Connection failed... check your internet connection")

    response.encoding = 'utf-8'
    try:
        token = response.json()
    except ValueError:
        _assert(False, "Server didn't send json")

    # save token
    tokens = JsonFile(os.path.expanduser('~/.tst/tokens.json'))
    tokens[site.name] = token['tst_token']
    tokens.writable = True
    tokens.save()

    msg = "Logged in %s as %s" % (site.name, token['email'])
    cprint(LGREEN, msg)
    logging.info(msg)
