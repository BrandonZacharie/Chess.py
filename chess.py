from curses import (
    A_COLOR,
    A_NORMAL,
    A_REVERSE,
    KEY_BACKSPACE,
    KEY_DOWN,
    KEY_END,
    KEY_ENTER,
    KEY_EOL,
    KEY_EXIT,
    KEY_HOME,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    curs_set,
    doupdate,
    panel,
    wrapper,
)
from curses.ascii import BS, DEL, ENQ, ESC, LF, SOH, VT
from os import getcwd, path
from typing import TYPE_CHECKING, Callable, List, Optional, Tuple, TypeAlias

from cli import draw_head, main

from game import FileType, Game

if TYPE_CHECKING:
    from _curses import _CursesWindow

    CursesWindow = _CursesWindow
else:
    from typing import Any

    CursesWindow = Any

MenuItems: TypeAlias = List[Tuple[str, Optional[Callable]]]


class Menu(object):
    def __init__(self, items: MenuItems, window: CursesWindow):
        self.window = window.subwin(3, 4)
        self.position = 0
        self.items = items
        self.panel = panel.new_panel(self.window)

        self.items.append(("exit", None))
        self.panel.hide()
        panel.update_panels()
        self.window.keypad(True)

    def navigate(self, n) -> None:
        self.position += n

        if self.position < 0:
            self.position = 0
        elif self.position >= len(self.items):
            self.position = len(self.items) - 1

    def display(self) -> None:
        self.panel.top()
        self.panel.show()
        self.window.clear()

        try:
            while True:
                self.window.refresh()
                doupdate()

                for index, item in enumerate(self.items):
                    if index == self.position:
                        mode = A_REVERSE
                    else:
                        mode = A_NORMAL

                    msg = " %d. %s  " % (index + 1, item[0])
                    self.window.addstr(1 + index, 1, msg, mode)

                key = self.window.getch()

                if key in [KEY_ENTER, ord("\n")]:
                    if self.position == len(self.items) - 1:
                        break

                    fn = self.items[self.position][1]

                    if fn is not None:
                        fn()
                elif key == KEY_UP:
                    self.navigate(-1)
                elif key == KEY_DOWN:
                    self.navigate(1)

                self.window.clear()
                self.panel.hide()
                panel.update_panels()
                doupdate()
        except KeyboardInterrupt:
            pass

        curs_set(0)


class Chess(object):
    def __init__(self, window: CursesWindow):
        curs_set(0)
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
            self.menus.main.items.insert(0, ("continue", lambda: self.play(self.game)))

        self.game = Game() if game is None else game

        main(self.window, self.game)
        curs_set(0)

        self.menus.main.position = 0

    def load(self):
        self.menus.load.display()

        self.menus.load.position = 0

    def load_pgn(self):
        x = 5
        y = 4
        input = (
            "〉" + path.realpath(path.join(getcwd(), path.dirname(__file__))) + path.sep
        )

        self.window.move(y, x)
        self.window.clrtobot()
        self.window.addstr(y, x, "Enter the file path: ")

        y += 1
        cursor = len(input) + 1

        self.window.addstr(y, x, input)
        curs_set(2)

        while True:
            key = self.window.getch()

            if key in (KEY_EXIT, ESC):
                break

            if key in (KEY_DOWN, KEY_UP):
                continue

            if key in (KEY_ENTER, KEY_EOL, LF):
                game = Game()

                try:
                    game.load(input[1:], FileType.PGN)
                except FileNotFoundError:
                    self.window.addstr(y + 2, x, "File not found.", A_COLOR)
                except Exception as e:
                    self.window.addstr(y + 2, x, f"Error: {e}", A_COLOR)
                else:
                    self.play(game)

                    break
            elif key == KEY_LEFT:
                if cursor > 2:
                    cursor -= 1
            elif key == KEY_RIGHT:
                if cursor < len(input) + 1:
                    cursor += 1
            elif key == VT:
                input = input[: cursor - 1]

                self.window.addstr(y, x, input)
                self.window.clrtoeol()
            elif key in (KEY_HOME, SOH):
                cursor = 2
            elif key in (KEY_END, ENQ):
                cursor = len(input) + 1
            elif key in (KEY_BACKSPACE, BS, DEL):
                if cursor > 2:
                    input = input[: cursor - 2] + input[cursor - 1 :]
                    cursor -= 1

                    self.window.addstr(y, x, input)
                    self.window.clrtoeol()
            else:
                input = input[: cursor - 1] + chr(key) + input[cursor - 1 :]
                cursor += 1

                self.window.addstr(y, x, input)

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
