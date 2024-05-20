from curses import A_BOLD, A_COLOR, wrapper
from curses import window as Window
from enum import StrEnum
from functools import partial
from typing import Callable, Optional, cast

from dateutil.parser import parse
from interface.draw import check_window_maxyx, draw_breadcrumbs
from interface.game import LogStyle, draw_head, main
from interface.input import fileprompt
from interface.menu import Menu

from game import Game, PGNFile


class Label(StrEnum):
    MakeGame = "new game"
    SaveGame = "save game"
    PlayGame = "continue…"
    LoadFile = "load file"
    SaveFile = "save file"
    Options = "options"
    About = "about"
    LogStyle = "log style"
    Reset = "factory reset"
    PGN = "PGN"
    JSON = "JSON"
    CoordinateNotation = "Coordinates"
    AlgebraicNotation = "Algebraic Notation"
    FileNotFound = "File not found."
    GameNotFound = "Game not found."
    GamesNotFound = "No games found."
    PressAnyKey = "Press any key to continue…"
    Error = "Error"


class Configuration:
    log_style = LogStyle.CoordinateNotation


class Chess(object):
    def __init__(self, window: Window):
        check_window_maxyx(window)
        draw_head(window)

        class Menus:
            root = Menu(
                [
                    (Label.MakeGame, self.play),
                    (Label.LoadFile, self.draw_load_menu),
                    (Label.Options, self.draw_cfg_menu),
                    (Label.About, self.draw_about),
                ],
                window,
            )
            load = Menu(
                [
                    (Label.PGN, self.load_pgn),
                    (Label.JSON, self.load_json),
                ],
                window,
                (Label.LoadFile,),
            )
            save = Menu(
                [
                    (Label.PGN, self.save_pgn),
                    (Label.JSON, self.save_json),
                ],
                window,
                (Label.SaveFile,),
            )
            cfg = Menu(
                [
                    (Label.LogStyle, self.draw_cfg_log_style_menu),
                    (Label.Reset, self.reset),
                ],
                window,
                (Label.Options,),
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
                    (LogStyle.CoordinateNotation, Label.CoordinateNotation),
                    (LogStyle.AlgebraicNotation, Label.AlgebraicNotation),
                )
            ],
            self.window,
            (Label.Options, Label.LogStyle),
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
        self.window.addstr(y + 5, 6, Label.PressAnyKey)
        self.window.getch()

    def play(self, game: Optional[Game] = None):
        if self.game is None:
            self.menus.root.insert(0, (Label.PlayGame, lambda: self.play(self.game)))
            self.menus.root.insert(2, (Label.SaveGame, self.draw_save_menu))

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
            draw_breadcrumbs(self.window, (6, 3), *self.menus.save.title, Label.PGN)

        self._fileprompt(handler=self._save_pgn)

        raise KeyboardInterrupt

    def save_json(self):
        if self.menus.save.title is not None:
            draw_breadcrumbs(self.window, (6, 3), *self.menus.save.title, Label.JSON)

        self._fileprompt(handler=self._save_json)

        raise KeyboardInterrupt

    def load_pgn(self):
        if self.menus.load.title is not None:
            draw_breadcrumbs(self.window, (6, 3), *self.menus.load.title, Label.PGN)

        self._fileprompt(handler=self._load_pgn)

    def load_json(self):
        if self.menus.load.title is not None:
            draw_breadcrumbs(self.window, (6, 3), *self.menus.load.title, Label.JSON)

        self._fileprompt(handler=self._load_json)

    def reset(self):
        self.cfg = Configuration()
        self.game = None

        for index, (label, *_) in enumerate(self.menus.root.items):
            if label == Label.PlayGame or label == Label.SaveFile:
                self.menus.root.pop(index)

        raise KeyboardInterrupt

    def _save_json(self, filename: str) -> bool:
        x = 5
        y = 6

        if self.game is None:
            self.window.addstr(y + 2, x, Label.GameNotFound, A_COLOR)
        else:
            try:
                self.game.save(filename)

                return True
            except FileNotFoundError:
                self.window.addstr(y + 2, x, Label.FileNotFound, A_COLOR)
            except Exception as e:
                self.window.addstr(y + 2, x, f"{Label.Error}: {e}", A_COLOR)

        return False

    def _save_pgn(self, filename: str) -> bool:
        x = 5
        y = 6

        if self.game is None:
            self.window.addstr(y + 2, x, Label.GameNotFound, A_COLOR)
        else:
            try:
                self.game.save_pgn(filename)

                return True
            except FileNotFoundError:
                self.window.addstr(y + 2, x, Label.FileNotFound, A_COLOR)
            except Exception as e:
                self.window.addstr(y + 2, x, f"{Label.Error}: {e}", A_COLOR)

        return False

    def _load_pgn(self, filename: str) -> bool:
        x = 5
        y = 6

        try:
            pgn_file = PGNFile(filename)

            if len(pgn_file) == 0:
                self.window.addstr(y + 2, x, Label.GamesNotFound, A_COLOR)
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
            self.window.addstr(y + 2, x, Label.FileNotFound, A_COLOR)
        except Exception as e:
            self.window.addstr(y + 2, x, f"{Label.Error}: {e}", A_COLOR)

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
            self.window.addstr(y + 2, x, Label.FileNotFound, A_COLOR)
        except Exception as e:
            self.window.addstr(y + 2, x, f"{Label.Error}: {e}", A_COLOR)

        return False


if __name__ == "__main__":  # pragma: no cover
    wrapper(Chess)
