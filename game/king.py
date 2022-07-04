from game.error import (
    IllegalMoveCastlingMovedKingError,
    IllegalMoveCastlingMovedRookError,
    IllegalMoveSpacesMoreThanOneError,
    IllegalMoveTakingPieceError,
    IllegalMoveThroughCheckError,
    IllegalMoveThroughPieceError,
)

from .board import Cell, Piece, Team


class King(Piece):
    def __init__(self, team: Team, has_moved: bool = False):
        super().__init__(team, has_moved)

        self.is_castling = False

    @staticmethod
    def symbol(team: Team) -> str:
        return "♔" if team is Team.BLACK else "♚"

    def check_take(self, cell: Cell):
        if self.cell is None:
            raise ReferenceError

        if self.cell is cell:
            return

        x = self.cell.x - cell.x
        dx = abs(x)
        dy = abs(self.cell.y - cell.y)

        if dx > 2 or dy > 1 or (dx == 2 and dy != 0):
            raise IllegalMoveSpacesMoreThanOneError(self.cell, cell)

        if cell.piece is not None and cell.piece.team is self.team:
            raise IllegalMoveTakingPieceError(self.cell, cell)

        if dx == 2:
            """
            Rules for castling:
            - The king can not have moved
            - The rook can not have moved
            - The king can not be in check
            - The king can not pass through check
            - No pieces can be between the king and rook
            """

            if self.has_moved:
                raise IllegalMoveCastlingMovedKingError(self.cell, cell)

            rook_cell = self.cell.board[cell.y][0 if x > 0 else 7]

            if rook_cell.piece is None or rook_cell.piece.has_moved:
                raise IllegalMoveCastlingMovedRookError(self.cell, cell, rook_cell)

            t = (self.cell.x, cell.x) if self.cell.x < cell.x else (cell.x, self.cell.x)

            for c in (self.cell.board[cell.y][x] for x in range(*t)):
                if c is self.cell:
                    continue

                if c.piece is not None:
                    raise IllegalMoveThroughPieceError(self.cell, cell, c)

                if not c.is_safe(self.team):
                    raise IllegalMoveThroughCheckError(self.cell, cell)

            rook_cell.piece.check_take(cell.left(1) if x < 0 else cell.right(1))
