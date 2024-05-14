from curses import A_BOLD, A_COLOR, A_DIM, wrapper
from curses import window as Window
from functools import partial
from typing import Callable, Optional, cast

from dateutil.parser import parse
from interface.draw import check_window_maxyx, draw_breadcrumbs
from interface.game import LogStyle, draw_head, main
from interface.input import fileprompt
from interface.menu import Menu

from game import Game, PGNFile


class Configuration:
    log_style = LogStyle.CoordinateNotation


class Chess(object):
    def __init__(self, window: Window):
        check_window_maxyx(window)
        draw_head(window)

        class Menus:
            root = Menu(
                [
                    ("new game", self.play),
                    ("load file", self.draw_load_menu),
                    ("options", self.draw_cfg_menu),
                    ("about", self.draw_about),
                ],
                window,
            )
            load = Menu(
                [
                    ("PGN", self.load_pgn),
                    ("JSON", self.load_json),
                ],
                window,
                ("load file",),
            )
            save = Menu(
                [
                    ("PGN", self.save_pgn),
                    ("JSON", self.save_json),
                ],
                window,
                ("save file",),
            )
            cfg = Menu(
                [
                    ("log style", self.draw_cfg_log_style_menu),
                ],
                window,
                ("options",),
            )

        self.window = window
        self.game: Optional[Game] = None
        self.menus = Menus()
        self.cfg = Configuration()

        self.menus.root.display()

    def draw_save_menu(self):
        self.menus.save.display()

        self.menus.save.position = 0

    def draw_load_menu(self):
        self.menus.load.display()

        self.menus.load.position = 0

    def draw_cfg_menu(self):
        self.menus.cfg.display()

        self.menus.cfg.position = 0

    def draw_cfg_log_style_menu(self):
        def set_style(style: LogStyle):
            self.cfg.log_style = style

            raise KeyboardInterrupt

        menu = Menu(
            [
                (
                    label,
                    partial(set_style, log_style),
                    A_BOLD if self.cfg.log_style == log_style else 0,
                )
                for log_style, label in (
                    (LogStyle.CoordinateNotation, "Coordinates"),
                    (LogStyle.AlgebraicNotation, "Algebraic Notation"),
                )
            ],
            self.window,
            ("options", "log style"),
        )

        menu.position = self.cfg.log_style.value

        menu.display()

    def draw_about(self):
        y = 4

        self.window.move(y, 0)
        self.window.clrtobot()
        self.window.addstr(y + 0, 6, f"© 2021 Brandon Zacharie", A_COLOR)
        self.window.addstr(y + 2, 6, "github: BrandonZacharie/Chess.py", A_COLOR)
        self.window.addstr(y + 3, 6, f"semver: {Game.VERSION}", A_COLOR)
        self.window.addstr(y + 5, 6, "Press any key to continue...")
        self.window.getch()

    def play(self, game: Optional[Game] = None):
        if self.game is None:
            self.menus.root.insert(0, ("continue…", lambda: self.play(self.game)))
            self.menus.root.insert(2, ("save file", self.draw_save_menu))

        self.game = Game() if game is None else game

        main(self.window, self.game, self.cfg.log_style)

        self.menus.root.position = 0

    def _fileprompt(
        self,
        filename: Optional[str] = None,
        handler: Optional["Callable[[str], bool]"] = None,
    ):
        fileprompt(self.window, filename, handler)

    def save_pgn(self):
        if self.menus.save.title is not None:
            draw_breadcrumbs(self.window, (6, 3), *self.menus.save.title, "PGN")

        self._fileprompt(handler=self._save_pgn)

        raise KeyboardInterrupt

    def save_json(self):
        if self.menus.save.title is not None:
            draw_breadcrumbs(self.window, (6, 3), *self.menus.save.title, "JSON")

        self._fileprompt(handler=self._save_json)

        raise KeyboardInterrupt

    def load_pgn(self):
        if self.menus.load.title is not None:
            draw_breadcrumbs(self.window, (6, 3), *self.menus.load.title, "PGN")

        self._fileprompt(handler=self._load_pgn)

    def load_json(self):
        if self.menus.load.title is not None:
            draw_breadcrumbs(self.window, (6, 3), *self.menus.load.title, "JSON")

        self._fileprompt(handler=self._load_json)

    def _save_json(self, filename: str) -> bool:
        x = 5
        y = 6

        if self.game is None:
            self.window.addstr(y + 2, x, "Game not found.", A_COLOR)
        else:
            try:
                self.game.save(filename)

                return True
            except FileNotFoundError:
                self.window.addstr(y + 2, x, "File not found.", A_COLOR)
            except Exception as e:
                self.window.addstr(y + 2, x, f"Error: {e}", A_COLOR)

        return False

    def _save_pgn(self, filename: str) -> bool:
        x = 5
        y = 6

        if self.game is None:
            self.window.addstr(y + 2, x, "Game not found.", A_COLOR)
        else:
            try:
                self.game.save_pgn(filename)

                return True
            except FileNotFoundError:
                self.window.addstr(y + 2, x, "File not found.", A_COLOR)
            except Exception as e:
                self.window.addstr(y + 2, x, f"Error: {e}", A_COLOR)

        return False

    def _load_pgn(self, filename: str) -> bool:
        x = 5
        y = 6

        try:
            pgn_file = PGNFile(filename)

            if len(pgn_file) == 0:
                self.window.addstr(y + 2, x, "No games found.", A_COLOR)
            else:
                Menu(
                    [
                        (
                            f"{parse(cast(str, game.date).replace('.??', ''), fuzzy=True).date()} \"{game.event}\" {game.white} vs. {game.black}",
                            partial(lambda i: self.play(pgn_file.game(i)), i),
                        )
                        for i, game in enumerate(pgn_file)
                    ],
                    self.window,
                ).display()

            return True
        except FileNotFoundError:
            self.window.addstr(y + 2, x, "File not found.", A_COLOR)
        except Exception as e:
            self.window.addstr(y + 2, x, f"Error: {e}", A_COLOR)

        return False

    def _load_json(self, filename: str) -> bool:
        x = 5
        y = 6

        try:
            game = Game()

            game.load(filename)
            self.play(game)

            return True
        except FileNotFoundError:
            self.window.addstr(y + 2, x, "File not found.", A_COLOR)
        except Exception as e:
            self.window.addstr(y + 2, x, f"Error: {e}", A_COLOR)

        return False


if __name__ == "__main__":  # pragma: no cover
    wrapper(Chess)
