from __future__ import print_function

import tst
import sys
import os

from urlparse import urlparse

from tst.colors import *
from tst.utils import cprint
from tst.utils import _assert
from tst.utils import is_posix_filename
from tst.utils import data2json
from tst.jsonfile import JsonFile

def main():
    assert sys.argv[0].endswith('/tst') and sys.argv[1] == 'checkout'
    checkout(sys.argv[2:])


def syntax_help():
    return LRED + "This is not a tst directory.\n" + RESET +\
           "Usage: tst checkout <key>[@<site>] [<directory>]\n"\
           "       tst checkout <url> [<directory>]\n\n"\
           "   or: tst checkout\n"\
           "       (inside a tst directory)"\


def process_args(args):
    _assert(0 <= len(args) <= 3, syntax_help())

    # process overwrite argument
    YES = ["--yes", "-y"]
    overwrite = any(yes in args for yes in YES)
    args = [e for e in args if e not in YES]

    # add default args
    if len(args) == 0:
        cwd = os.getcwd()
        _assert(tst.dirtype(cwd) == "assignment", "This directory is not a tst activity")
        args.append(os.path.basename(cwd))
        args.append(".")

    elif len(args) == 1 and os.path.isdir(args[0]):
        tst_object = JsonFile(args[0] + "/.tst/assignment.json")
        _assert("key" in tst_object, "No key found in tst object")
        _assert("site" in tst_object, "No site found in tst object")
        args = ["%s@%s" % (tst_object["key"], tst_object["site"]), args[0]]

    data = { "destdir": args[1] if len(args) > 1 else None }

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
    else:
        _assert(False, "Unrecognized key/url")


    # get site based either on sitename or url
    assert data['site'] is None or data['url'] is None
    site = tst.get_site(name=data['site']) if data['site'] else tst.get_site(url=url)
    _assert(site and site.url, "No site/url identified. Check your config.yaml")

    return site, data['key'], data['destdir'], overwrite


def existing_files(basedir, files):
    filenames = []
    for f in files:
        fullname = "%s/%s" % (basedir, f['name'])
        if os.path.exists(fullname):
            filenames.append(fullname)

    return filenames


def checkout(args):
    """checkout tst object from site/collection"""

    def is_valid_dir(dirtype):
        return dirtype in [None, "assignment"]

    # parse user arguments
    site, key, target_dir, overwrite = process_args(args)

    # fetch tst object
    cprint(LGREEN, "Fetching %s from %s" % (key, site.name or site.url))
    tst_object = site.get(key)
    _assert(tst_object is not None, "No tst object found in site")

    # set destination directory
    destdir = target_dir or tst_object.get('dirname') or tst_object.get('name') or key
    _assert(not os.path.exists(destdir) or (os.path.isdir(destdir) and is_valid_dir(tst.dirtype(destdir))), "Invalid target directory: %s" % destdir)

    # check whether files exist
    old_files = existing_files(destdir, tst_object['files'])
    if old_files and not overwrite:
        cprint(YELLOW, "If you proceed, these files will be overwriten")
        for fn in old_files:
            cprint(LCYAN, fn)

        cprint(YELLOW, "Proceed (y/n)? ", end="")
        if raw_input() != "y":
            cprint(LRED, "Aborting check out")
            sys.exit(1)

    # save files
    saved = tst.save_files(tst_object['files'], destdir)
    cprint(LBLUE, "%d files saved to %s%s%s directory" % (saved, LCYAN, destdir, LBLUE))
    if len(tst_object['files']) > saved:
        cprint(YELLOW, "%d files were NOT saved" % (len(tst_object['files']) - saved))

    internal = [{
        "name": ".tst/assignment.json",
        "content": data2json({
            "kind": "assignment",
            "site": site.name,
            "key": key,
        })
    }]
    tst.save_files(internal, destdir, verbose=False)
