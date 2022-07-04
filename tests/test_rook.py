from pytest import raises

from game import Game, Pawn, Rook, Turn
from game.error import IllegalMoveTakingPieceError, IllegalMoveThroughPieceError


def test_move_A2A4A1A3():
    game = Game()
    game.turn = Turn.WHITE

    assert len(game.moves("A1")) == 0

    game.move("A2", "A4")

    assert game.moves("A1") == game.cells("A2", "A3")

    game.move("A1", "A3")

    assert game.moves("A3") == game.cells(
        "A2",
        "A1",
        "B3",
        "C3",
        "D3",
        "D3",
        "E3",
        "F3",
        "G3",
        "H3",
    )


def test_illegal_move_taking_piece():
    game = Game()

    with raises(IllegalMoveTakingPieceError):
        game.move("A1", "A2")

    assert isinstance(game.cell("A1").piece, Rook)
    assert isinstance(game.cell("A2").piece, Pawn)


def test_illegal_move_through_piece():
    game = Game()

    with raises(IllegalMoveThroughPieceError):
        game.move("A1", "A3")

    assert isinstance(game.cell("A1").piece, Rook)
    assert isinstance(game.cell("A2").piece, Pawn)
