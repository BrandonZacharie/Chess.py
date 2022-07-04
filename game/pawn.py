from game.error import (
    IllegalMoveDirectionBackwardError,
    IllegalMoveDirectionDiagonalError,
    IllegalMoveDirectionHorizontalError,
    IllegalMoveSpacesMoreThanOneError,
    IllegalMoveSpacesMoreThanTwoError,
    IllegalMoveTakingPieceError,
    IllegalMoveThroughPieceError,
)

from .board import Cell, Piece, Team


class Pawn(Piece):
    @staticmethod
    def symbol(team: Team) -> str:
        return "♙" if team is Team.BLACK else "♟"

    def __str__(self) -> str:
        return self.symbol(self.team)

    def check_take(self, cell: Cell):
        if self.cell is None:
            raise ReferenceError

        if self.cell is cell:
            return

        x = cell.x - self.cell.x
        y = cell.y - self.cell.y

        if (self.is_black and y < 0) or (self.is_white and y > 0):
            raise IllegalMoveDirectionBackwardError(self.cell, cell)

        dx = abs(x)
        dy = abs(y)

        if dx > 1 or (dx == 1 and dy == 0):
            raise IllegalMoveDirectionHorizontalError(self.cell, cell)

        if dy > 2 or dx >= 1 and dy > 1:
            raise IllegalMoveSpacesMoreThanTwoError(self.cell, cell)

        if dy == 2 and self.has_moved:
            # can't move 2 spaces after having moved
            raise IllegalMoveSpacesMoreThanOneError(self.cell, cell)

        if cell.piece is None:
            if dx == 1 and dy == 1:
                piece = (cell.down(1) if self.is_white else cell.up(1)).piece

                if not isinstance(piece, Pawn) or not piece.is_en_passant():
                    raise IllegalMoveDirectionDiagonalError(self.cell, cell)
        else:
            if dx == 0 and dy == 1:
                # can't vertically take a piece
                raise IllegalMoveThroughPieceError(self.cell, cell, cell)

            if cell.piece.team is self.team:
                raise IllegalMoveTakingPieceError(self.cell, cell)

    def is_en_passant(self) -> bool:
        if self.cell is None:
            return False

        try:
            a, b = self.cell.board.log[-1]
        except IndexError:
            return False

        if isinstance(b, str) or not isinstance(b[0], int):
            return False

        x, y = b

        if self.cell is not self.cell.board[y][x]:
            return False

        x, y = a
        dx = abs(self.cell.x - x)
        dy = abs(self.cell.y - y)

        return dx == 0 and dy == 2
