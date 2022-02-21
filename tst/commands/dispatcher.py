import os
import sys
import logging
from subprocess import check_call, CalledProcessError

import tst
from tst.colors import *
from tst.utils import cprint

config = tst.get_config()
log = logging.getLogger('dispatcher')
handler_file = logging.FileHandler(os.path.expanduser('~/.tst/logs'))
handler_file.setFormatter(logging.Formatter('%(asctime)s|%(name)s|%(levelname)s|%(message)s'))
log.addHandler(handler_file)
log.setLevel(logging.DEBUG)

EXTERNALS = [
    "test",
    "status",
]
DEFAULT_COMMAND = "test"

def run_external_command(command, args):
    script_name = os.path.expanduser("tst-%s" % command)
    args.insert(0, script_name)
    try:
        exit = check_call(args)
    except CalledProcessError as e:
        sys.exit(e.returncode)
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
        run_external_command(command_name, args)

    else: # neither internal, nor external command!?
        command_name = DEFAULT_COMMAND
        run_external_command(command_name, args)

    return command_name


def dispatcher(args):
    possible_command = args[0] if args else None
    if possible_command in ['--version', '-v', 'version']:
        import tst.commands.version as version
        version.main()

    elif possible_command == 'info':
        import tst.commands.info as info
        info.main()

    elif possible_command == 'ls':
        import tst.commands.ls as ls
        ls.main()

    else:
        command = identify_and_run_command(args)


def main():
    if os.name != "posix":
        osplatform = f"{os.name}/{sys.platform}"
        print("┌────────────────────────────────────────────────────┐")
        print("│ Ops... sorry,                                      │")
        print("│ tst was designed to run on unix like sysyems       │")
        print("│ (unix, linux, macos, etc.)                         │")
        print("│                                                    │")
        print(f"│ It seems your system is: {osplatform:26.26}│")
        print("└────────────────────────────────────────────────────┘")
        sys.exit(1)

    try:
        args = sys.argv[:]
        args.pop(0) # pop dispatcher name
        dispatcher(args)
    except AssertionError as e:
        cprint(LRED, e)

    except KeyboardInterrupt:
        cprint(LRED, "\nUser interruption")
