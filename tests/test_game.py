from tempfile import NamedTemporaryFile
from typing import Any, Callable, List, Optional, Sequence, Tuple, Type

from pytest import mark, raises
from semver import VersionInfo

from game import Cell, Direction, FileType, Game, Knight, Pawn, Query, Team, Turn
from game.error import IllegalMoveError, IllegalMoveOutOfTurnError
from game.queen import Queen


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
        save = lambda: game.save(f.name, version=version)

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
    logs: Sequence[Tuple[str, Any]], exception: Type[Exception]
):
    game = Game()

    for a, b in logs:
        game.board.log.append(
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
    game = Game()

    game.move("A2", "A3")

    def serializable(version: str | int | float = 2) -> Optional[dict[str, str]]:
        data = Game.serializable(game, version)

        if data is not None:
            data["fileVersion"] = str(VersionInfo(0, 0, 0))

        return data

    game.serializable = serializable

    with NamedTemporaryFile() as f:
        game.save(f.name)

        with raises(ValueError):
            Game().load(f.name)


@mark.parametrize("filename", ["../tests/test1.pgn", "../tests/test2.pgn"])
def test_load_pgn(filename: str):
    game = Game()

    game.load(filename, FileType.PGN)


@mark.parametrize("filename", ["../tests/Nakamura.pgn", "../tests/Carlsen.pgn"])
def test_parse_pgn(filename: str):
    games = Game().parse_pgn(filename)


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
