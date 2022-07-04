from game import Game, Turn


def test_move_B1C3B5C7A8():
    game = Game()
    game.turn = Turn.WHITE

    assert game.moves("B1") == game.cells("A3", "C3")

    game.move("B1", "C3")

    assert game.moves("C3") == game.cells("B5", "D5", "A4", "E4", "B1")

    game.move("C3", "B5")

    assert game.moves("B5") == game.cells("A7", "C7", "D6", "D4", "A3", "C3")

    game.move("B5", "C7")

    assert game.moves("C7") == game.cells("A8", "E8", "A6", "E6", "B5", "D5")

    game.move("C7", "A8")

    assert game.moves("A8") == game.cells("C7", "B6")
