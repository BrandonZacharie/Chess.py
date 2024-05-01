from curses import (
    A_COLOR,
    A_NORMAL,
    A_REVERSE,
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
    doupdate,
    panel,
    wrapper,
)
from curses.ascii import BS, DEL, ENQ, ESC, LF, SOH, VT
from enum import IntEnum
from functools import partial
from os import getcwd, path
from typing import TYPE_CHECKING, Callable, List, Optional, Tuple, TypeAlias, cast

from cli import draw_head, main
from dateutil.parser import parse

from game import Game, PGNFile

if TYPE_CHECKING:
    from _curses import _CursesWindow

    CursesWindow = _CursesWindow
else:
    from typing import Any

    CursesWindow = Any

MenuItems: TypeAlias = List[Tuple[str, Optional[Callable]]]


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


class Menu(object):
    def __init__(self, items: MenuItems, window: CursesWindow):
        self._pages: Optional[List[MenuItems]] = None
        self.window = window.subwin(3, 4)
        self.position = 0
        self.page = 0
        self.page_size = 25
        self.items = items
        self.panel = panel.new_panel(self.window)

        self.items.append(("exit", None))
        self.panel.hide()
        panel.update_panels()
        self.window.keypad(True)

    @property
    def pages(self) -> List[MenuItems]:
        if self._pages is None:
            self._pages = [
                self.items[i : i + self.page_size]
                for i in range(0, len(self.items), self.page_size)
            ]

        return self._pages

    def insert(self, index: int, item: Tuple[str, Optional[Callable]]):
        self.items.insert(index, item)

        self._pages = None

    def navigate(self, n) -> None:
        self.position += n
        prev_page = self.page

        if self.position < 0:
            self.page = max(0, self.page - 1)
            next_page_size = len(self.pages[self.page])
            self.position = (
                0 if self.page == prev_page else max(self.position + next_page_size, 0)
            )

            return

        prev_page_size = len(self.pages[prev_page])

        if self.position >= prev_page_size:
            self.page = min(len(self.items) // self.page_size, self.page + 1)
            next_page_size = len(self.pages[self.page])
            self.position = (
                next_page_size - 1
                if self.page == prev_page
                else min(self.position - prev_page_size, next_page_size - 1)
            )

    def display(self) -> None:
        self.panel.top()
        self.panel.show()
        self.window.clear()

        try:
            while True:
                self.window.refresh()
                doupdate()
                curs_set(0)

                for index, item in enumerate(self.pages[self.page]):
                    mode = A_REVERSE if index == self.position else A_NORMAL
                    msg = (
                        f" ↵  {item[0]}  "
                        if item[1] is None
                        else " %d. %s  "
                        % (index + 1 + (self.page * self.page_size), item[0])
                    )

                    self.window.addstr(1 + index, 1, msg, mode)

                key = self.window.getch()

                match key:
                    case KeyCode.ENTER | KeyCode.LF:
                        fn = self.items[self.position][1]

                        if fn is None:
                            break

                        fn()
                    case KeyCode.UP:
                        self.navigate(-1)
                    case KeyCode.PPAGE:
                        self.navigate(-self.page_size)
                    case KeyCode.DOWN:
                        self.navigate(1)
                    case KeyCode.NPAGE:
                        self.navigate(self.page_size)
                    case KeyCode.EXIT | KeyCode.HOME | KeyCode.ESC:
                        break

                self.window.clear()
                self.panel.hide()
                panel.update_panels()
                doupdate()
        except KeyboardInterrupt:
            pass


class Chess(object):
    def __init__(self, window: CursesWindow):
        draw_head(window)

        class Menus:
            main = Menu(
                [
                    ("new game", self.play),
                    ("load file", self.load),
                    ("about", self.draw_about),
                ],
                window,
            )
            load = Menu(
                [
                    ("PGN", self.load_pgn),
                    ("JSON", self.load_json),
                ],
                window,
            )

        self.window = window
        self.game: Optional[Game] = None
        self.menus = Menus()

        self.menus.main.display()

    def play(self, game: Optional[Game] = None):
        if self.game is None:
            self.menus.main.insert(0, ("continue", lambda: self.play(self.game)))

        self.game = Game() if game is None else game

        main(self.window, self.game)

        self.menus.main.position = 0

    def load(self):
        self.menus.load.display()

        self.menus.load.position = 0

    def load_pgn(self):
        x = 5
        y = 4
        prompt = (
            "〉" + path.realpath(path.join(getcwd(), path.dirname(__file__))) + path.sep
        )

        self.window.move(y, x)
        self.window.clrtobot()
        self.window.addstr(y, x, "Enter the file path: ")

        y += 1
        cursor = len(prompt) + 1

        self.window.addstr(y, x, prompt)
        curs_set(2)

        while True:
            match self.window.getch():
                case KeyCode.EXIT | KeyCode.ESC:
                    break
                case KeyCode.DOWN | KeyCode.UP:
                    continue
                case KeyCode.ENTER | KeyCode.EOL | KeyCode.LF:
                    self.window.addstr(y + 2, x, "Loading...", A_COLOR)
                    self.window.refresh()

                    try:
                        pgn_file = PGNFile(prompt[1:])

                        if len(pgn_file) == 0:
                            self.window.addstr(y + 2, x, "No games found.", A_COLOR)
                        else:
                            menu = Menu(
                                [
                                    (
                                        f"{parse(cast(str, game.date).replace('.??', ''), fuzzy=True).date()} \"{game.event}\" {game.white} vs. {game.black}",
                                        partial(
                                            lambda i: self.play(pgn_file.game(i)), i
                                        ),
                                    )
                                    for i, game in enumerate(pgn_file)
                                ],
                                self.window,
                            )

                            menu.display()

                        break
                    except FileNotFoundError:
                        self.window.addstr(y + 2, x, "File not found.", A_COLOR)
                    except Exception as e:
                        self.window.addstr(y + 2, x, f"Error: {e}", A_COLOR)
                case KeyCode.LEFT:
                    if cursor > 2:
                        cursor -= 1
                case KeyCode.RIGHT:
                    if cursor < len(prompt) + 1:
                        cursor += 1
                case KeyCode.VT:
                    prompt = prompt[: cursor - 1]

                    self.window.addstr(y, x, prompt)
                    self.window.clrtoeol()
                case KeyCode.HOME | KeyCode.SOH:
                    cursor = 2
                case KeyCode.END | KeyCode.ENQ:
                    cursor = len(prompt) + 1
                case KeyCode.BACKSPACE | KeyCode.BS | KeyCode.DEL:
                    if cursor > 2:
                        prompt = prompt[: cursor - 2] + prompt[cursor - 1 :]
                        cursor -= 1

                        self.window.addstr(y, x, prompt)
                        self.window.clrtoeol()
                case KeyCode.DC:
                    if cursor < len(prompt) + 1:
                        prompt = prompt[: cursor - 1] + prompt[cursor:]

                        self.window.addstr(y, x, prompt)
                        self.window.clrtoeol()
                case key:
                    prompt = prompt[: cursor - 1] + chr(key) + prompt[cursor - 1 :]
                    cursor += 1

                    self.window.addstr(y, x, prompt)

            self.window.move(y, cursor + x)

        raise KeyboardInterrupt

    def load_json(self):
        pass

    def draw_about(self):
        y = 4

        self.window.move(y, 0)
        self.window.clrtobot()
        self.window.addstr(y + 0, 6, f"© 2021 Brandon Zacharie", A_COLOR)
        self.window.addstr(y + 2, 6, "github: BrandonZacharie/Chess.py", A_COLOR)
        self.window.addstr(y + 3, 6, f"semver: {Game.VERSION}", A_COLOR)
        self.window.addstr(y + 5, 6, "Press any key to continue...")
        self.window.getch()


if __name__ == "__main__":
    wrapper(Chess)
