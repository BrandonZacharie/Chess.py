from typing import cast

from pytest import raises

from game import Game, King, Pawn, Queen, Turn
from game.error import (
    IllegalMoveError,
    IllegalMoveThroughPieceError,
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


def test_illegal_move_take_own_piece():
    game = Game()
    game.turn = Turn.WHITE

    game.move("A2", "A4")
    game.move("B2", "B3")

    with raises(IllegalMoveError):
        game.move("B3", "A4")


def test_illegal_intial_move():
    game = Game()

    # Felber, Joesph J vs. Nakamura, Hikaru; New York, 1998

    game.move("E2", "E4")
    game.move("C7", "C5")
    game.move("G1", "F3")
    game.move("B8", "C6")
    game.move("D2", "D4")
    game.move("C5", "D4")
    game.move("F3", "D4")
    game.move("G8", "F6")
    game.move("B1", "C3")
    game.move("E7", "E5")
    game.move("D4", "B5")
    game.move("D7", "D6")
    game.move("C1", "G5")
    game.move("A7", "A6")
    game.move("G5", "F6")
    game.move("G7", "F6")
    game.move("B5", "A3")
    game.move("B7", "B5")
    game.move("C3", "D5")
    game.move("F8", "E7")
    game.move("G2", "G3")
    game.move("C8", "E6")
    game.move("F1", "G2")
    game.move("A8", "C8")
    game.move("C2", "C3")
    game.move("E8", "G8")
    game.move("A3", "C2")

    with raises(IllegalMoveThroughPieceError):
        game.move("F7", "F5")


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

    game.promote(Queen)


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
        game.promote(Queen)

    game.move((2, 6), (3, 7))

    with raises(IllegalMoveWhilePromotingError):
        game.move("D5", "D6")

    with raises(IllegalPromotionTypeError):
        game.promote(Pawn)

    with raises(IllegalPromotionTypeError):
        game.promote(King)


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
    game.promote(Queen)

    assert game.moves("C4") == game.cells("C3")
