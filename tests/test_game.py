from concurrent.futures import ThreadPoolExecutor
from tempfile import NamedTemporaryFile
from typing import Any, Callable, Generator, List, Optional, Sequence, Tuple, Type

from pytest import mark, raises

from game import (
    PIECE_NAME_TYPE_MAP,
    AlgebraicNotationLogEntry,
    Cell,
    Direction,
    Game,
    Knight,
    Pawn,
    PGNFile,
    Queen,
    Query,
    Team,
    Turn,
)
from game.error import (
    IllegalMoveError,
    IllegalMoveOutOfTurnError,
    IllegalMoveThroughCheckError,
)


def test_loads():
    s = """
        ──┬───┬───┬───┬───┬───┬───┬───┬───┐
        8 │ ♖ │ ♘ │ ♗ │ ♕ │ ♔ │ ♗ │ ♘ │ ♖ │
        ──┼───┼───┼───┼───┼───┼───┼───┼───┤
        7 │ ♙ │ ♙ │ ♙ │ ♙ │ ♙ │ ♙ │ ♞ │ ♙ │
        ──┼───┼───┼───┼───┼───┼───┼───┼───┤
        6 │   │   │   │   │   │   │   │   │
        ──┼───┼───┼───┼───┼───┼───┼───┼───┤
        5 │   │   │   │   │   │   │   │   │
        ──┼───┼───┼───┼───┼───┼───┼───┼───┤
        4 │   │ ♟ │ ♟ │ ♟ │ ♟ │ ♟ │ ♟ │ ♟ │
        ──┼───┼───┼───┼───┼───┼───┼───┼───┤
        3 │ ♟ │   │ ♝ │   │   │   │   │   │
        ──┼───┼───┼───┼───┼───┼───┼───┼───┤
        2 │   │ ♜ │   │ ♞ │ ♛ │   │   │   │
        ──┼───┼───┼───┼───┼───┼───┼───┼───┤
        1 │   │   │ ♚ │   │ ♜ │ ♝ │   │   │
        ──┼───┼───┼───┼───┼───┼───┼───┼───┤
          │ A │ B │ C │ D │ E │ F │ G │ H │
        """
    game = Game()

    game.loads(s)

    assert isinstance(game.cell("G7").piece, Knight)
    assert game.cell("G7").piece.team is Team.WHITE
    assert isinstance(game.cell("A3").piece, Pawn)
    assert game.cell("A3").piece.team is Team.WHITE


def test_ref_err():
    game = Game()
    row: Callable[[str], List[Cell]] = lambda start: game.board.get_cells(
        game.cell(start),
        Direction.RIGHT,
    )
    pieces = [cell.piece for cell in row("A1") + row("A2") if cell.piece is not None]
    game._board = None
    cells = row("A1") + row("A2")

    assert len(pieces) == len(cells)

    for piece, cell in zip(pieces, cells):
        with raises(ReferenceError):
            piece.check_take(cell)


def test_reset():
    game = Game()
    piece = game.cell("A2").piece

    game.move("A2", "A3")

    assert game.cell("A2").piece is None
    assert game.cell("A3").piece is piece

    game.reset()

    assert piece.cell is None
    assert game.cell("A3").piece is None
    assert game.cell("A2").piece is not None


@mark.parametrize("version", [2, 1, 0])
def test_save(version: int):
    game = Game()

    with NamedTemporaryFile() as f:
        assert not game.save(f.name, version=version)

    game.move("A2", "A3")

    with NamedTemporaryFile() as f:
        save: Callable = lambda: game.save(f.name, version=version)

        if version == 0:
            with raises(ValueError):
                save()
        else:
            assert save()


@mark.parametrize("version", [2, 1])
def test_load_json(version: int):
    def reload(game: Game) -> Game:
        with NamedTemporaryFile() as f:
            game.save(f.name, version=version)

            game = Game()

            game.load(f.name)

        return game

    game = Game()

    assert game.turn is Turn.WHITE

    game.move("B2", "B3")
    game.move("B7", "B6")
    game.move("C1", "A3")
    game.move("C8", "A6")
    game.move("F2", "F3")

    assert game.turn is Turn.BLACK

    game = reload(game)

    assert game.cell("B2").piece is None
    assert game.cell("B3").piece is not None
    assert game.cell("B7").piece is None
    assert game.cell("B6").piece is not None
    assert game.cell("C1").piece is None
    assert game.cell("A3").piece is not None
    assert game.cell("C8").piece is None
    assert game.cell("A6").piece is not None

    if version == 2:
        assert game.turn is Turn.BLACK

        game.move("B6", "B5")
        game.move("F3", "F4")
        game.move("B5", "B4")
        game.move("C2", "C4")
        game.move("B4", "C3")
        game.move("D2", "D4")
        game.move("C3", "C2")
        game.move("D1", "D2")
        game.move("C2", "C1")
        game.promote(Queen)

        game = reload(game)

        assert isinstance(game.cell("C1").piece, Queen)
        assert game.cell("C1").piece.team is Team.BLACK


