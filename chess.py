from curses import (
    A_BOLD,
    A_COLOR,
    A_DIM,
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

from cli import LogStyle, draw_head, main
from dateutil.parser import parse

from game import Game, PGNFile

if TYPE_CHECKING:
    from _curses import _CursesWindow

    CursesWindow = _CursesWindow
else:
    from typing import Any

    CursesWindow = Any

MenuItems: TypeAlias = List[
    Tuple[str, Optional[Callable]] | Tuple[str, Optional[Callable], int]
]


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
    def __init__(
        self,
        items: MenuItems,
        window: CursesWindow,
        title: Optional[str] = None,
    ):
        self._pages: Optional[List[MenuItems]] = None
        self.window = window.subwin(3, 4)
        self.title = title
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

                y = 0

                if self.title is not None:
                    self.window.addstr(y, 2, "↳ " + self.title)

                    y += 1

                y += 1

                for index, item in enumerate(self.pages[self.page]):
                    msg = (
                        f" ↵  {item[0]}  "
                        if item[1] is None
                        else " %d. %s  "
                        % (index + 1 + (self.page * self.page_size), item[0])
                    )
                    mode = A_REVERSE if index == self.position else A_NORMAL

                    if len(item) == 3:
                        mode |= item[2]

                    self.window.addstr(y + index, 1, msg, mode)

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


class Configuration:
    log_style = LogStyle.CoordinateNotation


class Chess(object):
    def __init__(self, window: CursesWindow):
        check_window_maxyx(window)
        draw_head(window)

        class Menus:
            root = Menu(
                [
                    ("new game", self.play),
                    ("load file", self.draw_load_menu),
                    ("options", self.draw_cfg_menu),
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
                "load file",
            )
            save = Menu(
                [
                    ("PGN", self.save_pgn, A_DIM),
                    ("JSON", self.save_json),
                ],
                window,
                "save file",
            )
            cfg = Menu(
                [
                    ("log style", self.draw_cfg_log_style_menu),
                ],
                window,
                "options",
            )

        self.window = window
        self.game: Optional[Game] = None
        self.menus = Menus()
        self.cfg = Configuration()

        self.menus.root.display()

    def draw_save_menu(self):
        self.menus.save.display()

        self.menus.save.position = 0

    def draw_load_menu(self):
        self.menus.load.display()

        self.menus.load.position = 0

    def draw_cfg_menu(self):
        self.menus.cfg.display()

        self.menus.cfg.position = 0

    def draw_cfg_log_style_menu(self):
        def set_style(style: LogStyle):
            self.cfg.log_style = style

            raise KeyboardInterrupt

        menu = Menu(
            [
                (
                    label,
                    partial(set_style, log_style),
                    A_BOLD if self.cfg.log_style == log_style else 0,
                )
                for log_style, label in (
                    (LogStyle.CoordinateNotation, "Coordinates"),
                    (LogStyle.AlgebraicNotation, "Algebraic Notation"),
                )
            ],
            self.window,
            "options/log style",
        )

        menu.position = self.cfg.log_style.value

        menu.display()

    def draw_about(self):
        y = 4

        self.window.move(y, 0)
        self.window.clrtobot()
        self.window.addstr(y + 0, 6, f"© 2021 Brandon Zacharie", A_COLOR)
        self.window.addstr(y + 2, 6, "github: BrandonZacharie/Chess.py", A_COLOR)
        self.window.addstr(y + 3, 6, f"semver: {Game.VERSION}", A_COLOR)
        self.window.addstr(y + 5, 6, "Press any key to continue...")
        self.window.getch()

    def play(self, game: Optional[Game] = None):
        if self.game is None:
            self.menus.root.insert(0, ("continue…", lambda: self.play(self.game)))
            self.menus.root.insert(2, ("save file", self.draw_save_menu))

        self.game = Game() if game is None else game

        main(self.window, self.game, self.cfg.log_style)

        self.menus.root.position = 0

    def save_pgn(self):
        pass

    def save_json(self):
        self._fileprompt(handler=self._save_json)

        raise KeyboardInterrupt

    def load_pgn(self):
        self._fileprompt(handler=self._load_pgn)

    def load_json(self):
        self._fileprompt(handler=self._load_json)

    def _save_json(self, filename: str) -> bool:
        x = 5
        y = 6

        if self.game is None:
            self.window.addstr(y + 2, x, "Game not found.", A_COLOR)
        else:
            try:
                self.game.save(filename)

                return True
            except FileNotFoundError:
                self.window.addstr(y + 2, x, "File not found.", A_COLOR)
            except Exception as e:
                self.window.addstr(y + 2, x, f"Error: {e}", A_COLOR)

        return False

    def _load_pgn(self, filename: str) -> bool:
        x = 5
        y = 6

        try:
            pgn_file = PGNFile(filename)

            if len(pgn_file) == 0:
                self.window.addstr(y + 2, x, "No games found.", A_COLOR)
            else:
                Menu(
                    [
                        (
                            f"{parse(cast(str, game.date).replace('.??', ''), fuzzy=True).date()} \"{game.event}\" {game.white} vs. {game.black}",
                            partial(lambda i: self.play(pgn_file.game(i)), i),
                        )
                        for i, game in enumerate(pgn_file)
                    ],
                    self.window,
                ).display()

            return True
        except FileNotFoundError:
            self.window.addstr(y + 2, x, "File not found.", A_COLOR)
        except Exception as e:
            self.window.addstr(y + 2, x, f"Error: {e}", A_COLOR)

        return False

    def _load_json(self, filename: str) -> bool:
        x = 5
        y = 6

        try:
            game = Game()

            game.load(filename)
            self.play(game)

            return True
        except FileNotFoundError:
            self.window.addstr(y + 2, x, "File not found.", A_COLOR)
        except Exception as e:
            self.window.addstr(y + 2, x, f"Error: {e}", A_COLOR)

        return False

    def _fileprompt(
        self,
        filename: Optional[str] = None,
        handler: Optional[Callable[[str], bool]] = None,
    ):
        x = 5
        y = 5

        if filename is None:
            filename = (
                path.realpath(path.join(getcwd(), path.dirname(__file__))) + path.sep
            )

        prompt = "〉" + filename

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

                    if handler is None or handler(prompt[1:]):
                        return

                    self.window.clrtobot()
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


if __name__ == "__main__":
    wrapper(Chess)
