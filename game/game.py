from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from enum import Enum
from json import dumps, loads
from os import getcwd, path
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

from pgn import PGNGame
from pgn import loads as pgn_loads
from semver import VersionInfo

from .board import (
    Bishop,
    Board,
    BoardSerializable,
    Cell,
    King,
    Knight,
    Move,
    Pawn,
    Piece,
    PlainNotationLog,
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
    "K": King,
    "Q": Queen,
    "B": Bishop,
    "N": Knight,
    "R": Rook,
    "P": Pawn,
}
PIECE_TYPE_NAME_MAP: dict[Type[Piece], str] = {
    King: "K",
    Queen: "Q",
    Bishop: "B",
    Knight: "N",
    Rook: "R",
    Pawn: "P",
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
                        if self._board is None or len(self._board.ilog) == 0
                        else Turn(
                            Team(Game().cell(self.board.ilog.entry(0)[0]).piece.team)
                        )
                    )
                )
            )
        )

    @turn.setter
    def turn(self, turn: Turn):
        self._next_turn = turn

    def find_playable_cell(
        self,
        cls: type[Piece],
        team: Team,
        rof: Optional[str],
        dest: Query,
        ignorable: Optional[Piece] = None,
    ) -> Cell:
        for cells in self.board:
            for cell in cells:
                if (
                    cell.piece is not None
                    and cell.piece is not ignorable
                    and cell.piece.team is team
                    and isinstance(cell.piece, cls)
                    and (rof is None or rof in cell.name)
                    and self.move(cell.piece, self.cell(dest), False)
                ):
                    return cell

        raise ValueError

    def reset(self) -> None:
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
                data["log"] = self._board.ilog
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

    def parse_json_file(self, filename: str) -> Optional[Game]:
        with open(filename, "r") as f:
            s = f.read()
            data = loads(s)
            version_info = VersionInfo.parse(data["fileVersion"])
            game = Game()
            game._created = datetime.fromisoformat(data["created"])

            match version_info.major:
                case 1:
                    types: List[Type[Piece]] = [
                        Pawn,
                        Rook,
                        Knight,
                        Bishop,
                        Queen,
                        King,
                    ]
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
                    log: PlainNotationLog[List] = PlainNotationLog(data["log"])
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
                                game.promote(PIECE_NAME_TYPE_MAP[b])
                            else:
                                game.move(a, b)
                case _:
                    raise ValueError("Unsupported version")
        return game

    def parse_pgn_move(self, move: str) -> Optional[Tuple[Query, Query, str | None]]:
        if move[0] == "{":
            return None

        team = Team.BLACK if self.turn == Turn.BLACK else Team.WHITE
        move = move.replace("+", "").replace("x", "")

        match move:
            case "O-O":
                return ("E8", "G8", None) if team is Team.BLACK else ("E1", "G1", None)
            case "O-O-O":
                return ("E8", "C8", None) if team is Team.BLACK else ("E1", "C1", None)
            case "0-1" | "1-0" | "1/2-1/2":
                return None

        p: type[Piece] = Pawn
        q1: Query
        q2: Query
        rof: Optional[str] = None
        promo: Optional[str] = None

        if "=" in move:
            promo = move[-1]
            move = move[:-2]

        if move[0].isupper():
            p = PIECE_NAME_TYPE_MAP[move[0]]
            move = move[1:]

        match len(move):
            case 2:
                pass
            case 3:
                rof = move[0].upper()
                move = move[1:]
            case _:
                raise ValueError

        q2 = move.upper()
        q1 = self.find_playable_cell(p, team, rof, q2).name

        return q1, q2, promo

    def load(self, filename: str):
        game = self.parse_json_file(filename)

        if game is not None:
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

    def move(self, q1: Query, q2: Query, can_commit: bool = True) -> bool:
        main_move: Optional[Move] = None
        rook_move: Optional[Move] = None

        def reverse() -> None:
            if main_move is not None:
                main_move.reverse()

            if rook_move is not None:
                rook_move.reverse()

        try:
            cell1, cell2 = self.cell(q1), self.cell(q2)

            if self.board.get_promotable() is not None:
                raise IllegalMoveWhilePromotingError(cell1, cell2)

            piece = cell1.piece

            if piece is None:
                raise IllegalMoveError(None, cell1, cell2)

            turn = Turn(piece.team)

            if self.turn != turn:
                raise IllegalMoveOutOfTurnError(cell1, cell2)

            t = type(piece)

            try:
                twin_cell = (
                    self.find_playable_cell(t, piece.team, None, cell2, piece)
                    if can_commit
                    else None
                )
            except ValueError:
                twin_cell = None

            elog_move: str
            x = cell1.x - cell2.x
            main_move = self.board.move_piece(piece, cell2)
            rook_cell = self.board[cell2.y][0 if x > 0 else 7]
            rook_piece = rook_cell.piece
            piece.is_castling = (
                isinstance(piece, King) and abs(x) == 2 and rook_piece is not None
            )

            if piece.is_castling:
                try:
                    rook_move = self.board.move_piece(
                        rook_piece,
                        cell2.left() if rook_cell.x > cell2.x else cell2.right(),
                    )
                    elog_move = "O-O" if x < 0 else "O-O-O"
                finally:
                    piece.is_castling = False
            else:
                if t is Pawn:
                    elog_move = (
                        ""
                        if main_move.taken_piece is None
                        else f"{cell1.name[0]}x".lower()
                    )

                    # TODO: Append annotation for En passant take.
                else:
                    elog_move = PIECE_TYPE_NAME_MAP[t]

                    if twin_cell is not None:
                        elog_move += (
                            cell1.name[1] if twin_cell.x == cell1.x else cell1.name[0]
                        ).lower()

                    if main_move.taken_piece is not None:
                        elog_move += "x"

                elog_move += cell2.name.lower()

            try:
                if not self.board.get_king(piece.team.opponent).is_safe:
                    elog_move += "+"
            except IndexError:
                pass

            # TODO: Append annotation for Checkmate.

            if can_commit:
                self._last_turn = turn

                if turn == Turn.WHITE:
                    self.board.elog.append((f"{self.board.move_index + 1}.", elog_move))
                else:
                    elog_entry = self.board.elog[-1]

                    if len(elog_entry) == 2:
                        self.board.elog[-1] = (elog_entry[0], elog_entry[1], elog_move)
                    else:
                        self.board.elog.append(
                            (f"{self.board.move_index}...", elog_move)
                        )

                    self.board.move_index += 1

                self.board.ilog.append((cell1.point, cell2.point))
                self.notify("move", main_move)
            else:
                reverse()

            return True
        except:
            reverse()

            if can_commit:
                raise

        return False

    def promote(self, t: Type[Piece]):
        cell = self.board.get_promotable()

        if cell is None:
            raise IllegalMoveError("cannot promote", cell)

        if cell.piece is None or not isinstance(cell.piece, Pawn) or t in (Pawn, King):
            raise IllegalPromotionTypeError(cell, t)

        cell.piece = t(cell.piece.team, has_moved=True)
        piece_name = PIECE_TYPE_NAME_MAP[t]
        elog_entry = self.board.elog[-1]

        def annotate(elog_move: str) -> str:
            """Add promotion notation and move check notation to the end if present."""

            return (
                f"{elog_move[:-1]}={piece_name}+"
                if elog_move[-1] == "+"
                else (
                    f"{elog_move}={piece_name}+"
                    if not self.board.get_king(cell.piece.team.opponent).is_safe
                    else f"{elog_move}={piece_name}"
                )
            )

        self.board.elog[-1] = (
            (elog_entry[0], annotate(elog_entry[1]))
            if len(elog_entry) == 2
            else (elog_entry[0], elog_entry[1], annotate(elog_entry[2]))
        )

        self.board.ilog.append((cell.point, piece_name))
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


class PGNFile(List[PGNGame]):
    def __init__(self, filename: str) -> None:
        self.filename = filename
        realpath = path.realpath(path.join(getcwd(), path.dirname(__file__)))

        super().__init__(pgn_loads(open(path.join(realpath, self.filename)).read()))

    def game(self, index: int = -1) -> Game:
        game = Game()
        level = 0

        for pgn_move in self[index].moves:
            if pgn_move == "(":
                level += 1

                continue

            if pgn_move == ")":
                level -= 1

                continue

            if level > 0:
                continue

            move = game.parse_pgn_move(pgn_move)

            if move is not None:
                q1, q2, promotion = move

                game.move(q1, q2)

                if promotion is not None:
                    game.promote(PIECE_NAME_TYPE_MAP[promotion])

        return game
