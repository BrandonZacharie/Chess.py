from typing import cast

from pytest import raises

from game import Game, King, Pawn, Queen, Turn
from game.error import (
    IllegalMoveError,
    IllegalMoveWhilePromotingError,
    IllegalPromotionTypeError,
)


def test_moves_A2A4A5A6B7():
    game = Game()
    game.turn = Turn.WHITE

    assert game.moves("A2") == game.cells("A4", "A3")

    game.move("A2", "A4")

    assert game.moves("A4") == game.cells("A5")

    game.move("A4", "A5")

    assert game.moves("A5") == game.cells("A6")

    game.move("A5", "A6")

    assert game.moves("A6") == game.cells("B7")

    game.move("A6", "B7")

    assert game.moves("B7") == game.cells("A8", "C8")


def test_moves_B7B5B4B3C2():
    game = Game()
    game.turn = Turn.BLACK

    assert game.moves("B7") == game.cells("B6", "B5")

    game.move("B7", "B5")

    assert game.moves("B5") == game.cells("B4")

    game.move("B5", "B4")

    assert game.moves("B4") == game.cells("B3")

    game.move("B4", "B3")

    assert game.moves("B3") == game.cells("A2", "C2")

    game.move("B3", "C2")

    assert game.moves("C2") == game.cells("B1", "D1")


def test_illegal_move_take_own_piece():
    game = Game()
    game.turn = Turn.WHITE

    game.move("A2", "A4")
    game.move("B2", "B3")

    with raises(IllegalMoveError):
        game.move("B3", "A4")


def test_promote():
    game = Game()

    for move in (
        ((0, 6), (0, 4)),
        ((1, 1), (1, 3)),
        ((0, 4), (0, 3)),
        ((1, 3), (1, 4)),
        ((0, 3), (0, 2)),
        ((1, 4), (1, 5)),
        ((3, 6), (3, 4)),
        ((1, 5), (2, 6)),
        ((3, 4), (3, 3)),
        ((2, 6), (3, 7)),
    ):
        game.move(*move)

    game.promote("D1", Queen)


def test_illegal_promote():
    game = Game()

    for move in (
        ((0, 6), (0, 4)),
        ((1, 1), (1, 3)),
        ((0, 4), (0, 3)),
        ((1, 3), (1, 4)),
        ((0, 3), (0, 2)),
        ((1, 4), (1, 5)),
        ((3, 6), (3, 4)),
        ((1, 5), (2, 6)),
        ((3, 4), (3, 3)),
    ):
        game.move(*move)

    with raises(IllegalMoveError):
        game.promote("D1", Queen)

    game.move((2, 6), (3, 7))

    with raises(IllegalMoveWhilePromotingError):
        game.move("D5", "D6")

    with raises(IllegalPromotionTypeError):
        game.promote("D1", Pawn)

    with raises(IllegalPromotionTypeError):
        game.promote("D1", King)


def test_en_passant():
    game = Game()

    game.move("A2", "A4")
    game.move("A7", "A6")
    game.move("A4", "A5")
    game.move("B7", "B5")

    en_passant_pawn = cast(Pawn, game.cell("B5").piece)

    assert en_passant_pawn.is_en_passant()

    pawn = game.cell("A5").piece

    assert game.moves("A5") == game.cells("B6")

    game.move("A5", "B6")

    assert game.cell("B5").piece is None
    assert game.cell("A5").piece is None
    assert game.cell("B6").piece is pawn
    assert not en_passant_pawn.is_en_passant()

    game.move("C7", "C5")
    game.move("D2", "D4")
    game.move("C5", "C4")
    game.move("B2", "B4")

    assert game.moves("C4") == game.cells("B3", "C3")

    game.move("B8", "C6")
    game.move("B6", "B7")
    game.move("A8", "A7")
    game.move("B7", "B8")
    game.promote("B8", Queen)

    assert game.moves("C4") == game.cells("C3")
