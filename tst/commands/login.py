from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from builtins import input
from uuid import getnode as get_mac

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


def login_old(sitename):
    """login in site"""

    # fetch site urls
    site = tst.get_site(sitename)
    _assert(site is not None, "Site %s not found in config.yaml" % sitename)

    login_url = site.login_url()
    token_url = site.token_url()
    _assert(login_url, "Site %s has no login url" % site.name)
    _assert(token_url, "Site %s has no token url" % site.name)

    # open login url to user
    cprint(LGREEN, "Get a code at: %s" % login_url)
    webbrowser.open(login_url)
    code = input(LCYAN + "Code? " + RESET)

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


def login(sitename):
    """login in site"""

    # fetch site urls
    site = tst.get_site(sitename)
    _assert(site is not None, "Site %s not found in config.yaml" % sitename)

    # check site login style
    auth_url = site.auth_url()
    access_url = site.access_url()
    if not auth_url or not access_url:
        return login_old(sitename)

    # proceed with new login
    login_url = site.login_url()
    access_url = site.access_url()
    #auth_url = site.auth_url()
    #_assert(login_url and access_url and auth_url, "Site %s has no login urls" % site.name)

    # request login token
    #cprint(LGREEN, "Starting login at %s" % login_url)
    response = site.post(login_url, {"mac": str(get_mac())})
    response.encoding = 'utf-8'
    login_token = response.json()['code']

    # open browser at authorization page
    web_url = 'http://tk0.tst-online.appspot.com/activate/#/code/%s' % login_token
    cprint(LGREEN, f"Hit ⟨Enter⟩ to open up the browser to login in {site.name}")
    input()
    if not webbrowser.open(web_url):
        cprint(LYELLOW, "Sorry, I cannot open the browser, visit:")
        cprint(LYELLOW, web_url)

    # request access
    cprint(YELLOW, access_url)
    for i in range(3):
        cprint('LCYAN', f'Tentando o get número {i} no site')
        response = site.get(f'{access_url}?code={login_token}')
        authorization = response.json()
        if response.status_code == 200: break

    # check authorization
    if not authorization['authorized']:
        cprint(LRED, 'Ooops! Not authorized')
        logging.info('login not authorized')
        sys.exit(1)

    # check whether the login worked
    if not 'tst_token' in authorization:
        cprint(LRED, 'Sorry, login failed')
        logging.info('no tst_token in authorized login')
        return

    # save token
    tokens = JsonFile(os.path.expanduser('~/.tst/tokens.json'))
    tokens[site.name] = authorization['tst_token']
    tokens.writable = True
    tokens.save()

    msg = "Logged in %s as %s" % (site.name, authorization['email'])
    cprint(LGREEN, msg)
    logging.info(msg)
