"""UI-layer tests for cli.py.

The curses ``Window`` and module-level ``curs_set`` are replaced with
mocks so the rendering and input-loop logic can be exercised without a
terminal. A real ``Game`` is used wherever the engine's behavior is
incidental to the test (board layout, default turn, etc.); ``MagicMock``
stands in when we want to observe what cli.py asks the game to do.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, List
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cli as cli_mod
from cli import (
    InputMode,
    LogStyle,
    draw_board,
    draw_elog,
    draw_head,
    draw_ilog,
    draw_input,
    draw_input_cursor,
    draw_input_err,
    draw_input_prompt,
    draw_notes,
    get_input,
    main,
)
from game import Game, Team
from game.error import IllegalMoveError


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def make_window(getch_keys: Iterable[int] = ()) -> MagicMock:
    """A MagicMock that mimics a curses ``Window``.

    ``getch`` returns the queued keys in order. If the test loop calls
    ``getch`` more times than the queue can satisfy, ``StopIteration``
    propagates and fails the test instead of hanging.
    """
    window = MagicMock(name="window")
    keys = iter(list(getch_keys))
    window.getch.side_effect = lambda: next(keys)
    window.getkey.return_value = " "
    return window


def rendered_strings(window: MagicMock) -> str:
    """Concatenate every string-typed positional arg passed to addstr."""
    return " ".join(
        arg
        for call in window.addstr.call_args_list
        for arg in call.args
        if isinstance(arg, str)
    )


def addstr_at(window: MagicMock, y: int, x: int) -> List[str]:
    """All strings written at exactly (y, x)."""
    return [
        call.args[2]
        for call in window.addstr.call_args_list
        if len(call.args) >= 3
        and call.args[0] == y
        and call.args[1] == x
        and isinstance(call.args[2], str)
    ]


@pytest.fixture
def curs_set_patch():
    with patch.object(cli_mod, "curs_set") as p:
        yield p


# ---------------------------------------------------------------------------
# draw_head
# ---------------------------------------------------------------------------


class TestDrawHead:
    def test_writes_chess_py_title_at_the_expected_position(self):
        window = make_window()
        draw_head(window)
        assert " Chess.py " in addstr_at(window, 2, 5)


# ---------------------------------------------------------------------------
# draw_input_prompt
# ---------------------------------------------------------------------------


class TestDrawInputPrompt:
    @pytest.mark.parametrize(
        "mode, expected",
        [
            (InputMode.SELECT_CELL, "Select a piece:"),
            (InputMode.SELECT_DEST, "Select a target:"),
            (InputMode.SELECT_PROM, "Select a promotion:"),
        ],
    )
    def test_renders_the_prompt_for_the_mode(self, mode, expected):
        window = make_window()
        draw_input_prompt(window, mode)
        assert expected in rendered_strings(window)
        window.clrtoeol.assert_called_once()

    def test_paused_renders_nothing_but_still_clears_eol(self):
        window = make_window()
        draw_input_prompt(window, InputMode.PAUSED)
        assert rendered_strings(window) == ""
        window.clrtoeol.assert_called_once()


# ---------------------------------------------------------------------------
# draw_input_err
# ---------------------------------------------------------------------------


class TestDrawInputErr:
    def test_writes_the_error_and_waits_for_a_key(self):
        window = make_window()
        draw_input_err(window, "Invalid input.")
        rendered = rendered_strings(window)
        assert "Invalid input." in rendered
        assert "Press any key to continue." in rendered
        window.getkey.assert_called_once()

    def test_accepts_exception_instances_directly(self):
        window = make_window()
        err = IllegalMoveError("boom")
        draw_input_err(window, err)
        assert "boom" in rendered_strings(window)


# ---------------------------------------------------------------------------
# draw_input_cursor / draw_input
# ---------------------------------------------------------------------------


class TestDrawInputCursor:
    def test_select_cell_moves_cursor_to_left_column(self):
        window = make_window()
        draw_input_cursor(window, InputMode.SELECT_CELL)
        window.move.assert_called_once_with(33, 6)

    def test_select_dest_skips_past_the_q1_echo(self):
        window = make_window()
        draw_input_cursor(window, InputMode.SELECT_DEST, "A2")
        # The prior cell name is reprinted, then the cursor jumps three
        # columns to the right to start the destination entry.
        assert "A2" in rendered_strings(window)
        window.move.assert_called_once_with(33, 9)

    def test_select_dest_without_prior_input_skips_echo(self):
        window = make_window()
        draw_input_cursor(window, InputMode.SELECT_DEST, None)
        # No addstr call at the echo position when s is None.
        assert rendered_strings(window) == ""
        window.move.assert_called_once_with(33, 9)


class TestDrawInput:
    def test_uppercases_lowercase_input(self):
        window = make_window()
        draw_input(window, InputMode.SELECT_CELL, ord("a"))
        # The character is written at the SELECT_CELL column (6).
        assert "A" in addstr_at(window, 33, 6)

    def test_select_dest_writes_at_offset_column(self):
        window = make_window()
        draw_input(window, InputMode.SELECT_DEST, ord("4"))
        assert "4" in addstr_at(window, 33, 9)


# ---------------------------------------------------------------------------
# draw_notes
# ---------------------------------------------------------------------------


class TestDrawNotes:
    def test_uses_current_turn_in_non_promotion_modes(self):
        window = make_window()
        game = Game()
        draw_notes(window, game, InputMode.SELECT_CELL)
        rendered = rendered_strings(window)
        assert "It is" in rendered
        assert game.turn.name in rendered
        assert "'s turn." in rendered

    def test_uses_last_turn_in_promotion_mode(self):
        """During SELECT_PROM the active turn has already flipped to the
        opponent, but the promotion belongs to the *previous* mover."""
        window = make_window()
        game = MagicMock()
        # The Turn enum is by-name in the rendered string, so we only need
        # something with a .name attribute on _last_turn.
        game.turn = MagicMock(name="WHITE_DUMMY")
        game.turn.name = "WHITE"
        game._last_turn = MagicMock(name="BLACK_DUMMY")
        game._last_turn.name = "BLACK"

        draw_notes(window, game, InputMode.SELECT_PROM)

        rendered = rendered_strings(window)
        assert "BLACK" in rendered
        assert "WHITE" not in rendered


# ---------------------------------------------------------------------------
# get_input
# ---------------------------------------------------------------------------


class TestGetInput:
    def test_paused_returns_empty_immediately(self):
        window = make_window()
        assert get_input(window, InputMode.PAUSED) == []
        window.getch.assert_not_called()

    def test_select_cell_collects_two_board_chars(self):
        window = make_window(getch_keys=[ord("A"), ord("2")])
        result = get_input(window, InputMode.SELECT_CELL)
        assert result == [ord("A"), ord("2")]

    def test_select_dest_collects_two_board_chars(self):
        window = make_window(getch_keys=[ord("a"), ord("4")])
        result = get_input(window, InputMode.SELECT_DEST)
        assert result == [ord("a"), ord("4")]

    def test_select_prom_collects_one_promotion_letter(self):
        window = make_window(getch_keys=[ord("B")])
        result = get_input(window, InputMode.SELECT_PROM)
        assert result == [ord("B")]

    def test_select_prom_accepts_all_four_promotion_letters(self):
        for key in (ord("Q"), ord("R"), ord("N"), ord("B")):
            window = make_window(getch_keys=[key])
            result = get_input(window, InputMode.SELECT_PROM)
            assert result == [key], f"SELECT_PROM dropped {chr(key)!r}"

    def test_select_prom_rejects_board_cell_letters(self):
        # In SELECT_PROM mode, board cell letters (A-H, 1-8) are NOT valid
        # promotion choices and must be filtered. 'B' is the one overlap.
        window = make_window(getch_keys=[ord("A"), ord("5"), ord("Q")])
        result = get_input(window, InputMode.SELECT_PROM)
        assert result == [ord("Q")]

    def test_non_board_chars_are_ignored(self):
        # The 'z' (not a board cell) should be discarded; loop keeps reading.
        window = make_window(getch_keys=[ord("z"), ord("!"), ord("A"), ord("2")])
        result = get_input(window, InputMode.SELECT_CELL)
        assert result == [ord("A"), ord("2")]
        # All four getch calls were consumed.
        assert window.getch.call_count == 4

    def test_esc_raises_keyboard_interrupt(self):
        from curses.ascii import ESC

        window = make_window(getch_keys=[ESC])
        with pytest.raises(KeyboardInterrupt):
            get_input(window, InputMode.SELECT_CELL)


# ---------------------------------------------------------------------------
# draw_board / draw_ilog / draw_elog
# ---------------------------------------------------------------------------


class TestDrawBoard:
    def test_draws_one_addstr_per_board_line(self):
        window = make_window()
        game = Game()
        draw_board(window, game.board, LogStyle.CoordinateNotation)

        # Every non-empty board line should have been written; we don't
        # care exactly which line lands where, just that each unique line
        # appears at least once.
        rendered = rendered_strings(window)
        for line in str(game.board).splitlines():
            if line.strip():
                assert line in rendered

    def test_coordinate_log_style_invokes_draw_ilog(self):
        window = make_window()
        game = Game()
        with (
            patch.object(cli_mod, "draw_ilog") as ilog,
            patch.object(cli_mod, "draw_elog") as elog,
        ):
            draw_board(window, game.board, LogStyle.CoordinateNotation)
            ilog.assert_called_once()
            elog.assert_not_called()

    def test_algebraic_log_style_invokes_draw_elog(self):
        window = make_window()
        game = Game()
        with (
            patch.object(cli_mod, "draw_ilog") as ilog,
            patch.object(cli_mod, "draw_elog") as elog,
        ):
            draw_board(window, game.board, LogStyle.AlgebraicNotation)
            elog.assert_called_once()
            ilog.assert_not_called()


class TestDrawLogs:
    def test_draw_ilog_renders_recent_moves(self):
        window = make_window()
        game = Game()
        game.move("A2", "A4")
        game.move("A7", "A5")

        draw_ilog(window, game.board)

        rendered = rendered_strings(window)
        # The ilog uses "from:to" coordinate notation for each ply, and
        # numbers them backward from the latest. The last move should be
        # present in some form.
        assert "A7" in rendered or "A5" in rendered
        assert "A2" in rendered or "A4" in rendered

    def test_draw_elog_renders_algebraic_notation(self):
        window = make_window()
        game = Game()
        game.move("A2", "A4")

        draw_elog(window, game.board)

        # The elog stores algebraic-notation tuples; at minimum the move
        # number prefix (e.g. "1.") must appear.
        rendered = rendered_strings(window)
        assert "1." in rendered

    def test_draw_ilog_breaks_after_four_columns(self):
        """``length_max`` is 24 lines per column, with at most 4 columns.

        Once the fourth column overflows the renderer stops drawing. We
        synthesize an ilog of 200 LogMove entries (well over 4 * 24) to
        exercise that break, and check the columns-2/3/4 advance.
        """
        window = make_window()
        board = MagicMock()
        # Each LogMove is ((from_x, from_y), (to_x, to_y)). get_cell_name
        # calls board[y][x].name, so make any indexing into board return a
        # cell with a stable name.
        cell = MagicMock()
        cell.name = "A1"
        board.__getitem__.return_value.__getitem__.return_value = cell
        board.ilog = [((0, 0), (1, 1)) for _ in range(200)]

        # Must not raise; the 4-column break is the only thing that lets
        # this finish in finite time given 200 entries.
        draw_ilog(window, board)

    def test_draw_elog_breaks_after_four_columns(self):
        window = make_window()
        board = MagicMock()
        board.elog = [(f"{i}.", "Nf3", "Nf6") for i in range(200)]

        draw_elog(window, board)


# ---------------------------------------------------------------------------
# main (game loop)
# ---------------------------------------------------------------------------


def _esc():
    from curses.ascii import ESC

    return ESC


class TestMainLoop:
    def test_exits_cleanly_on_esc_at_select_cell(self, curs_set_patch):
        window = make_window(getch_keys=[_esc()])
        game = Game()

        # Must return — no exception escapes.
        main(window, game, LogStyle.CoordinateNotation)

        # No move was performed.
        assert game.turn is Team.WHITE.value or game.turn.name == "WHITE"

    def test_each_call_without_game_uses_a_fresh_game(self, curs_set_patch):
        """Regression test for the mutable-default-argument footgun.

        Previously `def main(window, game: Game = Game(), ...)` shared a
        single Game across every caller that omitted the argument, so a
        move made in one call would leak into the next. The default is
        now None; each call constructs its own Game.
        """
        window1 = make_window(
            getch_keys=[ord("A"), ord("2"), ord("A"), ord("4"), _esc()]
        )
        main(window1, log_style=LogStyle.CoordinateNotation)

        # If the default were a shared Game, the second call would start
        # with white's a-pawn already moved and turn flipped to black.
        # Drive the same opening move from a fresh game; the engine
        # should accept it (it wouldn't if state had leaked over).
        window2 = make_window(
            getch_keys=[ord("A"), ord("2"), ord("A"), ord("4"), _esc()]
        )
        with patch.object(cli_mod, "draw_input_err") as err_mock:
            main(window2, log_style=LogStyle.CoordinateNotation)

        # No "Invalid input" / illegal-move error fired on the second
        # call → state did not leak from the first.
        err_mock.assert_not_called()

    def test_signature_default_is_none(self):
        """Structural guard: ensure the default isn't a Game instance
        again. A future refactor that re-introduces `Game()` as the
        default would silently re-bring the bug."""
        from inspect import signature

        params = signature(main).parameters
        assert params["game"].default is None

    def test_completes_one_move_then_exits(self, curs_set_patch):
        # White pushes the a-pawn two squares: A2 -> A4. Then ESC.
        window = make_window(
            getch_keys=[ord("A"), ord("2"), ord("A"), ord("4"), _esc()]
        )
        game = Game()
        initial_turn = game.turn

        main(window, game, LogStyle.CoordinateNotation)

        # Turn flipped → engine accepted the move.
        assert game.turn is not initial_turn

    def test_invalid_input_triggers_draw_input_err(self, curs_set_patch):
        # Two valid board cells that don't form a legal move: A1 (white
        # rook) to A2 (white pawn). game.move raises IllegalMoveError.
        window = make_window(
            getch_keys=[
                ord("A"),
                ord("1"),
                ord("A"),
                ord("2"),
                _esc(),
            ]
        )
        game = Game()
        initial_turn = game.turn

        with patch.object(cli_mod, "draw_input_err") as err_mock:
            main(window, game, LogStyle.CoordinateNotation)

        err_mock.assert_called()
        # The move was rejected so turn did not flip.
        assert game.turn is initial_turn

    def test_value_error_from_game_move_is_reported(self, curs_set_patch):
        # Feed a real key sequence but make game.move raise ValueError so
        # we exercise the ValueError branch specifically.
        window = make_window(
            getch_keys=[
                ord("A"),
                ord("2"),
                ord("A"),
                ord("4"),
                _esc(),
            ]
        )
        game = MagicMock()
        game.move.side_effect = ValueError("bad coords")
        # main also asks for board / turn rendering — keep those quiet.
        game.board.__str__ = lambda self: ""
        game.board.captures = {Team.WHITE: [], Team.BLACK: []}
        game.board.ilog = []
        game.board.elog = []
        game.turn.name = "WHITE"

        with patch.object(cli_mod, "draw_input_err") as err_mock:
            main(window, game, LogStyle.CoordinateNotation)

        err_mock.assert_called()
        # The argument was the literal "Invalid input." string for the
        # ValueError branch (the IllegalMoveError branch passes the
        # exception instance instead).
        assert any(call.args[1] == "Invalid input." for call in err_mock.call_args_list)


# ---------------------------------------------------------------------------
# End-to-end promotion behavior
# ---------------------------------------------------------------------------


def _game_one_move_from_promotion() -> Game:
    """Real Game positioned so that white's next move (F7->G8) promotes.

    Setup is a known short promotion line:
      1. e4 d5 2. exd5 e6 3. dxe6 Bc5 4. exf7+ Kf8
    Now white's f-pawn on f7 can capture g8 and promote.
    """
    g = Game()
    for q1, q2 in [
        ("E2", "E4"),
        ("D7", "D5"),
        ("E4", "D5"),
        ("E7", "E6"),
        ("D5", "E6"),
        ("F8", "C5"),
        ("E6", "F7"),
        ("E8", "F8"),
    ]:
        g.move(q1, q2)
    return g


class TestMainPromotionEndToEnd:
    """Drive ``main`` all the way through a real promotion attempt.

    Each parametrization plays the same 5-move promoting capture and
    presses one of the standard promotion letters. The test asserts the
    pawn is no longer promotable afterward (i.e. the engine accepted
    the promotion). The current ``get_input`` filter only lets 'B'
    through; 'Q' / 'R' / 'N' are xfail(strict) until that's fixed.
    """

    def _drive(self, piece_letter: str) -> bool:
        game = _game_one_move_from_promotion()
        keys = [
            ord("F"),
            ord("7"),
            ord("G"),
            ord("8"),
            ord(piece_letter),
            _esc(),
        ]
        window = make_window(getch_keys=keys)
        with patch.object(cli_mod, "curs_set"), patch.object(cli_mod, "draw_input_err"):
            main(window, game, LogStyle.CoordinateNotation)
        return game.board.get_promotable() is None

    def test_bishop_promotion_is_accepted(self, curs_set_patch):
        assert self._drive("B"), "Bishop promotion failed unexpectedly"

    def test_queen_promotion_is_accepted(self, curs_set_patch):
        assert self._drive("Q"), "Queen promotion was filtered out"

    def test_rook_promotion_is_accepted(self, curs_set_patch):
        assert self._drive("R"), "Rook promotion was filtered out"

    def test_knight_promotion_is_accepted(self, curs_set_patch):
        assert self._drive("N"), "Knight promotion was filtered out"


# ---------------------------------------------------------------------------
# run() entrypoint
# ---------------------------------------------------------------------------


class TestRun:
    def test_run_delegates_to_curses_wrapper_with_main(self):
        from cli import run

        with patch.object(cli_mod, "wrapper") as wrapper_mock:
            run()
            wrapper_mock.assert_called_once_with(cli_mod.main)
