from game.error import (
    IllegalMoveDirectionDiagonalError,
    IllegalMoveTakingPieceError,
    IllegalMoveThroughPieceError,
)

from .board import Cell, Direction, King, Piece, Team


class Rook(Piece):
    @staticmethod
    def symbol(team: Team) -> str:
        return "♖" if team is Team.BLACK else "♜"

    def check_take(self, cell: Cell):
        if self.cell is None:
            raise ReferenceError

        if self.cell is cell:
            return True

        if cell.x != self.cell.x and cell.y != self.cell.y:
            raise IllegalMoveDirectionDiagonalError(self.cell, cell)

        x = self.cell.x - cell.x
        y = self.cell.y - cell.y
        direction = (
            Direction.UP
            if y > 0
            else (
                Direction.DOWN
                if y < 0
                else Direction.LEFT if x > 0 else Direction.RIGHT
            )
        )
        distance = max(abs(x), abs(y))
        cells = self.cell.board.get_cells(self.cell, direction, distance)

        for c in cells[1:]:
            ### NOTE: Maybe this is not needed. Is self sliced out with [1:]?
            ### if c is cell:
            ###    break

            if c.piece is not None and not (
                isinstance(c.piece, King) and c.piece.is_castling
            ):
                raise IllegalMoveThroughPieceError(self.cell, cell, c)

        if cell.piece is not None and cell.piece.team is self.team:
            raise IllegalMoveTakingPieceError(self.cell, cell)
