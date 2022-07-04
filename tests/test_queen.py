from pytest import mark

from game import Game, Queen, Team, Turn


@mark.parametrize("cell", ["D1", "A1", "G1", "H4", "H8", "D8", "A7"])
def test_move_directions(cell: str):
    s = """
        ──┬───┬───┬───┬───┬───┬───┬───┬───┐
        8 │   │   │   │   │   │   │   │   │
        ──┼───┼───┼───┼───┼───┼───┼───┼───┤
        7 │   │   │   │   │   │   │   │   │
        ──┼───┼───┼───┼───┼───┼───┼───┼───┤
        6 │   │   │   │   │   │   │   │   │
        ──┼───┼───┼───┼───┼───┼───┼───┼───┤
        5 │   │   │   │   │   │   │   │   │
        ──┼───┼───┼───┼───┼───┼───┼───┼───┤
        4 │   │   │   │ ♛ │   │   │   │   │
        ──┼───┼───┼───┼───┼───┼───┼───┼───┤
        3 │   │   │   │   │   │   │   │   │
        ──┼───┼───┼───┼───┼───┼───┼───┼───┤
        2 │   │   │   │   │   │   │   │   │
        ──┼───┼───┼───┼───┼───┼───┼───┼───┤
        1 │   │   │   │   │   │   │   │   │
        ──┼───┼───┼───┼───┼───┼───┼───┼───┤
          │ A │ B │ C │ D │ E │ F │ G │ H │
        """
    game = Game()

    game.loads(s)

    assert isinstance(game.cell("D4").piece, Queen)

    game.move("D4", cell)

    assert isinstance(game.cell(cell).piece, Queen)


def test_move_C2C3D1A4():
    game = Game()
    game.turn = Turn.WHITE

    assert len(game.moves("D1")) == 0

    game.move("C2", "C3")

    assert game.moves("D1") == game.cells("A4", "B3", "C2")

    game.move("D1", "A4")

    assert game.moves("A4") == game.cells(
        "A3",
        "A5",
        "A6",
        "A7",
        "B3",
        "B4",
        "B5",
        "C2",
        "C4",
        "C6",
        "D1",
        "D4",
        "D7",
        "E4",
        "F4",
        "G4",
        "H4",
    )
