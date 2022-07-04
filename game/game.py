from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from enum import Enum
from json import dumps, loads
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    TypeAlias,
    cast,
)

from semver import VersionInfo

from .board import (
    Bishop,
    Board,
    BoardSerializable,
    Cell,
    King,
    Knight,
    Log,
    Pawn,
    Piece,
    Point,
    Queen,
    Rook,
    Team,
)
from .error import (
    IllegalMoveError,
    IllegalMoveOutOfTurnError,
    IllegalMoveWhilePromotingError,
    IllegalPromotionTypeError,
)

Query: TypeAlias = Cell | Piece | str | Tuple[int | str, int | str]
Handler: TypeAlias = Callable[["Game", Tuple[Any, ...]], None]

PIECE_NAME_TYPE_MAP: dict[str, Type[Piece]] = {
    str(t): cast(Type[Piece], t) for t in (King, Queen, Bishop, Knight, Rook, Pawn)
}


class Turn(Enum):
    value: Optional[Team]

    AUTO: Optional[Team] = None
    WHITE = Team.WHITE
    BLACK = Team.BLACK


class Game:
    VERSION = VersionInfo(1, 0, 0)

    def __init__(self, game: Optional[Game] = None) -> None:
        if game is None:
            self._created = datetime.now()
            self._first_turn = Turn.AUTO
            self._next_turn = Turn.AUTO
            self._last_turn = Turn.AUTO
            self._board: Optional[Board] = None
            self._handlers: Dict[str, Set[Handler]] = defaultdict(set)
        else:
            self._created = game._created
            self._first_turn = game._first_turn
            self._next_turn = game._next_turn
            self._last_turn = game._last_turn
            self._board = game._board
            self._handlers = game._handlers

    @property
    def board(self) -> Board:
        if self._board is None:
            self._board = Board()

        return self._board

    @property
    def turn(self) -> Turn:
        return (
            self._next_turn
            if self._next_turn != Turn.AUTO
            else (
                Turn(Team(not cast(Team, self._last_turn.value).value))
                if self._last_turn != Turn.AUTO
                else (
                    self._first_turn
                    if self._first_turn != Turn.AUTO
                    else (
                        Turn.WHITE
                        if self._board is None or len(self._board.log) == 0
                        else Turn(
                            Team(Game().cell(self.board.log.entry(0)[0]).piece.team)
                        )
                    )
                )
            )
        )

    @turn.setter
    def turn(self, turn: Turn):
        self._next_turn = turn

    def reset(self):
        Game.__init__(self)
        self.notify("reset")

    def serializable(self, version: str | int | float = 2) -> Optional[Dict[str, str]]:
        if self._board is None:
            return None

        version_info = VersionInfo.parse(
            version if isinstance(version, str) else f"{float(version)}.0"
        )
        data: Dict[str, Any] = {
            "fileVersion": str(version_info),
            "gameVersion": str(self.VERSION),
            "created": self._created.isoformat(),
            "preview": f"\n{str(self._board)}",
        }

        match version_info.major:
            case 1:
                data["board"] = self._board.serializable()
            case 2:
                data["log"] = self._board.log
            case _:
                raise ValueError("Invalid version")

        return data

    def save(self, filename: str, version: str | int | float = 2) -> bool:
        data = self.serializable(version)

        if data is None:
            return False

        with open(filename, "w") as f:
            f.write(dumps(data))

        self.notify("save")

        return True

    def load(self, filename: str):
        with open(filename, "r") as f:
            s = f.read()
            data = loads(s)
            version_info = VersionInfo.parse(data["fileVersion"])
            game = Game()
            game._created = datetime.fromisoformat(data["created"])

            match version_info.major:
                case 1:
                    types: List[Type[Piece]] = [Pawn, Rook, Knight, Bishop, Queen, King]
                    type_map: Dict[str, Type[Piece]] = {t.__name__: t for t in types}
                    game._board = Board(False)

                    for y, cells in enumerate(cast(BoardSerializable, data["board"])):
                        for x, piece in enumerate(cells):
                            if piece is not None:
                                kind = str(piece["kind"])
                                team = Team(bool(piece["team"]))
                                has_moved = bool(piece["has_moved"])
                                game.board[y][x].piece = type_map[kind](team, has_moved)
                case 2:
                    log: Log[List] = Log(data["log"])
                    size = len(log)

                    if size > 0:
                        cell = game.cell(log.entry(0)[0])

                        if cell.piece is None:
                            raise ValueError("Invalid log entry")

                        game._first_turn = Turn(cell.piece.team)

                        for i in range(size):
                            entry = log.entry(i)
                            a, b = entry

                            if isinstance(b, str):
                                game.promote(a, PIECE_NAME_TYPE_MAP.get(b, Pawn))
                            else:
                                game.move(a, b)
                case _:
                    raise ValueError("Unsupported version")

        Game.__init__(self, game)
        self.notify("load")

    def loads(self, s: str):
        board = Board(initialize=False)
        chmap: dict[str, Tuple[Type[Piece], Team]] = {
            type.symbol(team): (type, team)  # type: ignore
            for team in Team
            for type in (Pawn, Rook, Knight, Bishop, Queen, King)
        }
        y = -1

        for yv in s.strip().splitlines()[1:-1]:
            xv = yv.strip()[:-2].split(" │ ")[1:]

            if len(xv) == 8:
                y += 1

                for x, v in enumerate(xv):
                    ch = v.strip()

                    if len(ch) == 1:
                        t, team = chmap[ch]
                        piece = t(team)
                        piece.has_moved = True
                        board[y][x].piece = piece

        self._board = board

        self.notify("load")

    def point(self, q: Query) -> Point:
        if isinstance(q, str | tuple):
            if len(q) != 2:
                raise ValueError

            x, y = q if isinstance(q, tuple) else (q[0], q[1])

            if isinstance(x, str):
                x = ord(x) - 65

            if isinstance(y, str):
                y = 7 - (ord(y) - 49)

            if not (-1 < x < 8 and -1 < y < 8):
                raise ValueError

            return (x, y)

        if isinstance(q, Cell):
            return q.point

        if q.cell is not None:
            return q.cell.point

        raise ValueError

    def cell(self, q: Query) -> Cell:
        x, y = self.point(q)

        return self.board[y][x]

    def cells(self, *q: Query) -> Set[Cell]:
        return set(self.cell(q) for q in q)

    def move(self, q1: Query, q2: Query):
        cell1, cell2 = self.cell(q1), self.cell(q2)

        if self.board.get_promotable() is not None:
            raise IllegalMoveWhilePromotingError(cell1, cell2)

        p1 = cell1.piece
        p2 = cell2.piece

        if p1 is None:
            raise IllegalMoveError(None, cell1, cell2)

        turn = Turn(p1.team)

        if self.turn != turn:
            raise IllegalMoveOutOfTurnError(cell1, cell2)

        x = cell1.x - cell2.x
        dx = abs(x)
        y = cell1.y - cell2.y
        dy = abs(y)

        self.board.move_piece(p1, cell2)

        if isinstance(p1, Pawn) and dx == 1 and dy == 1 and p2 is None:
            (cell2.down(1) if p1.is_white else cell2.up(1)).piece = None
        elif isinstance(p1, King) and dx == 2:
            rook_cell1 = self.board[cell2.y][0 if x > 0 else 7]
            rook_cell2 = cell2.left(1) if rook_cell1.x > cell2.x else cell2.right(1)
            p1.is_castling = True

            try:
                self.board.move_piece(rook_cell1.piece, rook_cell2)
            finally:
                p1.is_castling = False

        self._last_turn = turn

        self.board.log.append((cell1.point, cell2.point))
        self.notify("move")

    def promote(self, q: Query, t: Type[Piece]):
        cell = self.cell(q)
        promotable = self.board.get_promotable()

        if cell != promotable:
            raise IllegalMoveError("cannot promote", cell)

        if cell.piece is None or not isinstance(cell.piece, Pawn) or t in (Pawn, King):
            raise IllegalPromotionTypeError(cell, t)

        cell.piece = t(cell.piece.team, has_moved=True)

        self.board.log.append((cell.point, str(t)))
        self.notify("promote")

    def moves(self, q: Query) -> Set[Cell]:
        cell = self.cell(q)

        return set(
            c
            for row in self.board
            for c in row
            if c is not cell and cell.piece is not None and cell.piece.can_take(c)
        )

    def notify(self, event: str, *args):
        for handler in self._handlers[event].copy():
            handler(self, args)

        if event != "notify":
            self.notify("notify", event)

    def add_event_handler(self, event: str, handler: Handler, once: bool = False):
        if once:
            old_handler = handler

            def new_handler(game: Game, args):
                old_handler(game, args)
                self.remove_event_handler(event, new_handler)

            handler = new_handler

        self._handlers[event].add(handler)

    def remove_event_handler(self, event: str, handler: Handler):
        try:
            self._handlers[event].remove(handler)
        except KeyError:
            pass
