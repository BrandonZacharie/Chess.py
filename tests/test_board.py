from types import NoneType
from typing import List, Type

from pytest import raises

from game import (
    Bishop,
    Board,
    Cell,
    Direction,
    Game,
    King,
    Knight,
    Pawn,
    Piece,
    Queen,
    Rook,
    Team,
)
from game.error import IllegalMoveThroughCheckError, IllegalMoveToCheckError


def test_layout():
    board = Board()
    template: List[List[Type[Piece] | None]] = [
        [Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook],
        [Pawn] * 8,
        [None] * 8,
        [None] * 8,
        [None] * 8,
        [None] * 8,
        [Pawn] * 8,
        [Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook],
    ]

    for y, r in enumerate(template):
        for x, t in enumerate(r):
            cell = board[y][x]

            assert isinstance(cell, Cell)
            assert cell.x is x
            assert cell.y is y

            if t is not None:
                assert isinstance(cell.piece, t)
                assert cell.piece is not None
                assert cell.piece.team is Team(y < len(template) / 2)
                assert cell.piece.cell is cell
                assert not cell.piece.has_moved


def test_pawn_white_move_1():
    board = Board()
    template: List[List[Type[Piece]]] = [
        [Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook],
        [Pawn] * 8,
        [NoneType] * 8,
        [NoneType] * 8,
        [NoneType] * 8,
        [Pawn] + [NoneType] * 7,
        [NoneType] + [Pawn] * 7,
        [Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook],
    ]

    pawn = board[6][0].piece

    assert isinstance(pawn, Pawn)
    assert pawn.cell is board[6][0]
    assert pawn.has_moved is False
    assert pawn.team is Team.WHITE

    cell = board[5][0]

    assert isinstance(cell, Cell)
    assert cell.piece is None
    assert cell.point == (0, 5)

    board.move_piece(pawn, cell)

    for y, r in enumerate(template):
        for x, t in enumerate(r):
            cell = board[y][x]

            assert isinstance(cell, Cell)
            assert cell.point == (x, y)

            piece = cell.piece

            if t is NoneType and piece is None:
                continue

            assert isinstance(piece, t)
            assert piece.cell is cell
            assert piece.has_moved or piece is not pawn
            assert piece.team is Team(y < len(template) / 2)


def test_pawn_white_move_2():
    board = Board()
    template: List[List[Type[Piece]]] = [
        [Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook],
        [Pawn] * 8,
        [NoneType] * 8,
        [NoneType] * 8,
        [Pawn] + [NoneType] * 7,
        [NoneType] * 8,
        [NoneType] + [Pawn] * 7,
        [Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook],
    ]

    pawn = board[6][0].piece

    assert isinstance(pawn, Pawn)
    assert pawn.cell is board[6][0]
    assert pawn.has_moved is False
    assert pawn.team is Team.WHITE

    cell = board[4][0]

    assert isinstance(cell, Cell)
    assert cell.piece is None
    assert cell.point == (0, 4)

    board.move_piece(pawn, cell)

    for y, r in enumerate(template):
        for x, t in enumerate(r):
            cell = board[y][x]

            assert isinstance(cell, Cell)
            assert cell.point == (x, y)

            piece = cell.piece

            if t is NoneType and piece is None:
                continue

            assert isinstance(piece, t)
            assert piece.cell is cell
            assert piece.has_moved or piece is not pawn
            assert piece.team is Team(y < len(template) / 2)


def test_pawn_white_move_invalid():
    board = Board()
    template: List[List[Type[Piece]]] = [
        [Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook],
        [Pawn] * 8,
        [NoneType] * 8,
        [NoneType] * 8,
        [NoneType] * 4 + [Pawn] + [NoneType] * 3,
        [NoneType] * 8,
        [Pawn] * 4 + [NoneType] + [Pawn] * 3,
        [Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook],
    ]

    pawn = board[6][4].piece

    board.move_piece(pawn, pawn.cell.up(2))

    assert not board.try_move_piece(pawn, pawn.cell.left(1))
    assert not board.try_move_piece(pawn, pawn.cell.right(1))
    assert not board.try_move_piece(pawn, pawn.cell.down(1))
    assert not board.try_move_piece(pawn, pawn.cell.down(1).left(1))
    assert not board.try_move_piece(pawn, pawn.cell.down(1).right(1))
    assert not board.try_move_piece(pawn, pawn.cell.up(1).left(1))
    assert not board.try_move_piece(pawn, pawn.cell.up(1).right(1))

    for y, r in enumerate(template):
        for x, t in enumerate(r):
            cell = board[y][x]

            assert isinstance(cell, Cell)
            assert cell.point == (x, y)

            piece = cell.piece

            if t is NoneType and piece is None:
                continue

            assert isinstance(piece, t)
            assert piece.cell is cell
            assert piece.has_moved or piece is not pawn
            assert piece.team is Team(y < len(template) / 2)


