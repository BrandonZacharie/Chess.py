from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import (
    Any,
    Dict,
    Generic,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeAlias,
    TypeVar,
    Union,
    cast,
)
from weakref import ReferenceType, ref

PieceSerializable: TypeAlias = Dict[str, str | bool]
CellSerializable: TypeAlias = Optional[PieceSerializable]
BoardSerializable: TypeAlias = List[List[CellSerializable]]
Point: TypeAlias = Tuple[int, int]
LogMove: TypeAlias = Tuple[Point, Point]
LogEvent: TypeAlias = Tuple[Point, str]
LogEntry: TypeAlias = Union[LogMove, LogEvent]
ST = TypeVar("ST", bound=Sequence[Point] | LogEvent)


class Direction(Enum):
    value: Tuple[int, int]

    UP = (0, 1)
    UP_LEFT = (-1, 1)
    UP_RIGHT = (1, 1)
    DOWN = (0, -1)
    DOWN_LEFT = (-1, -1)
    DOWN_RIGHT = (1, -1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)


class Team(Enum):
    value: bool

    BLACK = True
    WHITE = False

    @property
    def home(self) -> int:
        return 7 if self is Team.BLACK else 0

    @property
    def goal(self) -> int:
        return 0 if self is Team.BLACK else 7


class Piece(ABC):
    def __init__(self, team: Team, has_moved: bool = False):
        self._cell: Optional[ReferenceType[Optional[Cell]]] = None
        self.team = team
        self.has_moved = has_moved

    def __str__(self) -> str:
        return self.symbol(self.team)

    @property
    def name(self) -> str:
        return self.__class__.__name__

    @property
    def is_black(self) -> bool:
        return self.team is Team.BLACK

    @property
    def is_white(self) -> bool:
        return self.team is Team.WHITE

    @property
    def is_safe(self) -> bool:
        return self.cell is None or self.cell.is_safe(self.team)

    @property
    def cell(self) -> Optional[Cell]:
        return self._cell() if self._cell is not None else None

    @cell.setter
    def cell(self, cell: Optional[Cell]) -> None:
        self._cell = None if cell is None else ref(cell)

    @abstractmethod
    def check_take(self, cell: Cell):
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def symbol(team: Team) -> str:
        raise NotImplementedError

    def can_take(self, cell: Cell) -> bool:
        try:
            self.check_take(cell)

            return True
        except:
            return False

    def serializable(self) -> PieceSerializable:
        return {
            "kind": self.__class__.__name__,
            "team": self.team.value,
            "has_moved": self.has_moved,
        }


class Log(Generic[ST], List[ST]):
    def entry(self, index: int) -> LogEntry:
        entry = self[index]
        e1, e2 = entry[0], entry[1]
        a1, b1 = e1

        if isinstance(e2, str):
            return cast(LogEvent, ((a1, b1), e2))

        if isinstance(e2, Sequence):
            # Pick the first two values.
            a2, b2 = e2

            if isinstance(a2, int) and isinstance(b2, int):

                # Return only the exact shape as is the return type.
                return cast(LogMove, ((a1, b1), (a2, b2)))

        raise ValueError


class Cell:
    def __init__(self, x: int, y: int, board: Board):
        self._piece: Optional[Piece] = None
        self._board: ReferenceType[Board] = ref(board)
        self.x = x
        self.y = y

    def __str__(self):  # pragma: no cover
        piece = " " if self.piece is None else str(self.piece)
        x, y = self.name[0], self.name[1]

        return f"\n   ┌───┐\n {y} │ {piece} │\n   └───┘\n     {x}"

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Cell) and self.x == __o.x and self.y == __o.y

    def __lt__(self, __o: object) -> bool:
        return isinstance(__o, Cell) and self.name < __o.name

    @property
    def name(self) -> str:
        return f"{chr(self.x + 65)}{8 - self.y}"

    @property
    def point(self) -> Point:
        return self.x, self.y

    @property
    def piece(self):
        return self._piece

    @piece.setter
    def piece(self, piece: Optional[Piece]):
        if self._piece is piece:
            return

        if self._piece is not None:
            self._piece.cell = None

        if piece is not None:
            if piece.cell is not None:
                piece.cell.piece = None

            piece.cell = self

        self._piece = piece

    @property
    def board(self) -> Board:
        return self._board() or StaleBoard()

    @board.setter
    def board(self, board: Board) -> None:
        self._board = ref(board)

    def is_safe(self, team: Team) -> bool:
        return self.board.is_safe_cell(self, team)

    def up(self, distance: int = 1) -> Cell:
        return self.board[self.y - distance][self.x]

    def down(self, distance: int = 1) -> Cell:
        return self.board[self.y + distance][self.x]

    def left(self, distance: int = 1) -> Cell:
        return self.board[self.y][self.x - distance]

    def right(self, distance: int = 1) -> Cell:
        return self.board[self.y][self.x + distance]

    def serializable(self) -> CellSerializable:
        return None if self.piece is None else self.piece.serializable()