@mark.parametrize(
    ("logs", "exception"),
    (
        ([("A2", "A3"), ("A4", "A5")], IllegalMoveError),
        ([("A4", "A5")], ValueError),
        ([("A4", 2)], ValueError),
        ([("A1", "Q")], IllegalMoveError),
    ),
)
def test_load_json_invalid_log(
    logs: Sequence[Tuple[str, Any]],
    exception: Type[Exception],
):
    game = Game()

    for a, b in logs:
        game.board.ilog.append(
            (
                game.point(a),
                game.point(b) if isinstance(b, str) and len(b) == 2 else b,
            )
        )

    with NamedTemporaryFile() as f:
        game.save(f.name)

        with raises(exception):
            Game().load(f.name)


def test_load_json_unsupported_version():
    class TestGame(Game):
        def serializable(
            self, version: str | int | float = 2
        ) -> Optional[dict[str, str]]:
            data = super().serializable(version)

            if data is not None:
                data["fileVersion"] = "0.0.0"

            return data

    game = TestGame()

    game.move("A2", "A3")

    with NamedTemporaryFile() as f:
        game.save(f.name)

        with raises(ValueError):
            Game().load(f.name)


@mark.parametrize(
    "filename",
    [
        "../tests/test1.pgn",
        "../tests/test2.pgn",
        "../tests/Carlsen.pgn",
        "../tests/Nakamura.pgn",
    ],
)
def test_load_pgn_file(filename: str):
    def cleaned_pgn_moves(moves: Sequence[str]) -> Generator[str, Any, None]:
        level = 0

        for move in moves:
            match move[0]:
                case "(":
                    level += 1

                    continue
                case ")":
                    level -= 1

                    continue
                case "{":
                    continue

            if level > 0:
                continue

            match move:
                case "0-1" | "1-0" | "1/2-1/2":
                    continue

            yield move

    def cleaned_log_moves(
        moves: Sequence[AlgebraicNotationLogEntry],
    ) -> Generator[str, Any, None]:
        for move in moves:
            yield move[1]

            if len(move) == 3:
                yield move[2]

    pgn_file = PGNFile(filename)

    assert len(pgn_file) > 0

    with ThreadPoolExecutor() as executor:
        games = list(executor.map(pgn_file.game, range(len(pgn_file))))

    for pgn_game, game in zip(pgn_file, games):
        pgn_moves = list(cleaned_pgn_moves(pgn_game.moves))
        log_moves = list(cleaned_log_moves(game.board.elog))

        assert len(pgn_moves) == len(log_moves)
        assert pgn_moves == log_moves


def test_notify():
    game = Game()
    count = 0
    event: Optional[str] = None

    def handler(g: Game, args):
        nonlocal count, event

        count += 1
        event = args[0]

    game.add_event_handler("notify", handler, once=True)
    game.notify("test1")
    game.notify("test2")

    assert count == 1
    assert event == "test1"

    game.add_event_handler("notify", handler)
    game.notify("test1")

    assert event == "test1"
    assert count == 2

    game.add_event_handler("notify", handler)
    game.notify("test2")

    assert count == 3
    assert event == "test2"

    game.remove_event_handler("notify", handler)
    game.notify("test3")

    assert count == 3
    assert event == "test2"

    game.remove_event_handler("******", handler)


def test_illegal_move():
    game = Game()

    assert game.cell("A3").piece is None

    with raises(IllegalMoveError):
        game.move("A3", "A4")


def test_no_piece_to_move_error():
    game = Game()

    with raises(IllegalMoveError):
        raise IllegalMoveError("")

    with raises(IllegalMoveError):
        raise IllegalMoveError("", game.cell("A3"))


@mark.parametrize(
    "query",
    (
        "A",
        "0",
        "00",
        (0, -1),
        (9, 0),
        ("A", "A"),
        ("1", "1"),
        Pawn(Team.BLACK),
    ),
)
def test_invalid_point(query: Query):
    game = Game()

    with raises(ValueError):
        game.point(query)


@mark.parametrize("query", ("A1", (0, 0), ("A", "1")))
def test_point_parse(query: Query):
    game = Game()

    game.point(query)


def test_point_ref():
    game = Game()
    query = "A1"
    point = (0, 7)

    assert game.point(query) == point
    assert game.point(point) == point

    cell = game.cell(query)

    assert game.point(cell) == point
    assert game.point(cell.piece) == point


def test_illegal_move_out_of_turn():
    game = Game()

    game.move("A2", "A3")

    with raises(IllegalMoveOutOfTurnError):
        game.move("A3", "A4")


