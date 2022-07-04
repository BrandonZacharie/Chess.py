from pytest import raises

from game import Game, Rook, Turn
from game.error import (
    IllegalMoveCastlingMovedKingError,
    IllegalMoveCastlingMovedRookError,
    IllegalMoveThroughCheckError,
    IllegalMoveThroughPieceError,
)


def test_move_D2D3C1E3D1D2B1C3E1C1():
    game = Game()
    game.turn = Turn.WHITE

    assert len(game.moves("E1")) == 0

    game.move("D2", "D3")

    assert game.moves("E1") == game.cells("D2")

    game.move("C1", "E3")
    game.move("D1", "D2")

    assert game.moves("E1") == game.cells("D1")

    game.move("B1", "C3")

    assert game.moves("E1") == game.cells("D1", "C1")

    game.move("E1", "C1")

    assert isinstance(game.cell("D1").piece, Rook)


def test_move_E2E3F1D3G1E2E1G1():
    game = Game()
    game.turn = Turn.WHITE

    assert len(game.moves("E1")) == 0

    game.move("E2", "E3")

    assert game.moves("E1") == game.cells("E2")

    game.move("F1", "D3")

    assert game.moves("E1") == game.cells("E2", "F1")

    game.move("G1", "E2")

    assert game.moves("E1") == game.cells("F1", "G1")

    game.move("E1", "G1")

    assert isinstance(game.cell("F1").piece, Rook)


def test_illegal_castling_partner():
    game = Game()

    for move in (
        ("A2", "A4"),
        ("A7", "A5"),
        ("B1", "A3"),
        ("B8", "A6"),
        ("B2", "B3"),
        ("B7", "B6"),
        ("C1", "B2"),
        ("C8", "B7"),
        ("C2", "C3"),
        ("C7", "C6"),
        ("D1", "C2"),
        ("D8", "C7"),
        ("A1", "A2"),
        ("E8", "D8"),
        ("A2", "A1"),
        ("D8", "E8"),
        ("A1", "A2"),
        ("D7", "D6"),
    ):
        game.move(*move)

    with raises(IllegalMoveCastlingMovedRookError):
        game.move("E1", "C1")


def test_illegal_castling_moved():
    game = Game()

    for move in (
        ("A2", "A4"),
        ("A7", "A5"),
        ("B1", "A3"),
        ("B8", "A6"),
        ("B2", "B3"),
        ("B7", "B6"),
        ("C1", "B2"),
        ("C8", "B7"),
        ("C2", "C3"),
        ("C7", "C6"),
        ("D1", "C2"),
        ("D8", "C7"),
        ("A1", "A2"),
        ("E8", "D8"),
        ("A2", "A1"),
        ("D8", "E8"),
    ):
        game.move(*move)

    with raises(IllegalMoveCastlingMovedRookError):
        game.move("E1", "C1")

    game.move("D2", "D3")

    with raises(IllegalMoveCastlingMovedKingError):
        game.move("E8", "C8")


def test_illegal_castling_through():
    game = Game()

    for move in (
        ("A2", "A4"),
        ("A7", "A5"),
        ("B1", "A3"),
        ("B8", "A6"),
        ("B2", "B3"),
        ("B7", "B6"),
        ("C1", "B2"),
        ("C8", "B7"),
        ("C2", "C3"),
        ("C7", "C6"),
        ("D1", "C2"),
        ("D8", "C7"),
        ("C2", "B1"),
        ("D7", "D6"),
    ):
        game.move(*move)

    with raises(IllegalMoveThroughPieceError):
        game.move("E1", "C1")

    game.move("B1", "A2")
    game.move("C7", "D8")
    game.move("E1", "C1")

    with raises(IllegalMoveThroughPieceError):
        game.move("E8", "C8")


def test_illegal_move_through_check():
    game = Game()

    for move in (
        ("A2", "A4"),
        ("A7", "A5"),
        ("B1", "A3"),
        ("B8", "A6"),
        ("B2", "B3"),
        ("B7", "B6"),
        ("C1", "B2"),
        ("C8", "B7"),
        ("C2", "C3"),
        ("C7", "C6"),
        ("D1", "C2"),
        ("D8", "C7"),
        ("C2", "B1"),
        ("D7", "D6"),
        ("B1", "F5"),
    ):
        game.move(*move)

    with raises(IllegalMoveThroughCheckError):
        game.move("E8", "C8")