class Move:
    def __init__(self, original_piece: Piece, destination_cell: Cell, taken_cell: Cell):
        self.original_piece = original_piece
        self.original_cell = original_piece.cell
        self.destination_cell = destination_cell
        self.taken_cell = taken_cell
        self.taken_piece: Optional[Piece] = None
        self.has_moved = original_piece.has_moved
        self.is_castling = (
            original_piece.is_castling if isinstance(original_piece, King) else False
        )

    def perform(self) -> None:
        if self.taken_cell.piece is not None:
            self.taken_piece = self.taken_cell.piece

        self.taken_cell.piece = None
        self.destination_cell.piece = self.original_piece
        self.original_piece.has_moved = True

        if self.original_cell is not None:
            self.original_cell.piece = None

    def reverse(self) -> None:
        if self.original_cell is not None:
            self.original_cell.piece = self.original_piece

        if isinstance(self.original_piece, King):
            self.original_piece.is_castling = self.is_castling

        self.destination_cell.piece = None
        self.taken_cell.piece = self.taken_piece
        self.original_piece.has_moved = self.has_moved


from .bishop import Bishop
from .king import King
from .knight import Knight
from .pawn import Pawn
from .queen import Queen
from .rook import Rook


class Board(List[List[Cell]]):
    def __init__(self, initialize: bool = True):
        if initialize:
            template: List[List[Optional[Type[Piece]]]] = [
                [
                    Rook,
                    Knight,
                    Bishop,
                    Queen,
                    King,
                    Bishop,
                    Knight,
                    Rook,
                ],
                [Pawn] * 8,
                [None] * 8,
                [None] * 8,
            ]
            template += reversed(template)
        else:
            template = [[None] * 8 for _ in range(8)]

        self.log = Log[LogEntry]()
        self.captures: Dict[Team, List[Piece]] = {Team.BLACK: [], Team.WHITE: []}

        def make_cell(x: int, y: int, t: Optional[Type[Piece]]) -> Cell:
            cell = Cell(x, y, self)

            if t is not None:
                cell.piece = t(Team(y < len(template) / 2))

            return cell

        super().__init__(
            [make_cell(x, y, t) for x, t in enumerate(types)]
            for y, types in enumerate(template)
        )

    def __str__(self) -> str:
        return (
            "\n ──┬─"
            + "─┬─".join("─" for _ in range(len(self[0])))
            + "─┐\n"
            + "\n".join(
                f" {len(cells) - i} │ "
                + " │ ".join(" " if c.piece is None else str(c.piece) for c in cells)
                + " │\n "
                + "─┼─".join("─" for _ in cells)
                + "─┼───┤"
                for i, cells in enumerate(self)
            )
            + "\n   │ "
            + " │ ".join(chr(65 + i) for i in range(len(self[-1])))
            + " │ "
        )

    def is_safe_cell(self, cell: Cell, team: Team) -> bool:
        for cells in self:
            for c in cells:
                if (
                    c is not cell
                    and c.piece is not None
                    and c.piece.team != team
                    and c.piece.can_take(cell)
                ):
                    return False

        return True

    def move_piece(self, piece: Piece, cell: Cell) -> Move:
        piece.check_take(cell)

        is_en_passant = (
            isinstance(piece, Pawn)
            and piece.cell is not None
            and abs(cell.y - piece.cell.y) == 1
            and abs(cell.x - piece.cell.x) == 1
            and cell.piece is None
        )
        move = Move(
            piece,
            cell,
            cell if not is_en_passant else cell.up() if piece.is_black else cell.down(),
        )

        move.perform()

        king = self.get_king(piece.team)

        if not king.is_safe:
            move.reverse()

            from .error import IllegalMoveThroughCheckError, IllegalMoveToCheckError

            Error = (
                IllegalMoveThroughCheckError
                if piece is king
                else IllegalMoveToCheckError
            )

            raise Error(piece.cell, cell)

        if move.taken_piece is not None and isinstance(move.taken_piece, King):
            from .error import IllegalMoveTakingKingError

            raise IllegalMoveTakingKingError(piece.cell, cell)

        if move.taken_piece is not None:
            self.captures[move.taken_piece.team].append(move.taken_piece)

        return move

    def try_move_piece(self, piece: Piece, cell: Cell) -> bool:
        try:
            self.move_piece(piece, cell)
        except:
            return False

        return True

    def get_cells(self, start: Cell, direction: Direction, max: int = 8) -> List[Cell]:
        cells: List[Cell] = []
        ox, oy = direction.value

        for i in range(max):
            x = start.x + (i * ox) if ox != 0 else start.x
            y = start.y - (i * oy) if oy != 0 else start.y

            if not -1 < x < 8 or not -1 < y < 8:
                break

            cells.append(self[y][x])

        return cells

    def get_king(self, team: Team) -> King:
        for cells in self:
            for cell in cells:
                if (
                    cell.piece is not None
                    and isinstance(cell.piece, King)
                    and cell.piece.team is team
                ):
                    return cell.piece

        raise IndexError

    def get_promotable(self) -> Optional[Cell]:
        return next(
            (
                cell
                for team in Team
                for cell in self.get_cells(self[team.home][0], Direction.RIGHT)
                if isinstance(cell.piece, Pawn)
            ),
            None,
        )

    def serializable(self) -> BoardSerializable:
        return [[cell.serializable() for cell in cells] for cells in self]


class StaleBoard(Board):
    def __getattribute__(self, _) -> Any:
        raise ReferenceError
