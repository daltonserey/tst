# coding: utf-8
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from builtins import input, str

import sys
import curses
from curses import wrapper

def find_getch():
    try:
        import termios
    except ImportError:
        # Non-POSIX. Return msvcrt's (Windows') getch.
        import msvcrt
        return msvcrt.getch

    # POSIX system. Create and return a getch that manipulates the tty.
    import tty
    def _getch():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

    return _getch


def climenu(options, try_curses=False, prompt=None):
    if type(options) is dict:
        items = [(str(k), options[k]) for k in options]
        original_keys = {str(k): k for k in options.keys()}
    else:
        items = [(str(i + 1), options[i]) for i in range(len(options))]
        original_keys = {str(i + 1): i for i in range(len(options))}

    single_char_keys = all(len(str(k)) == 1 for k, text in items)
    items.sort(key=lambda e: "%05d" % int(e[0]) if str(e[0]).isdigit() else e[0])
    if try_curses and single_char_keys:
        selected = wrapper(menu_curses, items, prompt)
    else:
        selected = menu_term(items, prompt)

    return original_keys[selected]


def menu_term(items, prompt=None):
    for key, text in items:
        print('%s: %s' % (key, text), file=sys.stderr)

    options_keys = [key for key, text in items]
    single_char_keys = all(len(k) == 1 for k in options_keys)
    read_input = find_getch() if single_char_keys else input
    while True:
        print(prompt or '', end='')
        key = read_input()
        if key in options_keys: break

    return key


def menu_curses(stdscr, items, prompt):
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    assert h > len(items), "oops… screen is too small for menu"
    first_line = h - len(items) - (1 if prompt else 0)
    for i in range(len(items)):
        key = items[i][0]
        value = items[i][1]
        stdscr.addstr(first_line + i, 0, "%s. %s" % (key, value), curses.A_BOLD)

    keys_codes = [ord(key) for key, text in items]
    while True:
        if prompt:
            stdscr.addstr(h-1, 0, prompt)
            stdscr.refresh()
        key_code = stdscr.getch()
        if key_code in keys_codes: break

    return chr(key_code)
