from typing import Optional, Type

from .board import Cell


class IllegalMoveError(RuntimeError):
    def __init__(
        self,
        message: Optional[str],
        cell1: Optional[Cell] = None,
        cell2: Optional[Cell] = None,
        cell3: Optional[Cell] = None,
    ):
        prefix: Optional[str]

        match (cell1, cell2):
            case c1, c2 if c1 is not None and c1.piece and c2:
                prefix = f"Unable to move {c1.piece.name} {c1.name} to {c2.name}"
            case c1, c2 if c1 is not None and c1.piece and not c2:
                prefix = f"Unable to move {c1.piece.name}"
            case c1, c2 if c1 is not None and not c1.piece and c2:
                prefix = f"No piece to move at {c1.name} to {c2.name}"
            case c1, c2 if c1 is not None and not c1.piece and not c2:
                prefix = f"No piece to move at {c1.name}"
            case _:
                prefix = None

        suffix = (
            "."
            if cell3 is None
            else (
                f" at {cell3.name}."
                if cell3.piece is None
                else f" {cell3.piece.name} {cell3.name}."
            )
        )

        if message is not None and cell1 is not None and cell1.piece is not None:
            message = f"{cell1.piece.name} {message}"

        super().__init__("; ".join(filter(None, (prefix, message))) + suffix)


class IllegalMoveThroughPieceError(IllegalMoveError):
    def __init__(self, cell1: Cell, cell2: Cell, cell3: Cell):
        super().__init__(f"cannot move through", cell1, cell2, cell3)


class IllegalMoveThroughCheckError(IllegalMoveError):
    def __init__(self, cell1: Optional[Cell], cell2: Optional[Cell] = None):
        super().__init__("cannot move through check", cell1, cell2)


class IllegalMoveToCheckError(IllegalMoveError):
    def __init__(self, cell1: Optional[Cell], cell2: Optional[Cell] = None):
        super().__init__("cannot move to check", cell1, cell2)


class IllegalMoveTakingPieceError(IllegalMoveError):
    def __init__(self, cell1: Cell, cell2: Cell):
        super().__init__(f"cannot take own", cell1, cell2, cell2)


class IllegalMoveOutOfTurnError(IllegalMoveError):
    def __init__(self, cell1: Cell, cell2: Cell):
        super().__init__("cannot move out of turn", cell1, cell2)


class IllegalMoveWhilePromotingError(IllegalMoveError):
    def __init__(self, cell1: Cell, cell2: Cell):
        super().__init__("cannot move before promoting", cell1, cell2)


class IllegalMoveSpacesMoreThanOneError(IllegalMoveError):
    def __init__(self, cell1: Cell, cell2: Cell):
        super().__init__("can only move 1 space", cell1, cell2)


class IllegalMoveSpacesMoreThanTwoError(IllegalMoveError):
    def __init__(self, cell1: Cell, cell2: Cell):
        super().__init__("can only move 2 spaces", cell1, cell2)


class IllegalMoveDirectionDiagonalError(IllegalMoveError):
    def __init__(self, cell1: Cell, cell2: Cell):
        super().__init__("cannot move diagonally", cell1, cell2)


class IllegalMoveDirectionHorizontalError(IllegalMoveError):
    def __init__(self, cell1: Cell, cell2: Cell):
        super().__init__("cannot move horizontally", cell1, cell2)


class IllegalMoveDirectionBackwardError(IllegalMoveError):
    def __init__(self, cell1: Cell, cell2: Cell):
        super().__init__("cannot move backwards", cell1, cell2)


class IllegalMoveDirectionForBishopError(IllegalMoveError):
    def __init__(self, cell1: Cell, cell2: Cell):
        super().__init__("can only move diagonally", cell1, cell2)


class IllegalMoveDirectionForKnightError(IllegalMoveError):
    def __init__(self, cell1: Cell, cell2: Cell):
        super().__init__("can only move in L shape", cell1, cell2)


class IllegalMoveDirectionForQueenError(IllegalMoveError):
    def __init__(self, cell1: Cell, cell2: Cell):
        super().__init__("can only move straight", cell1, cell2)


class IllegalMoveCastlingMovedKingError(IllegalMoveError):
    def __init__(self, cell1: Cell, cell2: Cell):
        super().__init__("cannot castle once moved", cell1, cell2)


class IllegalMoveCastlingMovedRookError(IllegalMoveError):
    def __init__(self, cell1: Cell, cell2: Cell, cell3: Cell):
        suffix = "out Rook" if cell3.piece is None else " moved"

        super().__init__(f"cannot castle with{suffix}", cell1, cell2, cell3)


class IllegalPromotionTypeError(IllegalMoveError):
    def __init__(self, cell1: Cell, type: Type):
        super().__init__(f"cannot be promoted to {type.__name__}", cell1)


class IllegalMoveTakingKingError(IllegalMoveError):
    def __init__(self, cell1: Optional[Cell], cell2: Cell):
        super().__init__("cannot take King", cell1, cell2)
