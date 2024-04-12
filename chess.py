from curses import (
    A_COLOR,
    A_NORMAL,
    A_REVERSE,
    KEY_DOWN,
    KEY_ENTER,
    KEY_UP,
    curs_set,
    doupdate,
    panel,
    wrapper,
)
from typing import TYPE_CHECKING, Callable, List, Optional, Tuple, TypeAlias

from cli import Game, draw_head, main

if TYPE_CHECKING:
    from _curses import _CursesWindow

    CursesWindow = _CursesWindow
else:
    from typing import Any

    CursesWindow = Any

MenuItems: TypeAlias = List[Tuple[str, Optional[Callable]]]


class Menu(object):
    def __init__(self, items: MenuItems, stdscreen: CursesWindow):
        self.window = stdscreen.subwin(3, 4)

        self.window.keypad(True)

        self.panel = panel.new_panel(self.window)

        self.panel.hide()
        panel.update_panels()

        self.position = 0
        self.items = items

        self.items.append(("exit", None))

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
        draw_head(self.window)


class Chess(object):
    def __init__(self, window: CursesWindow):
        self.window = window

        curs_set(0)
        draw_head(window)

        Menu(
            [
                ("new game", self.play),
                ("load file", self.load),
                ("about", self.draw_about),
            ],
            window,
        ).display()

    def play(self):
        main(self.window)

    def load(self):
        draw_head(self.window)
        Menu(
            [
                ("PGN", self.load_pgn),
                ("JSON", self.load_json),
            ],
            self.window,
        ).display()

    def load_pgn(self):
        pass

    def load_json(self):
        pass

    def draw_about(self):
        y = 4

        self.window.clear()
        draw_head(self.window)
        self.window.addstr(y + 0, 6, f"© 2021 Brandon Zacharie", A_COLOR)
        self.window.addstr(y + 2, 6, "github: BrandonZacharie/Chess.py", A_COLOR)
        self.window.addstr(y + 3, 6, f"semver: {Game.VERSION}", A_COLOR)
        self.window.addstr(y + 5, 6, "Press any key to continue...")
        self.window.getch()
        self.window.clear()


if __name__ == "__main__":
    wrapper(Chess)