def test_get_cells():
    game = Game()

    cell = game.cell("A1")
    cells = game.board.get_cells(cell, Direction.UP)

    assert len(cells) == 8
    assert cells[0] is cell
    assert cells[-1] is game.cell("A8")

    cell = game.cell("A8")
    cells = game.board.get_cells(cell, Direction.DOWN)

    assert len(cells) == 8
    assert cells[0] is cell
    assert cells[-1] is game.cell("A1")

    cell = game.cell("H1")
    cells = game.board.get_cells(cell, Direction.LEFT)

    assert len(cells) == 8
    assert cells[0] is cell
    assert cells[-1] is game.cell("A1")

    cell = game.cell("A1")
    cells = game.board.get_cells(cell, Direction.RIGHT)

    assert len(cells) == 8
    assert cells[0] is cell
    assert cells[-1] is game.cell("H1")

    cell = game.cell("H1")
    cells = game.board.get_cells(cell, Direction.UP_LEFT)

    assert len(cells) == 8
    assert cells[0] is cell
    assert cells[-1] is game.cell("A8")

    cell = game.cell("A8")
    cells = game.board.get_cells(cell, Direction.DOWN_RIGHT)

    assert len(cells) == 8
    assert cells[0] is cell
    assert cells[-1] is game.cell("H1")

    cell = game.cell("A1")
    cells = game.board.get_cells(cell, Direction.UP_RIGHT)

    assert len(cells) == 8
    assert cells[0] is cell
    assert cells[-1] is game.cell("H8")

    cell = game.cell("H8")
    cells = game.board.get_cells(cell, Direction.DOWN_LEFT)

    assert len(cells) == 8
    assert cells[0] is cell
    assert cells[-1] is game.cell("A1")


def test_can_take_self_cell():
    board = Board()

    for cell in board.get_cells(board[0][0], Direction.RIGHT):
        assert cell.piece is not None
        assert cell.piece.can_take(cell)

    assert board[1][0].piece.can_take(board[1][0])


def test_illegal_move_through_check():
    game = Game()

    game.move("A2", "A3")
    game.move("A7", "A6")
    game.move("B1", "C3")
    game.move("B7", "B6")
    game.move("B2", "B3")
    game.move("D7", "D6")
    game.move("C1", "B2")
    game.move("F7", "F6")
    game.move("D2", "D4")
    game.move("G7", "G6")
    game.move("D1", "D3")
    game.move("H7", "H6")
    game.move("E1", "C1")
    game.move("H6", "H5")
    game.move("C1", "D2")
    game.move("C8", "F5")
    game.move("D3", "E3")
    game.move("F5", "E4")

    assert game.board.get_king(Team.WHITE).is_safe

    with raises(IllegalMoveThroughCheckError):
        game.move("D2", "D3")


def test_illegal_move_to_check():
    game = Game()

    game.move("A2", "A3")
    game.move("A7", "A6")
    game.move("B1", "C3")
    game.move("B7", "B6")
    game.move("B2", "B3")
    game.move("D7", "D6")
    game.move("C1", "B2")
    game.move("F7", "F6")
    game.move("D2", "D4")
    game.move("G7", "G6")
    game.move("D1", "D3")
    game.move("H7", "H6")
    game.move("E1", "C1")
    game.move("H6", "H5")
    game.move("C1", "D2")
    game.move("C8", "F5")
    game.move("D3", "E3")
    game.move("F5", "E4")
    game.move("E3", "D3")
    game.move("E4", "F5")
    game.move("D3", "E4")
    game.move("A6", "A5")
    game.move("D2", "D3")
    game.move("B6", "B5")

    assert game.board.get_king(Team.WHITE).is_safe

    with raises(IllegalMoveToCheckError):
        game.move("E4", "F4")


def test_illegal_move_in_check():
    game = Game()

    game.move("A2", "A3")
    game.move("A7", "A6")
    game.move("B1", "C3")
    game.move("B7", "B6")
    game.move("B2", "B3")
    game.move("D7", "D6")
    game.move("C1", "B2")
    game.move("F7", "F6")
    game.move("D2", "D4")
    game.move("G7", "G6")
    game.move("D1", "D3")
    game.move("H7", "H6")
    game.move("E1", "C1")
    game.move("H6", "H5")
    game.move("C1", "D2")
    game.move("C8", "F5")
    game.move("D3", "E3")
    game.move("F5", "E4")
    game.move("E3", "D3")
    game.move("E4", "F5")
    game.move("D3", "E4")
    game.move("A6", "A5")
    game.move("D2", "D3")
    game.move("B6", "B5")
    game.move("H2", "H3")
    game.move("F5", "E4")

    assert not game.board.get_king(Team.WHITE).is_safe

    with raises(IllegalMoveToCheckError):
        game.move("B3", "B4")

    game.move("C3", "E4")

    assert game.board.get_king(Team.WHITE).is_safe


def test_team_rows():
    b = Team.BLACK
    w = Team.WHITE

    assert b.home == w.goal
    assert w.home == b.goal


def test_cell_set_piece():
    game = Game()

    cell = game.cell("A1")
    piece = cell.piece

    assert piece is not None

    cell.piece = piece


def test_cell_set_board():
    game = Game()

    cell = game.cell("A1")
    board = cell.board

    assert board is not None

    cell.board = board


def test_cell_operators():
    game = Game()

    assert game.cell("A1") == game.cell("A1")
    assert game.cell("A1") != game.cell("A2")
    assert game.cell("A1") < game.cell("A2")
    assert game.cell("A2") > game.cell("A1")


def test_get_king():
    game = Game()
    cell = game.cell("E1")

    assert game.board.get_king(Team.WHITE) is cell.piece

    cell.piece = None

    with raises(IndexError):
        game.board.get_king(Team.WHITE)


def test_stale_board_ref():
    game = Game()
    cell = game.cell("A2")
    game._board = None
    game = Game()

    with raises(ReferenceError):
        cell.board.move_piece(cell.piece, cell)


def test_piece_symbols():
    for (type, team), char in zip(
        (
            (type, team)
            for type in (Pawn, Rook, Knight, Bishop, Queen, King)
            for team in Team
        ),
        "♙ ♟ ♖ ♜ ♘ ♞ ♗ ♝ ♕ ♛ ♔ ♚".split(" "),
    ):
        assert str(type(team)) == char
