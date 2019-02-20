from __future__ import print_function

import tst
import sys
import os

from urlparse import urlparse

from tst.colors import *
from tst.utils import cprint, _assert, is_posix_filename
from tst.jsonfile import JsonFile

def main():
    assert sys.argv[0].endswith('/tst') and sys.argv[1] == 'checkout'
    checkout(sys.argv[2:])

def is_url(s):
    return s.startswith("http://")


def syntax_help():
    return "Syntax:\n"\
           "  - tst checkout <url>\n"\
           "  - tst checkout <key>\n"\
           "  - tst checkout <key@site>\n"


def parse_cli_args(args):
    _assert(1 <= len(args) <= 2, syntax_help())

    data = { "destdir": args[1] if len(args) > 1 else os.getcwd() }

    key_or_url = args[0]
    url = urlparse(key_or_url)
    _assert(not url.fragment, "Fragments not supported in url")
    _assert(not url.username, "Usernames not supported in url")
    _assert(not url.password, "Passwords not supported in url")

    if url.scheme == 'http':
        # key_or_url == "http://.../key"
        path, key = url.path.rsplit("/", 1) if "/" in url.path else (url.path, '')
        data["url"] = "%s://%s%s" % (url.scheme, url.netloc, path)
        data["site"] = None
        data["key"] = key

    elif is_posix_filename(key_or_url, extra_chars="@"):
        num_ats = key_or_url.count("@")
        if num_ats == 0:
            # key_or_url == "key"
            data["url"] = None
            data["site"] = "_DEFAULT"
            data["key"] = key_or_url

        elif num_ats == 1:
            # key_or_url == "key@site"
            key, sitename = key_or_url.split("@")
            data["url"] = None
            data["site"] = sitename
            data["key"] = key

    return data['site'], data['key'], data['url'], data['destdir']


def checkout(args):
    """checkout tst object from site/collection"""

    sitename, key, url, destdir = parse_cli_args(args)
    assert tst.dirtype(destdir) is None

    site = tst.get_site(name=sitename, url=url)
    _assert(site, "No site identified")
    _assert(site.url, "Couldn't determine site url. Check your config.yaml file.")

    tst_object = site.get(key)
    _assert(tst_object is not None, "No tst object found in site")
    tst.save2fs(tst_object)
