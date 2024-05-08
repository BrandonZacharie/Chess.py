from curses import A_BOLD, A_UNDERLINE, curs_set, wrapper
from curses.ascii import ESC
from enum import IntEnum
from itertools import zip_longest
from typing import TYPE_CHECKING, List, Optional, Tuple, cast

from game import PIECE_NAME_TYPE_MAP, Board, Game, Team
from game.board import LogEvent, LogMove
from game.error import IllegalMoveError

if TYPE_CHECKING:
    from _curses import _CursesWindow

    CursesWindow = _CursesWindow
else:
    from typing import Any

    CursesWindow = Any


BOARD_CELL_ORDS = [ord(ch) for ch in "12345678ABCDEFGHabcdefgh"]


class LogStyle(IntEnum):
    CoordinateNotation = 0
    AlgebraicNotation = 1


class InputMode(IntEnum):
    PAUSED = 0
    SELECT_CELL = 1
    SELECT_DEST = 2
    SELECT_PROM = 3


def draw_head(window: CursesWindow):
    window.addstr(2, 5, " Chess.py ", A_BOLD | A_UNDERLINE)


def draw_board(window: CursesWindow, board: Board, log_style: LogStyle):
    x = 5
    y = 7

    """Draw the board."""
    for line in str(board).splitlines():
        window.addstr(y, x, f"{line}")

        y += 1

    """Draw the captures."""
    for captures, y in (
        (board.captures[Team.WHITE], 4),
        (board.captures[Team.BLACK], y),
    ):
        window.addstr(y, x + 1, "⌜" + " " * 33 + "⌝")

        y += 1

        for i, pieces in enumerate(
            list(zip_longest(*[iter(captures)] * 16, fillvalue=" "))
        ):
            window.addstr(y + i, x + 3, " ".join(str(piece) for piece in pieces))

        window.addstr(y + 2, x + 1, "⌞" + " " * 33 + "⌟")

    """Draw the moves."""
    match log_style:
        case LogStyle.CoordinateNotation:
            draw_ilog(window, board)
        case LogStyle.AlgebraicNotation:
            draw_elog(window, board)


def draw_ilog(window: CursesWindow, board: Board):
    def get_cell_name(indices: Tuple[int, int]) -> str:
        return board[indices[1]][indices[0]].name

    def get_moves() -> List[List[str]]:
        count = 0
        moves: List[List[str]] = []

        for entry in board.ilog:
            if type(entry[1]) is tuple:
                move = cast(LogMove, entry)

                moves.append([f"{get_cell_name(move[0])}:{get_cell_name(move[1])}"])

                count += 1
            else:
                event = cast(LogEvent, entry)

                moves[count - 1].append(f"{get_cell_name(event[0])}:^{event[1]}")

        return moves

    moves = get_moves()
    count = len(moves)
    lines = 0
    x = 43
    y = 5
    columns = 1
    prefix_max = 0
    output_max = 8
    length_max = 24

    window.addstr(y - 1, x - 2, "⌜")
    window.addstr(y + length_max, x - 2, "⌞")

    for i, entry in enumerate(reversed(moves)):
        length = len(entry)
        prefix = f"{count - i}."
        prefix_max = max(prefix_max, len(prefix))

        if lines + length > length_max:
            if columns == 4:
                break

            x += output_max + 2
            lines = 0
            columns += 1

        for j, move in enumerate(reversed(entry)):
            window.move(y + lines, x)
            window.clrtoeol()

            if j == length - 1:
                window.addstr(y + lines, x, prefix, A_BOLD)

            window.addstr(y + lines, x + 1 + prefix_max, move)

            output_max = max(output_max, len(move) + 1 + prefix_max)
            lines += 1

    window.addstr(y - 1, x + output_max + 1, "⌝")
    window.addstr(y + length_max, x + output_max + 1, "⌟")


def draw_elog(window: CursesWindow, board: Board):
    lines = 0
    x = 43
    y = 5
    columns = 1
    prefix_max = 0
    output_max = 8
    length_max = 24

    window.addstr(y - 1, x - 2, "⌜")
    window.addstr(y + length_max, x - 2, "⌞")

    for entry in reversed(board.elog):
        prefix = entry[0]
        prefix_max = max(prefix_max, len(prefix))
        move = f"{entry[1]} {entry[2]}" if len(entry) == 3 else entry[1]

        if lines + 1 > length_max:
            if columns == 4:
                break

            x += output_max + 2
            lines = 0
            columns += 1

        window.move(y + lines, x)
        window.clrtoeol()
        window.addstr(y + lines, x, prefix, A_BOLD)
        window.addstr(y + lines, x + 1 + prefix_max, move)

        output_max = max(output_max, len(move) + 1 + prefix_max)
        lines += 1

    window.addstr(y - 1, x + output_max + 1, "⌝")
    window.addstr(y + length_max, x + output_max + 1, "⌟")


