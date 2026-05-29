from curses import A_NORMAL, A_REVERSE, curs_set, doupdate, panel
from curses import window as Window
from math import floor
from typing import Callable, List, Optional, Sequence, Tuple, TypeAlias

from .draw import draw_breadcrumbs
from .input import KeyCode

MenuItems: TypeAlias = List[
    Tuple[str, Optional[Callable]] | Tuple[str, Optional[Callable], int]
]


class Menu(object):
    def __init__(
        self,
        items: MenuItems,
        window: Window,
        title: Optional[Sequence[str]] = None,
    ):
        self._pages: Optional[List[MenuItems]] = None
        self.window = window.subwin(3, 4)
        self.title = title
        self.position = 0
        self.page = 0
        self.page_size = 25
        self.items = list(items)
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

    def pop(self, index: int):
        self.items.pop(index)

        self._pages = None

    def navigate(self, n: int) -> None:
        self.position += n
        prev_page = self.page

        if self.position < 0:
            self.page = max(0, self.page + floor(self.position / self.page_size))
            next_page_size = len(self.pages[self.page])
            self.position = (
                0 if self.page == prev_page else max(self.position + next_page_size, 0)
            )

            return

        prev_page_size = len(self.pages[prev_page])

        if self.position >= prev_page_size:
            self.page = min(
                len(self.pages) - 1,
                self.page + floor(self.position / self.page_size),
            )
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
                    draw_breadcrumbs(self.window, (2, y), *self.title)

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
                    case KeyCode.HOME:
                        self.navigate(-len(self.items))
                    case KeyCode.END:
                        self.navigate(len(self.items))
                    case KeyCode.EXIT | KeyCode.ESC:
                        break

                self.window.clear()
        except KeyboardInterrupt:
            pass

        self.panel.hide()
        panel.update_panels()
        doupdate()