def test_promote():
    game = Game()

    game.move("A2", "A4")
    game.move("B7", "B5")
    game.move("A4", "B5")
    game.move("B8", "A6")
    game.move("B5", "B6")
    game.move("A6", "C5")
    game.move("B6", "B7")
    game.move("C5", "B3")
    game.move("B7", "B8")
    game.promote(PIECE_NAME_TYPE_MAP["Q"])
    game.move("A8", "B8")
    game.move("C2", "C4")
    game.move("B8", "B4")
    game.move("C4", "C5")
    game.move("B4", "B5")
    game.move("C5", "C6")
    game.move("B5", "B6")
    game.move("C6", "D7")
    game.move("D8", "D7")
    game.move("D2", "D4")
    game.move("A7", "A5")
    game.move("A1", "A4")
    game.move("D7", "A4")
    game.move("D4", "D5")
    game.move("A4", "D4")
    game.move("D5", "D6")
    game.move("D4", "D1")
    game.move("E1", "D1")
    game.move("A5", "A4")
    game.move("E2", "E4")
    game.move("G7", "G5")
    game.move("E4", "E5")
    game.move("F8", "H6")
    game.move("E5", "E6")
    game.move("G8", "F6")
    game.move("D6", "D7")
    game.move("E8", "G8")
    game.move("D7", "D8")
    game.promote(PIECE_NAME_TYPE_MAP["Q"])
    game.move("G8", "G7")
    game.move("E6", "F7")
    game.move("G7", "G6")
    game.move("F1", "A6")
    game.move("F8", "H8")
    game.move("F7", "F8")
    game.promote(PIECE_NAME_TYPE_MAP["Q"])
    game.move("A4", "A3")


def test_playable_cell():
    game = Game()

    assert game.find_playable_cell(Pawn, Team.WHITE, None, "A3").name == "A2"
    assert game.find_playable_cell(Pawn, Team.WHITE, None, "A4").name == "A2"

    with raises(ValueError):
        game.find_playable_cell(Pawn, Team.WHITE, None, "A5")

    assert game.find_playable_cell(Knight, Team.WHITE, None, "A3").name == "B1"
    assert game.find_playable_cell(Knight, Team.WHITE, None, "C3").name == "B1"

    with raises(ValueError):
        game.find_playable_cell(Knight, Team.WHITE, None, "D2")


def test_invalid_pgn_move():
    game = Game()

    with raises(ValueError):
        game.parse_pgn_move("aaaa")

    with raises(ValueError):
        game.parse_pgn_move("a5")


def test_illegal_move_through_check():
    game = Game()

    game.move("A2", "A4")
    game.move("B7", "B5")
    game.move("A4", "B5")
    game.move("C7", "C5")
    game.move("B5", "C6")
    game.move("B8", "C6")
    game.move("A1", "A6")
    game.move("C8", "A6")
    game.move("C2", "C4")
    game.move("A6", "C4")
    game.move("D1", "A4")
    game.move("D8", "A5")
    game.move("A4", "A5")
    game.move("A7", "A6")
    game.move("A5", "C7")

    with raises(IllegalMoveThroughCheckError):
        game.move("E8", "C8")


def test_revert_castling_move():
    game = Game()

    game.move("E2", "E4")
    game.move("E7", "E5")
    game.move("G1", "F3")
    game.move("B8", "C6")
    game.move("F1", "C4")
    game.move("G8", "F6")

    assert game.move("E1", "G1", can_commit=False)
    assert game.cell("E1").piece.name == "King"
    assert game.cell("H1").piece.name == "Rook"


def test_add_comment():
    game = Game()

    game.add_comment(" ")
    game.add_comment("This is a comment.")

    assert game.board.elog[-1] == ("1.", "{This is a comment.}")

    game.move("E2", "E4")
    game.move("E7", "E5")
    game.move("G1", "F3")
    game.move("B8", "C6")
    game.move("F1", "C4")
    game.move("G8", "F6")
    game.move("A2", "A4")
    game.add_comment("This is a comment.")

    assert game.board.elog[-1] == ("4.", "a4", "{This is a comment.}")

    game.move("B7", "B5")

    assert game.board.elog[-1] == ("4...", "b5")

    game.add_comment("This is a comment.")

    assert game.board.elog[-1] == ("4...", "b5", "{This is a comment.}")

    game.add_comment("This is a comment.")

    assert game.board.elog[-1] == (
        "4...",
        "b5",
        "{This is a comment. This is a comment.}",
    )

    game.move("A4", "A5")
    game.add_comment("This is a comment.")

    assert game.board.elog[-1] == ("5.", "a5", "{This is a comment.}")

    game.add_comment("This is a comment.")

    assert game.board.elog[-1] == (
        "5.",
        "a5",
        "{This is a comment. This is a comment.}",
    )