def draw_notes(window: CursesWindow, game: Game, mode: InputMode):
    x = 6
    y = 31
    lead = "It is "
    tail = "'s turn."
    turn = game.turn

    if mode is InputMode.SELECT_PROM:
        turn = game._last_turn

    window.addstr(y, x, lead)
    window.addstr(y, x + len(lead), turn.name, A_BOLD)
    window.addstr(y, x + len(lead) + len(turn.name), tail)


def draw_input_prompt(window: CursesWindow, mode: InputMode):
    x = 6
    y = 32

    match mode:
        case InputMode.SELECT_CELL:
            window.addstr(y, x, "Select a piece:")
        case InputMode.SELECT_DEST:
            window.addstr(y, x, "Select a target:")
        case InputMode.SELECT_PROM:
            window.addstr(y, x, "Select a promotion:")

    window.clrtoeol()


def draw_input_err(window: CursesWindow, e: Exception | str):
    x = 6
    y = 32

    window.move(y + 1, x)
    window.clrtoeol()
    window.addstr(y, x, f"{e} Press any key to continue.")
    window.getkey()


def draw_input_cursor(window: CursesWindow, mode: InputMode, s: Optional[str] = None):
    y = 33
    x = 6

    match mode:
        case InputMode.SELECT_CELL:
            pass
        case InputMode.SELECT_DEST:
            if s is not None:
                window.addstr(y, x, s)

            x += 3
        case InputMode.SELECT_PROM:
            pass

    window.move(y, x)
    window.clrtoeol()


def draw_input(window: CursesWindow, mode: InputMode, ch: int):
    y = 33
    x = 6 if mode is InputMode.SELECT_CELL else 9

    window.addstr(y, x, f"{chr(ch)}".upper())


def get_input(window: CursesWindow, mode: InputMode) -> List[int]:
    count: int
    input: List[int] = []

    match mode:
        case InputMode.PAUSED:
            count = 0
        case InputMode.SELECT_CELL | InputMode.SELECT_DEST:
            count = 2
        case InputMode.SELECT_PROM:
            count = 1

    while count > 0:
        ch = window.getch()

        if ch == ESC:
            raise KeyboardInterrupt

        if ch not in BOARD_CELL_ORDS:
            continue

        draw_input(window, mode, ch)
        input.append(ch)

        count -= 1

    return input


def main(
    window: CursesWindow,
    game: Game = Game(),
    log_style: LogStyle = LogStyle.CoordinateNotation,
):
    mode = InputMode.SELECT_CELL
    q1 = ""
    q2 = ""

    curs_set(2)
    window.move(0, 0)
    window.clrtobot()
    draw_head(window)
    draw_board(window, game.board, log_style)

    while True:
        draw_notes(window, game, mode)
        draw_input_prompt(window, mode)
        draw_input_cursor(window, mode, q1 if mode is InputMode.SELECT_DEST else None)

        try:
            input = "".join([chr(ch) for ch in get_input(window, mode)]).upper()
        except KeyboardInterrupt:
            return

        match mode:
            case InputMode.SELECT_CELL:
                q1 = input
                mode = InputMode.SELECT_DEST
            case InputMode.SELECT_DEST:
                q2 = input
                mode = InputMode.SELECT_CELL

                try:
                    game.move(q1, q2)
                except ValueError:
                    draw_input_err(window, "Invalid input.")
                except IllegalMoveError as e:
                    draw_input_err(window, e)
                else:
                    draw_board(window, game.board, log_style)
                    draw_input_cursor(window, mode)
                    window.clrtoeol()

                    if game.board.get_promotable() is not None:
                        mode = InputMode.SELECT_PROM
            case InputMode.SELECT_PROM:
                try:
                    game.promote(PIECE_NAME_TYPE_MAP[input.upper()])
                except KeyError:
                    draw_input_err(window, "Invalid input.")
                else:
                    draw_board(window, game.board, log_style)

                    mode = InputMode.SELECT_CELL


def run() -> None:
    wrapper(main)


if __name__ == "__main__":
    run()
