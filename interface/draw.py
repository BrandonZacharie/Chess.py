from curses import A_BOLD, A_COLOR, A_UNDERLINE
from curses import window as Window
from typing import Tuple


def check_window_maxyx(window: Window, maxyx: Tuple[int, int] = (40, 40)) -> bool:
    attempts = 0

    while True:
        y, x = window.getmaxyx()

        if x < maxyx[1] or y < maxyx[0]:
            window.addstr(
                0,
                0,
                "window is too small… press any key to retry "
                + (f"({attempts})" if attempts > 0 else ""),
                A_COLOR,
            )
            window.refresh()
            window.getch()

            attempts += 1
        else:
            window.clear()

            break

    return attempts > 0


def draw_head(window: Window):
    window.addstr(2, 5, " Chess.py ", A_BOLD | A_UNDERLINE)


def draw_breadcrumbs(window: Window, coordinates: Tuple[int, int], *breadcrumbs: str):
    x, y = coordinates

    window.addstr(y, x, "↳ " + " 〉".join(breadcrumbs))
