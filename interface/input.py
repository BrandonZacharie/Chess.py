from curses import (
    A_COLOR,
    KEY_BACKSPACE,
    KEY_DC,
    KEY_DOWN,
    KEY_END,
    KEY_ENTER,
    KEY_EOL,
    KEY_EXIT,
    KEY_HOME,
    KEY_LEFT,
    KEY_NPAGE,
    KEY_PPAGE,
    KEY_RIGHT,
    KEY_UP,
    curs_set,
)
from curses import window as Window
from curses.ascii import BS, DEL, ENQ, ESC, LF, SOH, VT
from enum import IntEnum
from os import getcwd, path
from typing import Callable, Optional


class KeyCode(IntEnum):
    BACKSPACE = KEY_BACKSPACE
    DC = KEY_DC
    DOWN = KEY_DOWN
    END = KEY_END
    ENTER = KEY_ENTER
    EOL = KEY_EOL
    EXIT = KEY_EXIT
    HOME = KEY_HOME
    LEFT = KEY_LEFT
    NPAGE = KEY_NPAGE
    PPAGE = KEY_PPAGE
    RIGHT = KEY_RIGHT
    UP = KEY_UP
    BS = BS
    DEL = DEL
    ENQ = ENQ
    ESC = ESC
    LF = LF
    SOH = SOH
    VT = VT


def fileprompt(
    window: Window,
    filename: Optional[str] = None,
    handler: Optional[Callable[[str], bool]] = None,
):
    x = 5
    y = 5

    if filename is None:
        filename = path.realpath(path.join(getcwd(), path.dirname(__file__))) + path.sep

    prompt = "〉" + filename

    window.move(y, x)
    window.clrtobot()
    window.addstr(y, x, "Enter the file path: ")

    y += 1
    cursor = len(prompt) + 1

    window.addstr(y, x, prompt)
    curs_set(2)

    while True:
        match window.getch():
            case KeyCode.EXIT | KeyCode.ESC:
                break
            case KeyCode.DOWN | KeyCode.UP:
                continue
            case KeyCode.ENTER | KeyCode.EOL | KeyCode.LF:
                window.addstr(y + 2, x, "Loading...", A_COLOR)
                window.clrtoeol()
                window.refresh()

                if handler is None or handler(prompt[1:]):
                    return

                window.clrtobot()
            case KeyCode.LEFT:
                if cursor > 2:
                    cursor -= 1
            case KeyCode.RIGHT:
                if cursor < len(prompt) + 1:
                    cursor += 1
            case KeyCode.VT:
                prompt = prompt[: cursor - 1]

                window.addstr(y, x, prompt)
                window.clrtoeol()
            case KeyCode.HOME | KeyCode.SOH:
                cursor = 2
            case KeyCode.END | KeyCode.ENQ:
                cursor = len(prompt) + 1
            case KeyCode.BACKSPACE | KeyCode.BS | KeyCode.DEL:
                if cursor > 2:
                    prompt = prompt[: cursor - 2] + prompt[cursor - 1 :]
                    cursor -= 1

                    window.addstr(y, x, prompt)
                    window.clrtoeol()
            case KeyCode.DC:
                if cursor < len(prompt) + 1:
                    prompt = prompt[: cursor - 1] + prompt[cursor:]

                    window.addstr(y, x, prompt)
                    window.clrtoeol()
            case key if 0 <= key < 0x100:
                prompt = prompt[: cursor - 1] + chr(key) + prompt[cursor - 1 :]
                cursor += 1

                window.addstr(y, x, prompt)
            case _:
                pass

        window.move(y, cursor + x)

    raise KeyboardInterrupt
