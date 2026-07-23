"""The screen state machine: which key leads where, and what pausing means.

These tests never touch a terminal — the app takes `Key` values in and
reports which screen it is on, so every transition can be driven directly.
"""

import pytest

from tetris.core.app import App, Screen
from tetris.core.game import GameState
from tetris.core.keys import Key
from tetris.core.piece import Piece


@pytest.fixture()
def app() -> App:
    return App(seed=1)


@pytest.fixture()
def playing_app() -> App:
    app = App(seed=1)
    app.start_game("modern")
    return app


# ----------------------------------------------------------------------
# Menu
# ----------------------------------------------------------------------
def test_the_app_opens_on_the_menu(app):
    assert app.screen is Screen.MENU
    assert app.game is None


@pytest.mark.parametrize(("key", "mode"), [(Key.D1, "CLASSIC"), (Key.D2, "MODERN")])
def test_menu_digits_start_the_matching_mode(app, key, mode):
    app.handle_keys([key])
    assert app.screen is Screen.PLAYING
    assert app.game is not None
    assert app.rules.name == mode


def test_menu_opens_and_closes_the_controls_screen(app):
    app.handle_keys([Key.D3])
    assert app.screen is Screen.HELP
    app.handle_keys([Key.ENTER])
    assert app.screen is Screen.MENU


@pytest.mark.parametrize("key", [Key.D4, Key.Q, Key.ESCAPE])
def test_the_menu_can_quit(app, key):
    app.handle_keys([key])
    assert app.screen is Screen.QUIT
    assert not app.is_running


def test_gameplay_keys_do_nothing_in_the_menu(app):
    """A stray SPACE on the title screen must not start or affect a game."""
    app.handle_keys([Key.SPACE, Key.LEFT, Key.C])
    assert app.screen is Screen.MENU
    assert app.game is None


# ----------------------------------------------------------------------
# Pausing
# ----------------------------------------------------------------------
def test_p_pauses_and_resumes(playing_app):
    playing_app.handle_keys([Key.P])
    assert playing_app.screen is Screen.PAUSED
    playing_app.handle_keys([Key.P])
    assert playing_app.screen is Screen.PLAYING


def test_time_does_not_pass_while_paused(playing_app):
    """Pausing is not a flag inside the rules — the game simply stops
    being ticked, so nothing in the core needs to know pausing exists."""
    playing_app.handle_keys([Key.P])
    piece_before = playing_app.game.current

    playing_app.tick(10.0)

    assert playing_app.game.current == piece_before
    assert playing_app.game.pieces_placed == 0


def test_the_game_survives_a_pause(playing_app):
    playing_app.game.current = Piece("T", row=8, col=4)
    playing_app.handle_keys([Key.P])
    playing_app.tick(5.0)
    playing_app.handle_keys([Key.P])

    assert playing_app.game.current.row == 8  # exactly where it was


def test_gameplay_keys_are_ignored_while_paused(playing_app):
    playing_app.game.current = Piece("T", row=8, col=4)
    playing_app.handle_keys([Key.P])
    playing_app.handle_keys([Key.LEFT, Key.SPACE])
    assert playing_app.game.current == Piece("T", row=8, col=4)


def test_escape_from_pause_returns_to_the_menu(playing_app):
    playing_app.handle_keys([Key.P, Key.ESCAPE])
    assert playing_app.screen is Screen.MENU


# ----------------------------------------------------------------------
# Playing
# ----------------------------------------------------------------------
def test_gameplay_keys_reach_the_game(playing_app):
    playing_app.game.current = Piece("O", row=8, col=4)
    playing_app.handle_keys([Key.LEFT])
    assert playing_app.game.current.col == 3


def test_escape_abandons_the_game_without_recording_a_score(playing_app, tmp_path):
    playing_app.handle_keys([Key.ESCAPE])
    assert playing_app.screen is Screen.MENU
    assert playing_app.last_rank is None


def test_reaching_a_top_out_moves_to_the_game_over_screen(playing_app, monkeypatch):
    monkeypatch.setattr("tetris.core.app.record_score", lambda *a, **k: ([], None))
    playing_app.game.state = GameState.GAME_OVER
    playing_app.tick(0.1)
    assert playing_app.screen is Screen.GAME_OVER


# ----------------------------------------------------------------------
# Game over
# ----------------------------------------------------------------------
@pytest.fixture()
def finished_app(monkeypatch) -> App:
    monkeypatch.setattr("tetris.core.app.record_score", lambda *a, **k: ([], 1))
    app = App(seed=1)
    app.start_game("modern")
    assert app.game is not None
    app.game.state = GameState.GAME_OVER
    app.tick(0.1)
    return app


def test_r_starts_a_fresh_game_in_the_same_mode(finished_app):
    finished_app.handle_keys([Key.R])
    assert finished_app.screen is Screen.PLAYING
    assert finished_app.game.state is GameState.PLAYING
    assert finished_app.game.pieces_placed == 0
    assert finished_app.rules.name == "MODERN"


def test_enter_returns_to_the_menu(finished_app):
    finished_app.handle_keys([Key.ENTER])
    assert finished_app.screen is Screen.MENU


def test_a_finished_game_records_its_score(monkeypatch):
    recorded = {}

    def fake_record(mode, entry, *args, **kwargs):
        recorded["mode"] = mode
        recorded["score"] = entry.score
        return [entry], 1

    monkeypatch.setattr("tetris.core.app.record_score", fake_record)
    app = App(seed=1)
    app.start_game("classic")
    assert app.game is not None
    app.game.scorer.score = 4242
    app.game.state = GameState.GAME_OVER
    app.tick(0.1)

    assert recorded["mode"] == "classic"
    assert recorded["score"] == 4242
    assert app.last_rank == 1
