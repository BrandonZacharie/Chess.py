"""UI-layer tests for chess.py.

The curses Window and module-level curses helpers (``panel``, ``doupdate``,
``curs_set``) are replaced with mocks so the logic in ``Menu`` and
``Chess._fileprompt`` can be exercised without a terminal.

Tests that target the known bugs identified in the review are marked
``xfail(strict=True)``. When a bug is fixed the test will start passing
and pytest will fail the strict-xfail, forcing us to remove the marker.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, List
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chess as chess_mod
from chess import Chess, Configuration, KeyCode, Menu, check_window_maxyx


def make_window(getch_keys: Iterable[int] = ()) -> MagicMock:
    """Build a MagicMock that quacks like a curses ``Window``.

    ``getmaxyx`` returns a comfortably-large terminal by default, and
    ``subwin`` returns another mock window so ``Menu.__init__`` works.
    ``getch`` is primed with the supplied key sequence; an empty sequence
    raises ``StopIteration`` if exhausted, which fails the test loudly
    rather than hanging.
    """
    window = MagicMock(name="window")
    window.getmaxyx.return_value = (40, 80)

    sub = MagicMock(name="subwin")
    sub.getmaxyx.return_value = (40, 80)
    window.subwin.return_value = sub
    sub.subwin.return_value = sub

    keys = iter(list(getch_keys))
    window.getch.side_effect = lambda: next(keys)
    sub.getch.side_effect = lambda: next(keys)

    return window


@pytest.fixture
def curses_patches():
    """Patch module-level curses helpers used by chess.py."""
    with patch.object(chess_mod, "panel") as panel_mock, patch.object(
        chess_mod, "doupdate"
    ) as doupdate_mock, patch.object(chess_mod, "curs_set") as curs_set_mock:
        panel_mock.new_panel.side_effect = lambda *_a, **_kw: MagicMock(name="panel")
        yield {
            "panel": panel_mock,
            "doupdate": doupdate_mock,
            "curs_set": curs_set_mock,
        }


# ---------------------------------------------------------------------------
# check_window_maxyx
# ---------------------------------------------------------------------------


class TestCheckWindowMaxyx:
    def test_returns_false_when_window_is_large_enough(self):
        window = make_window()
        window.getmaxyx.return_value = (40, 80)

        assert check_window_maxyx(window) is False
        window.getch.assert_not_called()

    def test_returns_true_after_retry_when_window_was_too_small(self):
        window = MagicMock(name="window")
        window.getmaxyx.side_effect = [(10, 10), (40, 80)]
        window.getch.return_value = ord(" ")

        assert check_window_maxyx(window) is True
        assert window.getch.call_count == 1
        # The retry prompt was rendered before the retry.
        assert window.addstr.called

    def test_custom_minimum_size_is_respected(self):
        window = MagicMock(name="window")
        window.getmaxyx.return_value = (10, 10)
        window.getch.side_effect = [ord(" ")]
        window.getmaxyx.side_effect = [(10, 10), (60, 60)]

        assert check_window_maxyx(window, maxyx=(50, 50)) is True


# ---------------------------------------------------------------------------
# Menu.pages / Menu.insert
# ---------------------------------------------------------------------------


class TestMenuPagination:
    def _menu(self, items, curses_patches):
        window = make_window()
        return Menu(list(items), window)

    def test_exit_item_is_appended(self, curses_patches):
        items = [("one", lambda: None), ("two", lambda: None)]
        menu = self._menu(items, curses_patches)

        assert menu.items[-1] == ("exit", None)

    def test_pages_split_items_in_chunks_of_page_size(self, curses_patches):
        items = [(f"i{n}", lambda: None) for n in range(60)]
        menu = self._menu(items, curses_patches)
        # 60 items + the appended "exit" = 61 → 3 pages of 25/25/11.
        assert [len(p) for p in menu.pages] == [25, 25, 11]

    def test_pages_cache_is_invalidated_by_insert(self, curses_patches):
        items = [(f"i{n}", lambda: None) for n in range(3)]
        menu = self._menu(items, curses_patches)
        first = menu.pages
        assert len(first[0]) == 4  # 3 + exit

        menu.insert(0, ("inserted", lambda: None))
        second = menu.pages

        assert second is not first
        assert second[0][0][0] == "inserted"
        assert len(second[0]) == 5

    @pytest.mark.xfail(
        strict=True,
        reason="BUG: Menu.__init__ appends 'exit' to the caller's list, so "
        "passing the same list twice yields two 'exit' entries.",
    )
    def test_shared_items_list_is_not_mutated(self, curses_patches):
        window = make_window()
        items: List = [("one", lambda: None)]
        Menu(items, window)

        assert ("exit", None) not in items


# ---------------------------------------------------------------------------
# Menu.navigate
# ---------------------------------------------------------------------------


def _menu_with(items, curses_patches):
    window = make_window()
    return Menu(list(items), window)


class TestMenuNavigate:
    def test_down_within_page(self, curses_patches):
        menu = _menu_with([(f"i{n}", lambda: None) for n in range(5)], curses_patches)
        menu.navigate(1)
        assert (menu.page, menu.position) == (0, 1)

    def test_up_at_top_stays_at_top(self, curses_patches):
        menu = _menu_with([(f"i{n}", lambda: None) for n in range(5)], curses_patches)
        menu.navigate(-1)
        assert (menu.page, menu.position) == (0, 0)

    def test_down_at_bottom_stays_at_bottom_when_single_page(self, curses_patches):
        items = [(f"i{n}", lambda: None) for n in range(3)]
        menu = _menu_with(items, curses_patches)  # 3 + exit = 4 items, one page
        menu.position = 3
        menu.navigate(1)
        assert menu.page == 0
        assert menu.position == 3

    def test_down_crosses_to_next_page(self, curses_patches):
        items = [(f"i{n}", lambda: None) for n in range(40)]  # +exit → 41
        menu = _menu_with(items, curses_patches)
        menu.position = 24
        menu.navigate(1)
        assert menu.page == 1
        assert 0 <= menu.position < len(menu.pages[menu.page])

    def test_up_crosses_to_previous_page(self, curses_patches):
        items = [(f"i{n}", lambda: None) for n in range(40)]
        menu = _menu_with(items, curses_patches)
        menu.page = 1
        menu.position = 0
        menu.navigate(-1)
        assert menu.page == 0
        assert menu.position == 24

    def test_large_forward_jump_clamps_to_last_page(self, curses_patches):
        items = [(f"i{n}", lambda: None) for n in range(40)]
        menu = _menu_with(items, curses_patches)
        menu.navigate(len(menu.items))
        assert 0 <= menu.page < len(menu.pages)
        assert 0 <= menu.position < len(menu.pages[menu.page])

    @pytest.mark.xfail(
        strict=True,
        reason="BUG: when len(items) is an exact multiple of page_size, "
        "navigate forward off the end sets self.page to len(items)//page_size, "
        "which is out of bounds (should be len(pages)-1).",
    )
    def test_forward_navigation_when_items_align_with_page_size(self, curses_patches):
        # 49 user items + appended exit = 50 = 2 * page_size, so
        # len(pages) == 2 (valid indices 0,1) but the clamp in navigate()
        # is `len(items) // page_size` == 2 — one past the end. To trip
        # it we must navigate forward off the LAST page.
        items = [(f"i{n}", lambda: None) for n in range(49)]
        menu = _menu_with(items, curses_patches)

        menu.page = 1
        menu.position = 24  # last entry of the last page
        menu.navigate(1)  # navigate past the end

        assert menu.page < len(menu.pages), (
            f"page={menu.page} is out of range for {len(menu.pages)} pages"
        )
        # And the next render must not crash on pages[self.page].
        _ = menu.pages[menu.page]


# ---------------------------------------------------------------------------
# Menu.display
# ---------------------------------------------------------------------------


class TestMenuDisplay:
    def test_esc_exits_immediately(self, curses_patches):
        window = make_window(getch_keys=[int(KeyCode.ESC)])
        menu = Menu([("one", lambda: None)], window)

        menu.display()  # should return without raising

    def test_enter_on_exit_item_breaks_the_loop(self, curses_patches):
        # First press DOWN to land on the exit item, then ENTER.
        window = make_window(
            getch_keys=[int(KeyCode.DOWN), int(KeyCode.ENTER)]
        )
        menu = Menu([("one", lambda: None)], window)
        menu.display()

    def test_enter_invokes_selected_callback(self, curses_patches):
        called = []
        window = make_window(
            getch_keys=[int(KeyCode.ENTER), int(KeyCode.ESC)]
        )
        menu = Menu([("one", lambda: called.append(1))], window)

        menu.display()

        assert called == [1]

    def test_keyboard_interrupt_from_callback_exits_cleanly(self, curses_patches):
        def boom():
            raise KeyboardInterrupt

        window = make_window(getch_keys=[int(KeyCode.ENTER)])
        menu = Menu([("boom", boom)], window)

        menu.display()  # KeyboardInterrupt is swallowed

    @pytest.mark.xfail(
        strict=True,
        reason="BUG: panel.hide() lives inside the display loop, so after the "
        "first non-exit keypress the panel is removed from the deck and "
        "subsequent iterations leave it hidden. The hide call should only "
        "happen once, when display() exits.",
    )
    def test_panel_is_not_hidden_between_keypresses(self, curses_patches):
        window = make_window(
            getch_keys=[
                int(KeyCode.DOWN),
                int(KeyCode.DOWN),
                int(KeyCode.UP),
                int(KeyCode.ESC),
            ]
        )
        menu = Menu(
            [("one", lambda: None), ("two", lambda: None), ("three", lambda: None)],
            window,
        )
        menu.display()

        assert menu.panel.hide.call_count <= 1, (
            f"panel.hide() was called {menu.panel.hide.call_count} times; "
            "it should only run once on display() exit."
        )


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


class TestConfiguration:
    def test_default_log_style(self):
        from cli import LogStyle

        cfg = Configuration()
        assert cfg.log_style is LogStyle.CoordinateNotation


# ---------------------------------------------------------------------------
# Chess._fileprompt
# ---------------------------------------------------------------------------


class _BareChess:
    """An almost-Chess used to drive methods that only need ``self.window``.

    The real ``Chess.__init__`` wires up Menu(...) instances and enters the
    root menu loop. For ``_fileprompt`` and ``_load_pgn`` we only need a
    window, so we lift the methods onto a lightweight stand-in.
    """

    _fileprompt = Chess._fileprompt
    _load_pgn = Chess._load_pgn

    def __init__(self, window):
        self.window = window


def _run_fileprompt(keys, handler=None):
    window = make_window(getch_keys=keys)
    bare = _BareChess(window)
    return bare, window, bare._fileprompt(handler=handler)


class TestFilePrompt:
    def test_esc_raises_keyboard_interrupt(self, curses_patches):
        window = make_window(getch_keys=[int(KeyCode.ESC)])
        bare = _BareChess(window)

        with pytest.raises(KeyboardInterrupt):
            bare._fileprompt()

    def test_enter_invokes_handler_with_typed_path(self, curses_patches):
        received: List[str] = []

        def handler(path: str) -> bool:
            received.append(path)
            return True

        keys = [ord("a"), ord("b"), ord("c"), int(KeyCode.ENTER)]
        window = make_window(getch_keys=keys)
        bare = _BareChess(window)

        bare._fileprompt(handler=handler)  # returns on handler success

        assert len(received) == 1
        # The default prompt is the directory of chess.py + path.sep + "abc".
        assert received[0].endswith("abc")

    def test_backspace_removes_character_before_cursor(self, curses_patches):
        received: List[str] = []

        def handler(path: str) -> bool:
            received.append(path)
            return True

        keys = [
            ord("a"),
            ord("b"),
            ord("c"),
            int(KeyCode.BACKSPACE),
            int(KeyCode.ENTER),
        ]
        window = make_window(getch_keys=keys)
        _BareChess(window)._fileprompt(handler=handler)

        assert received[0].endswith("ab")

    def test_handler_returning_false_keeps_loop_open(self, curses_patches):
        calls: List[str] = []

        def handler(path: str) -> bool:
            calls.append(path)
            return False  # signal "try again"

        # Type 'a', press ENTER (handler returns False, loop continues),
        # then press ESC to break.
        keys = [ord("a"), int(KeyCode.ENTER), int(KeyCode.ESC)]
        window = make_window(getch_keys=keys)
        bare = _BareChess(window)

        with pytest.raises(KeyboardInterrupt):
            bare._fileprompt(handler=handler)

        assert len(calls) == 1
        assert calls[0].endswith("a")

    def test_arrow_keys_move_cursor_without_inserting(self, curses_patches):
        received: List[str] = []

        def handler(path: str) -> bool:
            received.append(path)
            return True

        # Type "ab", LEFT, insert 'X' between a and b → "aXb".
        keys = [
            ord("a"),
            ord("b"),
            int(KeyCode.LEFT),
            ord("X"),
            int(KeyCode.ENTER),
        ]
        window = make_window(getch_keys=keys)
        _BareChess(window)._fileprompt(handler=handler)

        assert received[0].endswith("aXb")

    @pytest.mark.xfail(
        strict=True,
        reason="BUG: _fileprompt's default branch accepts any keycode and "
        "calls chr(key), so curses special keys (F1, KEY_RESIZE, etc.) get "
        "inserted as garbage characters or raise ValueError for "
        "out-of-range codepoints.",
    )
    def test_unhandled_special_keys_are_ignored(self, curses_patches):
        from curses import KEY_F1

        received: List[str] = []

        def handler(path: str) -> bool:
            received.append(path)
            return True

        # Pressing F1 should not modify the prompt.
        keys = [ord("a"), KEY_F1, ord("b"), int(KeyCode.ENTER)]
        window = make_window(getch_keys=keys)
        _BareChess(window)._fileprompt(handler=handler)

        assert received[0].endswith("ab"), (
            f"unhandled special key leaked into the path: {received[0]!r}"
        )


# ---------------------------------------------------------------------------
# Chess.__init__ end-to-end
# ---------------------------------------------------------------------------


@pytest.fixture
def chess_instance(curses_patches):
    """A fully-constructed Chess whose root menu was dismissed via ESC.

    ``cli.main`` is patched out for the lifetime of the test so
    ``Chess.play`` doesn't try to drive the (mocked) game loop.
    """
    window = make_window(getch_keys=[int(KeyCode.ESC)])
    with patch.object(chess_mod, "main") as main_mock:
        instance = Chess(window)
        instance._main_mock = main_mock  # exposed for assertions
        yield instance


class TestChessInit:
    def test_root_menu_has_the_expected_entries(self, chess_instance):
        labels = [item[0] for item in chess_instance.menus.root.items]
        # Order matters: insertions in ``play`` rely on it.
        assert labels == [
            "new game",
            "load file",
            "options",
            "about",
            "exit",
        ]

    def test_sub_menus_are_constructed(self, chess_instance):
        assert chess_instance.menus.load is not None
        assert chess_instance.menus.save is not None
        assert chess_instance.menus.cfg is not None
        # Sub-menus also receive an appended "exit".
        for menu in (
            chess_instance.menus.load,
            chess_instance.menus.save,
            chess_instance.menus.cfg,
        ):
            assert menu.items[-1] == ("exit", None)

    def test_no_game_is_active_after_construction(self, chess_instance):
        assert chess_instance.game is None

    def test_main_is_not_called_when_user_exits_root_menu(self, chess_instance):
        chess_instance._main_mock.assert_not_called()


# ---------------------------------------------------------------------------
# Chess.play
# ---------------------------------------------------------------------------


class TestChessPlay:
    def test_first_play_inserts_continue_and_save_entries(self, chess_instance):
        chess_instance.play()

        labels = [item[0] for item in chess_instance.menus.root.items]
        assert labels[0] == "continue…"
        assert "save file" in labels
        # "save file" should land at index 2 (after continue + new game).
        assert labels.index("save file") == 2

    def test_second_play_does_not_duplicate_entries(self, chess_instance):
        chess_instance.play()
        first_labels = [item[0] for item in chess_instance.menus.root.items]

        chess_instance.play()
        second_labels = [item[0] for item in chess_instance.menus.root.items]

        assert second_labels == first_labels
        assert second_labels.count("continue…") == 1
        assert second_labels.count("save file") == 1

    def test_play_invokes_main_with_game_and_log_style(self, chess_instance):
        chess_instance.play()

        chess_instance._main_mock.assert_called_once()
        args, _ = chess_instance._main_mock.call_args
        assert args[0] is chess_instance.window
        assert args[1] is chess_instance.game
        assert args[2] == chess_instance.cfg.log_style

    def test_play_resets_root_menu_position(self, chess_instance):
        chess_instance.menus.root.position = 3
        chess_instance.play()
        assert chess_instance.menus.root.position == 0


# ---------------------------------------------------------------------------
# Chess._load_pgn against real fixtures
# ---------------------------------------------------------------------------


PGN_DIR = Path(__file__).resolve().parent


class TestLoadPgn:
    @pytest.fixture
    def bare(self, curses_patches):
        return _BareChess(make_window(getch_keys=[int(KeyCode.ESC)]))

    def test_missing_file_returns_false_and_reports_the_error(self, bare):
        ok = bare._load_pgn("does-not-exist.pgn")
        assert ok is False
        # An error message must have been drawn somewhere on the window.
        # addstr is called as addstr(y, x, message[, attr]); pull only the
        # string positional args out of the call list.
        rendered = " ".join(
            arg
            for call in bare.window.addstr.call_args_list
            for arg in call.args
            if isinstance(arg, str)
        ).lower()
        assert "not found" in rendered or "error" in rendered

    def test_loads_simple_pgn_and_renders_a_menu(self, bare, curses_patches):
        # The PGNFile loader joins with ``game/`` so we pass an absolute path
        # to side-step that resolution.
        ok = bare._load_pgn(str(PGN_DIR / "test1.pgn"))

        # The constructed sub-menu exits immediately on the queued ESC, so
        # _load_pgn returns True for a successful load.
        assert ok is True

    def test_loads_pgn_with_partial_dates(self, bare, curses_patches):
        # test2.pgn uses "1886.??.??" — exercises the ``.replace('.??', '')``
        # / ``fuzzy=True`` branch in the menu-label formatter.
        ok = bare._load_pgn(str(PGN_DIR / "test2.pgn"))
        assert ok is True
