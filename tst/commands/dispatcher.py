import os
import sys
import logging
from subprocess import check_call, CalledProcessError
from distutils.spawn import find_executable

import tst
from tst.colors import *
from tst.utils import cprint

config = tst.get_config()
log = logging.getLogger('dispatcher')
handler_file = logging.FileHandler(os.path.expanduser('~/.tst/logs'))
handler_file.setFormatter(logging.Formatter('%(asctime)s|%(name)s|%(levelname)s|%(message)s'))
log.addHandler(handler_file)
log.setLevel(logging.DEBUG)


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


def dispatcher(args):
    args.pop(0) # pop script name

    first_arg = args[0] if args else None
    if first_arg in ['--version', '-v', 'version']:
        import tst.commands.version as version
        version.main()

    elif find_executable(f'tst-{first_arg}'):
        cprint(YELLOW, f"external command: tst-{first_arg}")
        command_name = args.pop(0)
        run_external_command(command_name, args)

    else:
        import tst.commands.test as test
        test.main()


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
        dispatcher(args)

    except KeyboardInterrupt:
        cprint(LRED, "\nUser interruption")

    except (AssertionError, Exception) as e:
        cprint(LRED, "sorry, critical error")
        log.error(e)
        cprint(LRED, f"{e.__class__.__name__}: {e}")

