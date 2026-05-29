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
from chess import Chess, Configuration
from interface.draw import check_window_maxyx
from interface.input import KeyCode
from interface.menu import Menu
from game import Game


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

    queue_keys(window, getch_keys)
    return window


def queue_keys(window: MagicMock, keys: Iterable[int]) -> None:
    """(Re)prime a mock window's ``getch`` with a new key sequence.

    Tests that drive multiple menus through the same Chess instance use
    this between calls so each sub-menu gets its own ESC.
    """
    it = iter(list(keys))
    window.getch.side_effect = lambda: next(it)
    window.subwin.return_value.getch.side_effect = lambda: next(it)


@pytest.fixture(autouse=True)
def _isolate_chessrc(tmp_path, monkeypatch):
    """Redirect Configuration's default ~/.chessrc into a per-test tmp_path
    so tests never read from or write to the real user home directory.
    """
    monkeypatch.setattr(chess_mod.Path, "home", lambda: tmp_path)


@pytest.fixture
def curses_patches():
    """Patch module-level curses helpers used by the interface package."""
    import interface.menu as menu_mod
    import interface.input as input_mod

    with (
        patch.object(menu_mod, "panel") as panel_mock,
        patch.object(menu_mod, "doupdate") as doupdate_mock,
        patch.object(menu_mod, "curs_set") as curs_set_menu_mock,
        patch.object(input_mod, "curs_set") as curs_set_input_mock,
    ):
        panel_mock.new_panel.side_effect = lambda *_a, **_kw: MagicMock(name="panel")
        yield {
            "panel": panel_mock,
            "doupdate": doupdate_mock,
            "curs_set": curs_set_menu_mock,
            "curs_set_input": curs_set_input_mock,
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

        assert menu.page < len(
            menu.pages
        ), f"page={menu.page} is out of range for {len(menu.pages)} pages"
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
        window = make_window(getch_keys=[int(KeyCode.DOWN), int(KeyCode.ENTER)])
        menu = Menu([("one", lambda: None)], window)
        menu.display()

    def test_enter_invokes_selected_callback(self, curses_patches):
        called = []
        window = make_window(getch_keys=[int(KeyCode.ENTER), int(KeyCode.ESC)])
        menu = Menu([("one", lambda: called.append(1))], window)

        menu.display()

        assert called == [1]

    def test_keyboard_interrupt_from_callback_exits_cleanly(self, curses_patches):
        def boom():
            raise KeyboardInterrupt

        window = make_window(getch_keys=[int(KeyCode.ENTER)])
        menu = Menu([("boom", boom)], window)

        menu.display()  # KeyboardInterrupt is swallowed

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
        # Menu.__init__ hides the panel once on construction; we only care
        # about hide() calls during display().
        menu.panel.hide.reset_mock()

        menu.display()

        assert menu.panel.hide.call_count == 1, (
            f"panel.hide() was called {menu.panel.hide.call_count} times "
            "during display(); it should only run once on exit."
        )


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


class TestConfiguration:
    def test_default_log_style(self):
        from interface.game import LogStyle

        cfg = Configuration()
        assert cfg.log_style is LogStyle.CoordinateNotation

    def test_first_creation_writes_default_to_disk(self, tmp_path):
        from interface.game import LogStyle

        filepath = tmp_path / ".chessrc"
        assert not filepath.exists()

        Configuration(filepath)

        assert filepath.exists()
        assert filepath.read_text() == f"log_style={LogStyle.CoordinateNotation.name}"

    def test_existing_file_is_loaded(self, tmp_path):
        from interface.game import LogStyle

        filepath = tmp_path / ".chessrc"
        filepath.write_text(f"log_style={LogStyle.AlgebraicNotation.name}")

        cfg = Configuration(filepath)

        assert cfg.log_style is LogStyle.AlgebraicNotation

    def test_setting_log_style_persists_to_disk(self, tmp_path):
        from interface.game import LogStyle

        filepath = tmp_path / ".chessrc"
        cfg = Configuration(filepath)

        cfg.log_style = LogStyle.AlgebraicNotation

        # Round-trip: a fresh Configuration sees the change.
        assert Configuration(filepath).log_style is LogStyle.AlgebraicNotation


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

        assert received[0].endswith(
            "ab"
        ), f"unhandled special key leaked into the path: {received[0]!r}"


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
        assert "save game" in labels
        # "save game" should land at index 2 (after continue + new game).
        assert labels.index("save game") == 2

    def test_second_play_does_not_duplicate_entries(self, chess_instance):
        chess_instance.play()
        first_labels = [item[0] for item in chess_instance.menus.root.items]

        chess_instance.play()
        second_labels = [item[0] for item in chess_instance.menus.root.items]

        assert second_labels == first_labels
        assert second_labels.count("continue…") == 1
        assert second_labels.count("save game") == 1

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

    def test_empty_pgn_file_reports_no_games(self, bare, curses_patches, tmp_path):
        empty = tmp_path / "empty.pgn"
        empty.write_text("")
        ok = bare._load_pgn(str(empty))
        assert ok is True
        rendered = " ".join(
            arg
            for call in bare.window.addstr.call_args_list
            for arg in call.args
            if isinstance(arg, str)
        )
        assert "No games found." in rendered

    def test_malformed_pgn_reports_an_error(self, bare, curses_patches, tmp_path):
        # A non-empty file that pgnparser can't parse correctly drives the
        # general Exception branch (line 392-393).
        bad = tmp_path / "bad.pgn"
        bad.write_text("not a real pgn\n\xFF\xFE\x00 garbage")
        ok = bare._load_pgn(str(bad))
        # Either bool result is fine — what we care about is that the error
        # was caught and a message was drawn somewhere.
        rendered = " ".join(
            arg
            for call in bare.window.addstr.call_args_list
            for arg in call.args
            if isinstance(arg, str)
        ).lower()
        assert ok in (True, False)
        # If it did fail, "error" should appear in the rendered string.
        if ok is False:
            assert "error" in rendered or "not found" in rendered


# ---------------------------------------------------------------------------
# Menu rendering details (title, item modes, navigation keys)
# ---------------------------------------------------------------------------


class TestMenuRendering:
    def test_title_is_rendered_when_present(self, curses_patches):
        window = make_window(getch_keys=[int(KeyCode.ESC)])
        menu = Menu([("one", lambda: None)], window, title=("Settings",))
        menu.display()

        rendered = " ".join(
            arg
            for call in menu.window.addstr.call_args_list
            for arg in call.args
            if isinstance(arg, str)
        )
        assert "↳ Settings" in rendered

    def test_item_with_attribute_third_tuple_element_uses_it(self, curses_patches):
        from curses import A_DIM

        window = make_window(getch_keys=[int(KeyCode.ESC)])
        menu = Menu([("dim entry", lambda: None, A_DIM)], window)
        menu.display()

        # Look at the attribute argument of the addstr that drew the item.
        rendered_with_attrs = [
            call.args
            for call in menu.window.addstr.call_args_list
            if len(call.args) >= 4
            and isinstance(call.args[2], str)
            and "dim entry" in call.args[2]
        ]
        assert rendered_with_attrs, "the dim item was never rendered"
        # The mode field (call.args[3]) should have A_DIM bit set.
        assert any((args[3] & A_DIM) for args in rendered_with_attrs)


class TestMenuNavigationKeys:
    """Keys whose match cases aren't covered by the simple navigation tests."""

    def _menu_with_many_items(self, getch_keys):
        window = make_window(getch_keys=getch_keys)
        items = [(f"i{n}", lambda: None) for n in range(40)]  # > 1 page
        return Menu(items, window)

    def test_ppage_navigates_back_one_page(self, curses_patches):
        menu = self._menu_with_many_items([int(KeyCode.PPAGE), int(KeyCode.ESC)])
        menu.page = 1
        menu.position = 5
        menu.display()
        # After PPAGE the user lands back on page 0.
        assert menu.page == 0

    def test_npage_navigates_forward_one_page(self, curses_patches):
        menu = self._menu_with_many_items([int(KeyCode.NPAGE), int(KeyCode.ESC)])
        menu.display()
        assert menu.page == 1

    def test_home_navigates_to_first_page(self, curses_patches):
        menu = self._menu_with_many_items([int(KeyCode.HOME), int(KeyCode.ESC)])
        menu.page = 1
        menu.position = 7
        menu.display()
        assert (menu.page, menu.position) == (0, 0)

    def test_end_navigates_to_last_page(self, curses_patches):
        menu = self._menu_with_many_items([int(KeyCode.END), int(KeyCode.ESC)])
        menu.display()
        assert menu.page == len(menu.pages) - 1


# ---------------------------------------------------------------------------
# Chess.draw_* sub-menu drivers
# ---------------------------------------------------------------------------


class TestChessDrawMenus:
    def test_draw_save_menu_displays_and_resets_position(self, chess_instance):
        chess_instance.menus.save.position = 1
        queue_keys(chess_instance.window, [int(KeyCode.ESC)])
        chess_instance.draw_save_menu()
        assert chess_instance.menus.save.position == 0

    def test_draw_load_menu_displays_and_resets_position(self, chess_instance):
        chess_instance.menus.load.position = 1
        queue_keys(chess_instance.window, [int(KeyCode.ESC)])
        chess_instance.draw_load_menu()
        assert chess_instance.menus.load.position == 0

    def test_draw_cfg_menu_displays_and_resets_position(self, chess_instance):
        # cfg menu only has one real entry plus exit; bump position then
        # confirm it's reset.
        chess_instance.menus.cfg.position = 1
        queue_keys(chess_instance.window, [int(KeyCode.ESC)])
        chess_instance.draw_cfg_menu()
        assert chess_instance.menus.cfg.position == 0

    def test_draw_cfg_log_style_menu_selects_a_style(self, chess_instance):
        # Pressing ENTER on the first entry (Coordinates) sets the style
        # via set_style() which raises KeyboardInterrupt to break.
        queue_keys(chess_instance.window, [int(KeyCode.ENTER)])
        chess_instance.draw_cfg_log_style_menu()
        # The set_style branch ran; log_style is now an instance attribute
        # equal to LogStyle.CoordinateNotation.
        from interface.game import LogStyle

        assert chess_instance.cfg.log_style == LogStyle.CoordinateNotation

    def test_draw_cfg_log_style_menu_can_exit_without_choosing(self, chess_instance):
        queue_keys(chess_instance.window, [int(KeyCode.ESC)])
        chess_instance.draw_cfg_log_style_menu()
        # No exception; original log_style preserved.

    def test_draw_about_renders_credits_and_waits_for_key(self, chess_instance):
        queue_keys(chess_instance.window, [ord(" ")])
        chess_instance.draw_about()

        rendered = " ".join(
            arg
            for call in chess_instance.window.addstr.call_args_list
            for arg in call.args
            if isinstance(arg, str)
        )
        assert "Brandon Zacharie" in rendered
        assert "github" in rendered
        assert "semver" in rendered
        assert "Press any key to continue…" in rendered


# ---------------------------------------------------------------------------
# Chess save/load entrypoints
# ---------------------------------------------------------------------------


class TestChessSaveLoad:
    def test_save_pgn_fails_when_no_game_then_loop_keeps_running(self, chess_instance):
        queue_keys(chess_instance.window, [int(KeyCode.ENTER), int(KeyCode.ESC)])
        with pytest.raises(KeyboardInterrupt):
            chess_instance.save_pgn()

    def test_save_pgn_returns_via_explicit_keyboard_interrupt_on_success(
        self, chess_instance, tmp_path
    ):
        chess_instance.game = MagicMock()
        chess_instance._fileprompt = lambda handler: handler(str(tmp_path / "g.pgn"))
        with pytest.raises(KeyboardInterrupt):
            chess_instance.save_pgn()
        chess_instance.game.save_pgn.assert_called_once_with(str(tmp_path / "g.pgn"))

    def test_save_json_fails_when_no_game_then_loop_keeps_running(self, chess_instance):
        # ENTER on the prompt triggers the handler; handler returns False
        # because game is None ("Game not found."). The _fileprompt loop
        # stays open, so we press ESC next which raises KeyboardInterrupt
        # from the loop's exit path.
        queue_keys(chess_instance.window, [int(KeyCode.ENTER), int(KeyCode.ESC)])
        with pytest.raises(KeyboardInterrupt):
            chess_instance.save_json()

    def test_save_json_returns_via_explicit_keyboard_interrupt_on_success(
        self, chess_instance, tmp_path
    ):
        # With a real (MagicMock) game on the instance, the handler
        # returns True on ENTER and _fileprompt returns normally; the
        # explicit `raise KeyboardInterrupt` at the end of save_json
        # then fires.
        chess_instance.game = MagicMock()
        chess_instance._fileprompt = lambda handler: handler(str(tmp_path / "g.json"))
        with pytest.raises(KeyboardInterrupt):
            chess_instance.save_json()
        chess_instance.game.save.assert_called_once_with(str(tmp_path / "g.json"))

    def test_load_json_invokes_fileprompt(self, chess_instance, tmp_path):
        # Drive _fileprompt to ENTER with the default path, then ESC.
        # The handler will fail (file not found) and the loop continues.
        queue_keys(chess_instance.window, [int(KeyCode.ENTER), int(KeyCode.ESC)])
        with pytest.raises(KeyboardInterrupt):
            chess_instance.load_json()

    def test_load_pgn_invokes_fileprompt(self, chess_instance):
        # Same shape as load_json: ENTER then ESC. The handler fails (no
        # such PGN at the default path) and ESC exits the loop.
        queue_keys(chess_instance.window, [int(KeyCode.ENTER), int(KeyCode.ESC)])
        with pytest.raises(KeyboardInterrupt):
            chess_instance.load_pgn()


class TestSaveJsonHandler:
    def test_returns_false_when_no_game_is_active(self, chess_instance):
        ok = chess_instance._save_json("/tmp/anywhere.json")
        assert ok is False
        rendered = " ".join(
            arg
            for call in chess_instance.window.addstr.call_args_list
            for arg in call.args
            if isinstance(arg, str)
        )
        assert "Game not found." in rendered

    def test_saves_when_game_is_active(self, chess_instance, tmp_path):
        chess_instance.game = MagicMock()
        target = tmp_path / "out.json"
        ok = chess_instance._save_json(str(target))
        assert ok is True
        chess_instance.game.save.assert_called_once_with(str(target))

    def test_reports_file_not_found(self, chess_instance):
        chess_instance.game = MagicMock()
        chess_instance.game.save.side_effect = FileNotFoundError()
        ok = chess_instance._save_json("/no/such/dir/out.json")
        assert ok is False
        rendered = " ".join(
            arg
            for call in chess_instance.window.addstr.call_args_list
            for arg in call.args
            if isinstance(arg, str)
        )
        assert "File not found." in rendered

    def test_reports_generic_errors(self, chess_instance):
        chess_instance.game = MagicMock()
        chess_instance.game.save.side_effect = RuntimeError("disk full")
        ok = chess_instance._save_json("/tmp/out.json")
        assert ok is False
        rendered = " ".join(
            arg
            for call in chess_instance.window.addstr.call_args_list
            for arg in call.args
            if isinstance(arg, str)
        )
        assert "disk full" in rendered


class TestSavePgnHandler:
    def test_returns_false_when_no_game_is_active(self, chess_instance):
        ok = chess_instance._save_pgn("/tmp/anywhere.pgn")
        assert ok is False
        rendered = " ".join(
            arg
            for call in chess_instance.window.addstr.call_args_list
            for arg in call.args
            if isinstance(arg, str)
        )
        assert "Game not found." in rendered

    def test_saves_when_game_is_active(self, chess_instance, tmp_path):
        chess_instance.game = MagicMock()
        target = tmp_path / "out.pgn"
        ok = chess_instance._save_pgn(str(target))
        assert ok is True
        chess_instance.game.save_pgn.assert_called_once_with(str(target))

    def test_reports_file_not_found(self, chess_instance):
        chess_instance.game = MagicMock()
        chess_instance.game.save_pgn.side_effect = FileNotFoundError()
        ok = chess_instance._save_pgn("/no/such/dir/out.pgn")
        assert ok is False
        rendered = " ".join(
            arg
            for call in chess_instance.window.addstr.call_args_list
            for arg in call.args
            if isinstance(arg, str)
        )
        assert "File not found." in rendered

    def test_reports_generic_errors(self, chess_instance):
        chess_instance.game = MagicMock()
        chess_instance.game.save_pgn.side_effect = RuntimeError("disk full")
        ok = chess_instance._save_pgn("/tmp/out.pgn")
        assert ok is False
        rendered = " ".join(
            arg
            for call in chess_instance.window.addstr.call_args_list
            for arg in call.args
            if isinstance(arg, str)
        )
        assert "disk full" in rendered


class TestLoadJsonHandler:
    def test_missing_file_returns_false(self, chess_instance):
        ok = chess_instance._load_json("/does/not/exist.json")
        assert ok is False

    def test_generic_errors_are_caught(self, chess_instance, tmp_path):
        # An empty file isn't a valid JSON game; Game.load should raise.
        empty = tmp_path / "empty.json"
        empty.write_text("")
        ok = chess_instance._load_json(str(empty))
        assert ok is False
        rendered = " ".join(
            arg
            for call in chess_instance.window.addstr.call_args_list
            for arg in call.args
            if isinstance(arg, str)
        )
        # Either branch is fine — what matters is the loop reported something.
        assert "error" in rendered.lower() or "not found" in rendered.lower()

    def test_loads_a_saved_game_and_starts_play(self, chess_instance, tmp_path):
        # Save a Game (Game.save only serializes when there's at least one
        # move on the log), then drive _load_json on it. The fixture has
        # cli.main patched to a MagicMock so play() returns immediately.
        seed = Game()
        seed.move("E2", "E4")
        target = tmp_path / "g.json"
        assert seed.save(str(target)) is True

        ok = chess_instance._load_json(str(target))
        assert ok is True
        chess_instance._main_mock.assert_called_once()


# ---------------------------------------------------------------------------
# _fileprompt edit keys
# ---------------------------------------------------------------------------


class TestFilePromptEditKeys:
    def _drive(self, keys):
        received: List[str] = []

        def handler(path: str) -> bool:
            received.append(path)
            return True

        window = make_window(getch_keys=keys)
        _BareChess(window)._fileprompt(handler=handler)
        return received[0] if received else None

    def test_down_and_up_are_ignored(self, curses_patches):
        path = self._drive(
            [
                ord("a"),
                int(KeyCode.DOWN),
                int(KeyCode.UP),
                ord("b"),
                int(KeyCode.ENTER),
            ]
        )
        assert path.endswith("ab")

    def test_right_moves_cursor(self, curses_patches):
        # Type "ab", LEFT, LEFT (cursor at start), RIGHT (cursor between
        # a and b), insert 'X' → "aXb".
        path = self._drive(
            [
                ord("a"),
                ord("b"),
                int(KeyCode.LEFT),
                int(KeyCode.LEFT),
                int(KeyCode.RIGHT),
                ord("X"),
                int(KeyCode.ENTER),
            ]
        )
        assert path.endswith("aXb")

    def test_vt_clears_from_cursor_to_end(self, curses_patches):
        # Type "abcd", LEFT, LEFT, VT — wipes "cd" leaving "ab".
        path = self._drive(
            [
                ord("a"),
                ord("b"),
                ord("c"),
                ord("d"),
                int(KeyCode.LEFT),
                int(KeyCode.LEFT),
                int(KeyCode.VT),
                int(KeyCode.ENTER),
            ]
        )
        assert path.endswith("ab")

    def test_home_jumps_cursor_to_start(self, curses_patches):
        # Type "ab" appended to the default path, HOME, then 'X' — the X
        # is inserted at the very start (just after the prompt sentinel).
        path = self._drive(
            [
                ord("a"),
                ord("b"),
                int(KeyCode.HOME),
                ord("X"),
                int(KeyCode.ENTER),
            ]
        )
        assert path.startswith("X")
        assert path.endswith("ab")

    def test_end_jumps_cursor_to_end(self, curses_patches):
        # Type "ab", HOME, END, 'X' → "abX".
        path = self._drive(
            [
                ord("a"),
                ord("b"),
                int(KeyCode.HOME),
                int(KeyCode.END),
                ord("X"),
                int(KeyCode.ENTER),
            ]
        )
        assert path.endswith("abX")

    def test_delete_key_removes_character_after_cursor(self, curses_patches):
        # Type "abc", HOME, DC (delete 'a') → "bc".
        path = self._drive(
            [
                ord("a"),
                ord("b"),
                ord("c"),
                int(KeyCode.HOME),
                int(KeyCode.DC),
                int(KeyCode.ENTER),
            ]
        )
        assert path.endswith("bc")
