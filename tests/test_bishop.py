from game import Game, Turn


def test_move_D2D3C1E3():
    game = Game()
    game.turn = Turn.WHITE

    assert len(game.moves("C1")) == 0

    game.move("D2", "D3")

    assert game.moves("C1") == game.cells("D2", "E3", "F4", "G5", "H6")

    game.move("C1", "E3")

    assert game.moves("E3") == game.cells(
        "F4",
        "A7",
        "C5",
        "D2",
        "C1",
        "D4",
        "B6",
        "G5",
        "H6",
    )
