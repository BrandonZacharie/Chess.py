from game.error import (
    IllegalMoveDirectionForQueenError,
    IllegalMoveTakingPieceError,
    IllegalMoveThroughPieceError,
)

from .board import Cell, Direction, Piece, Team


class Queen(Piece):
    @staticmethod
    def symbol(team: Team) -> str:
        return "♕" if team is Team.BLACK else "♛"

    def check_take(self, cell: Cell):
        if self.cell is None:
            raise ReferenceError

        if self.cell is cell:
            return True

        x = self.cell.x - cell.x
        y = self.cell.y - cell.y

        if x + y != 0 and x - y != 0 and x != 0 and y != 0:
            raise IllegalMoveDirectionForQueenError(self.cell, cell)

        direction = (
            Direction.UP
            if x == 0 and y > 0
            else (
                Direction.DOWN
                if x == 0 and y < 0
                else (
                    Direction.LEFT
                    if x > 0 and y == 0
                    else (
                        Direction.RIGHT
                        if x < 0 and y == 0
                        else (
                            Direction.UP_LEFT
                            if x > 0 and y > 0
                            else (
                                Direction.DOWN_RIGHT
                                if x < 0 and y < 0
                                else (
                                    Direction.UP_RIGHT
                                    if x < 0 and y > 0
                                    else Direction.DOWN_LEFT
                                )
                            )
                        )
                    )
                )
            )
        )
        distance = abs(x) + abs(y)
        cells = self.cell.board.get_cells(self.cell, direction, distance)

        for c in cells[1:]:
            if c is cell:
                break

            if c.piece is not None:
                raise IllegalMoveThroughPieceError(self.cell, cell, c)

        if cell.piece is not None and cell.piece.team is self.team:
            raise IllegalMoveTakingPieceError(self.cell, cell)
