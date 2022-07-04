from game.error import IllegalMoveDirectionForKnightError, IllegalMoveTakingPieceError

from .board import Cell, Piece, Team


class Knight(Piece):
    @staticmethod
    def symbol(team: Team) -> str:
        return "♘" if team is Team.BLACK else "♞"

    def check_take(self, cell: Cell):
        if self.cell is None:
            raise ReferenceError

        if self.cell is cell:
            return

        dx = abs(self.cell.x - cell.x)
        dy = abs(self.cell.y - cell.y)

        if not ((dx == 1 and dy == 2) or (dx == 2 and dy == 1)):
            raise IllegalMoveDirectionForKnightError(self.cell, cell)

        if cell.piece is not None and cell.piece.team is self.team:
            raise IllegalMoveTakingPieceError(self.cell, cell)
