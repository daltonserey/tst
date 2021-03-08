from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from builtins import input

import tst
import sys
import os

from urllib.parse import urlparse

from tst.colors import *
from tst.utils import cprint
from tst.utils import _assert
from tst.utils import is_posix_filename
from tst.utils import data2json
from tst.jsonfile import JsonFile

def main():
    assert sys.argv[0].endswith('tst') and sys.argv[1] == 'checkout'

    # parse user arguments
    args = sys.argv[2:]
    site, key, target_dir, overwrite = process_args(args)

    checkout(site, key, target_dir, overwrite)


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
        ## no args: use current directory
        cwd = os.getcwd()
        _assert(tst.dirtype(cwd) == "assignment", "This directory is not a tst activity")
        args.append(os.path.basename(cwd))
        args.append(".")

    elif len(args) == 1 and os.path.isdir(args[0]):
        ## single directory as arg: make sure is a checkout
        checkout_file = args[0] + "/.tst/assignment.json"
        _assert(os.path.exists(checkout_file), "Directory %s has no checkout info\n%sTry: tst checkout key <new-directory>" % (args[0], RESET))
        tst_object = JsonFile(checkout_file)
        _assert("key" in tst_object, "Checkout corrupted: missing key")
        _assert("site" in tst_object, "Checkout corrupted: missing site")
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


def checkout(site, key, target_dir, overwrite):
    """checkout activity/assignment from site/collection"""

    def is_valid_dir(dirtype):
        return dirtype in [None, "assignment"]

    # fetch activity
    cprint(LGREEN, "Fetching %s from %s" % (key, site.name or site.url))
    activity, response = site.get_activity(key)
    if response.status_code == 404:
        activity, response = site.get_directory(key)

    if response.status_code == 401:
        cprint(LRED, 'Checkout failed (%s)' % site.last_response.status_code)
        cprint(WHITE, 'run: tst login')
        return

    elif response.status_code == 404:
        cprint(LRED, 'Checkout failed (%s)' % site.last_response.status_code)
        cprint(LRED, 'Assignment not found')
        return

    elif response.status_code == 412:
        cprint(LRED, 'Checkout failed (%s)' % site.last_response.status_code)
        cprint(LRED, 'Error: %s' % site.last_response.json()['messages'][0])
        return

    _assert(activity, "CANNOT checkout %s from site %s (%s)" % (key, site.name, response.status_code))

    # set destination directory
    destdir = target_dir or activity.get('dirname') or activity.get('name') or key
    if not target_dir:
        cprint(YELLOW, "Directory argument not found")
        cprint(RESET, "(You can add directory as an additional argument)")
        while True:
            destdir = input("Provide directory name (default %s): " % destdir) or key
            if is_posix_filename(destdir, extra_chars="/"): break
            cprint(YELLOW, "Invalid portable posix filename: '%s'" % destdir)

    _assert(not os.path.exists(destdir) or (os.path.isdir(destdir) and is_valid_dir(tst.dirtype(destdir))), "Invalid target directory: %s" % destdir)

    # check whether files exist
    old_files = existing_files(destdir, activity['files'])
    if old_files and not overwrite:
        cprint(YELLOW, "If you proceed, these files will be overwriten")
        for fn in old_files:
            cprint(LCYAN, fn)

        cprint(YELLOW, "Proceed (y/N)? ", end="")
        if input() != "y":
            cprint(LRED, 'Aborting checkout')
            sys.exit(1)

    # save files
    saved = tst.save_files(activity['files'], destdir)
    cprint(LBLUE, "%d files saved to %s%s%s directory" % (saved, LCYAN, destdir, LBLUE))
    if len(activity['files']) > saved:
        cprint(YELLOW, "%d files were NOT saved" % (len(activity['files']) - saved))

    internal = [{
        "name": ".tst/assignment.json",
        "content": data2json({
            "kind": "assignment",
            "site": site.name,
            "key": key,
            "iid": activity.get('iid'),
            "user": activity.get('user'),
        })
    }]
    tst.save_files(internal, destdir, verbose=False)
