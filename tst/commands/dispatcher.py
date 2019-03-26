from __future__ import print_function

import os
import sys
from subprocess import check_call, CalledProcessError

import tst
from tst.colors import *
from tst.utils import cprint

EXTERNALS = [
    "test",
    "commit",
    "status",
    "new",
    "delete",
]
DEFAULT_COMMAND = "test"


def run_external_command(command, args):
    script_name = os.path.expanduser("tst-%s" % command)
    args.insert(0, script_name)
    try:
        check_call(args)
    except CalledProcessError:
        pass
    except OSError:
        print("tst: couldn't run command '%s'" % command, file=sys.stderr)


def identify_and_run_command(args):
    from distutils.spawn import find_executable
    if args and (args[0] in EXTERNALS):
        command_name = args.pop(0)
        run_external_command(command_name, args)

    elif args and find_executable('tst-%s' % args[0]):
        command_name = args.pop(0)
        cprint(YELLOW, "┌───────────────────────────────────┐")
        cprint(YELLOW, "│ WARNING: this is a custom command │")
        cprint(YELLOW, "└───────────────────────────────────┘")
        run_external_command(command_name, args)
        cprint(YELLOW, "┌───────────────────────────────────┐")
        cprint(YELLOW, "│ WARNING: this is a custom command │")
        cprint(YELLOW, "└───────────────────────────────────┘")
            
    else: # neither internal, nor external command!?
        command_name = DEFAULT_COMMAND
        run_external_command(command_name, args)

    return command_name


def version():
    import pkg_resources
    import requests

    current_version = pkg_resources.get_distribution('tst').version
    cprint(WHITE, current_version)
    try:
        response = requests.get('https://pypi.org/pypi/tst/json')
        data = response.json()
        latest_version = data['info']['version']
        if current_version != latest_version:
            cprint(YELLOW, 'tst %s is available' % latest_version)
            print('Use `pip install --upgrade tst`')
            sys.exit()
    except requests.ConnectionError:
        pass


def dispatcher(args):
    possible_command = args[0] if args else None
    if possible_command in ['--version', '-v', 'version']:
        version()
        sys.exit()

    elif possible_command == 'info':
        import info
        info.main()

    elif possible_command == 'login':
        import login
        login.main()

    elif possible_command == 'ls':
        import ls
        ls.main()

    elif possible_command == 'checkout':
        dirtype = tst.dirtype()
        if dirtype == "old:activity":
            cprint(YELLOW, "┌─────────────────────────────────────────────────────────┐")
            cprint(YELLOW, "│ IMPORTANT                                               │")
            cprint(YELLOW, "│                                                         │")
            cprint(YELLOW, "│ This is an old style activity. The old checkout command │")
            cprint(YELLOW, "│ will be used.                                           │")
            cprint(YELLOW, "└─────────────────────────────────────────────────────────┘")
            run_external_command("checkout", args[1:])

        elif dirtype not in [None, "assignment"]:
            cprint(LRED, "┌───────────────────────────────────────────────┐")
            cprint(LRED, "│ checkout cannot be executed in this directory │")
            cprint(LRED, "│                                               │")
            cprint(LRED, "│ Currently, the checkout command must be used  │")
            cprint(LRED, "│ in a non tst directory.                       │")
            cprint(LRED, "└───────────────────────────────────────────────┘")

        else:
            import checkout
            checkout.main()

    elif possible_command == 'update':
        cprint(LRED, "┌─────────────────────────────────────┐")
        cprint(LRED, "│ update is deprecated                │")
        cprint(LRED, "│                                     │")
        cprint(LRED, "│ Use pip to update tst:              │")
        cprint(LRED, "│ $ pip install tst --upgrade --user  │")
        cprint(LRED, "└─────────────────────────────────────┘")

    elif possible_command == 'config':
        cprint(LRED, "┌────────────────────────────────────────────────────┐")
        cprint(LRED, "│ config is deprecated                               │")
        cprint(LRED, "│                                                    │")
        cprint(LRED, "│ Edit ~/.tst/config.yaml directly to configure tst. │")
        cprint(LRED, "│ See documentation to see existing options.         │")
        cprint(LRED, "└────────────────────────────────────────────────────┘")

    else:
        command = identify_and_run_command(args)


def main():
    args = sys.argv[:]
    args.pop(0) # pop dispatcher name
    config = tst.get_config()
    dispatcher(args) 
