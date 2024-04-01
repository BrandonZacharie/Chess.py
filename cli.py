from curses import A_BOLD, A_COLOR, A_UNDERLINE, curs_set, wrapper
from enum import Enum
from typing import TYPE_CHECKING, List, Optional, Tuple, cast

from game import PIECE_NAME_TYPE_MAP, Board, Game, Team
from game.board import Event, Move
from game.error import IllegalMoveError

if TYPE_CHECKING:
    from _curses import _CursesWindow

    CursesWindow = _CursesWindow
else:
    from typing import Any

    CursesWindow = Any


class InputMode(Enum):
    PAUSED = 0
    SELECT_CELL = 1
    SELECT_DEST = 2
    SELECT_PROM = 3


def draw_head(window: CursesWindow):
    window.addstr(2, 5, " Chess.py ", A_BOLD | A_UNDERLINE)


def draw_foot(window: CursesWindow, y: int = 34):
    window.addstr(y, 6, f"© 2021 Brandon Zacharie", A_COLOR)
    window.addstr(y + 1, 6, "github: BrandonZacharie/Chess.py", A_COLOR)
    window.addstr(y + 2, 6, f"semver: {Game.VERSION}", A_COLOR)


def draw_board(window: CursesWindow, board: Board):
    x = 5
    y = 6

    """Draw the board."""
    for line in str(board).splitlines():
        window.addstr(y, x, f"{line}")

        y += 1

    """Draw the captures."""
    for captures, y in (
        (board.captures[Team.BLACK], 5),
        (board.captures[Team.WHITE], y + 1),
    ):
        window.addstr(y - 1, x + 1, "⌜" + " " * 33 + "⌝")
        window.addstr(y + 0, x + 3, " ".join(str(piece) for piece in captures))
        window.addstr(y + 1, x + 1, "⌞" + " " * 33 + "⌟")

    """Draw the log."""
    draw_log(window, board)


def draw_log(window: CursesWindow, board: Board):
    def get_cell_name(indices: Tuple[int, int]) -> str:
        return board[indices[1]][indices[0]].name

    def get_moves() -> List[List[str]]:
        moves = 0
        log: List[List[str]] = []

        for entry in board.log:
            if type(entry[1]) is tuple:
                move = cast(Move, entry)

                log.append([f"{get_cell_name(move[0])}:{get_cell_name(move[1])}"])

                moves += 1
            else:
                event = cast(Event, entry)

                log[moves - 1].append(f"{get_cell_name(event[0])}:^{event[1]}")

        return log

    moves = get_moves()
    count = len(moves)
    lines = 0
    x = 43
    y = 5
    columns = 1
    prefix_max = 0
    output_max = 8
    length_max = 22

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


def draw_notes(window: CursesWindow, game: Game, mode: InputMode):
    x = 6
    y = 29
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
    y = 30

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
    y = 30

    window.move(y + 1, x)
    window.clrtoeol()
    window.addstr(y, x, f"{e} Press any key to continue.")
    window.getkey()


def draw_input_cursor(window: CursesWindow, mode: InputMode, s: Optional[str] = None):
    y = 31
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
    x = 6 if mode is InputMode.SELECT_CELL else 9

    window.addstr(31, x, f"{chr(ch)}".upper())


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

    for _ in range(count):
        ch = window.getch()

        draw_input(window, mode, ch)
        input.append(ch)

    return input


def main(window: CursesWindow):
    game = Game()
    mode = InputMode.SELECT_CELL
    q1 = ""
    q2 = ""

    window.clear()
    curs_set(2)

    draw_head(window)
    draw_foot(window)
    draw_board(window, game.board)

    while True:
        draw_notes(window, game, mode)
        draw_input_prompt(window, mode)
        draw_input_cursor(window, mode, q1 if mode is InputMode.SELECT_DEST else None)

        input = "".join([chr(ch) for ch in get_input(window, mode)]).upper()

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
                    draw_board(window, game.board)
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
                    draw_board(window, game.board)

                    mode = InputMode.SELECT_CELL


def run():
    wrapper(main)


if __name__ == "__main__":
    run()
