"""Tests for the game loop: gravity, actions, locking and top-out.

Time is a parameter here, not a wall clock — `tick(dt)` is called with
whatever delta the test needs, so a "one second of gravity" test runs
instantly and deterministically.
"""

import pytest

from tetris.core.constants import BOARD_HIDDEN_ROWS, BOARD_WIDTH
from tetris.core.game import (
    DEFAULT_GRAVITY_INTERVAL,
    SOFT_DROP_MULTIPLIER,
    Action,
    Game,
    GameState,
)
from tetris.core.piece import Piece


@pytest.fixture()
def game() -> Game:
    return Game(seed=1)


def force_piece(game: Game, kind: str, row: int = 0, col: int = 3) -> None:
    """Replaces the current piece, so tests don't depend on the RNG."""
    game.current = Piece(kind, row=row, col=col)


# ----------------------------------------------------------------------
# Spawning
# ----------------------------------------------------------------------
def test_game_starts_playing_with_a_piece_in_the_hidden_rows(game):
    assert game.state is GameState.PLAYING
    assert game.current.row < BOARD_HIDDEN_ROWS + 2


def test_spawn_is_roughly_centred():
    game = Game(seed=7)
    columns = [col for _, col in game.current.cells]
    centre = BOARD_WIDTH / 2
    assert abs(sum(columns) / len(columns) - centre) <= 1.5


def test_same_seed_replays_the_same_pieces():
    """Reproducibility: the whole point of seeding. A bug report becomes
    'run seed 42' instead of 'it happened once, I think'."""
    kinds_a = [Game(seed=42)._next_kind() for _ in range(20)]
    kinds_b = [Game(seed=42)._next_kind() for _ in range(20)]
    assert kinds_a == kinds_b


# ----------------------------------------------------------------------
# Movement
# ----------------------------------------------------------------------
def test_move_left_and_right(game):
    force_piece(game, "O", row=5, col=4)
    game.apply(Action.MOVE_LEFT)
    assert game.current.col == 3
    game.apply(Action.MOVE_RIGHT)
    assert game.current.col == 4


def test_movement_stops_at_the_walls(game):
    force_piece(game, "O", row=5, col=-1)  # O occupies cols 0..1 here
    game.apply(Action.MOVE_LEFT)
    assert game.current.col == -1  # refused, piece unchanged


def test_movement_is_blocked_by_locked_blocks(game):
    force_piece(game, "O", row=5, col=4)  # occupies cols 5-6
    for row in range(4, 8):
        game.board.grid[row][4] = "X"  # wall of blocks immediately left
    game.apply(Action.MOVE_LEFT)
    assert game.current.col == 4


def test_rotation_changes_state_when_it_fits(game):
    force_piece(game, "T", row=5, col=4)
    game.apply(Action.ROTATE_CW)
    assert game.current.rotation == 1
    game.apply(Action.ROTATE_CCW)
    assert game.current.rotation == 0


def test_rotation_is_refused_when_blocked(game):
    """Classic rules: no wall kicks. A flat I piece in a one-row-high gap
    cannot stand up, and simply stays as it is."""
    force_piece(game, "I", row=5, col=3)  # occupies row 6, cols 3-6
    for col in range(3, 7):
        game.board.grid[8][col] = "X"  # ceiling of the gap below
        game.board.grid[4][col] = "X"  # floor of the gap above
    before = game.current
    game.apply(Action.ROTATE_CW)
    assert game.current == before


# ----------------------------------------------------------------------
# Gravity
# ----------------------------------------------------------------------
def test_piece_falls_after_the_gravity_interval(game):
    force_piece(game, "T", row=5, col=4)
    game.tick(DEFAULT_GRAVITY_INTERVAL * 0.9)
    assert game.current.row == 5  # not yet
    game.tick(DEFAULT_GRAVITY_INTERVAL * 0.2)
    assert game.current.row == 6


def test_a_long_frame_applies_every_owed_row(game):
    """If three intervals' worth of time passes at once, the piece falls
    three rows — not one. Otherwise a slow frame silently pauses gravity."""
    force_piece(game, "T", row=2, col=4)
    game.tick(DEFAULT_GRAVITY_INTERVAL * 3.5)
    assert game.current.row == 5


def test_soft_drop_speeds_up_gravity(game):
    force_piece(game, "T", row=2, col=4)
    game.apply(Action.SOFT_DROP)
    game.tick(DEFAULT_GRAVITY_INTERVAL / SOFT_DROP_MULTIPLIER)
    assert game.current.row == 3


def test_releasing_soft_drop_restores_normal_speed(game):
    force_piece(game, "T", row=2, col=4)
    game.apply(Action.SOFT_DROP)
    game.release_soft_drop()
    game.tick(DEFAULT_GRAVITY_INTERVAL / SOFT_DROP_MULTIPLIER)
    assert game.current.row == 2


# ----------------------------------------------------------------------
# Landing and locking
# ----------------------------------------------------------------------
def test_piece_locks_when_it_cannot_fall(game):
    force_piece(game, "O", row=game.board.height - 2, col=4)
    landed = game.current
    game.tick(DEFAULT_GRAVITY_INTERVAL)
    assert game.pieces_placed == 1
    for row, col in landed.cells:
        assert game.board.grid[row][col] == "O"
    assert game.current is not landed  # a new piece arrived


def test_hard_drop_lands_and_locks_immediately(game):
    force_piece(game, "T", row=2, col=4)
    game.apply(Action.HARD_DROP)
    assert game.pieces_placed == 1
    bottom = game.board.grid[game.board.height - 1]
    assert any(cell == "T" for cell in bottom)


def test_ghost_position_is_where_a_hard_drop_would_land(game):
    force_piece(game, "T", row=2, col=4)
    ghost = game.ghost_position()
    game.apply(Action.HARD_DROP)
    for row, col in ghost.cells:
        assert game.board.grid[row][col] == "T"


def test_locking_a_full_row_clears_it_and_counts_it(game):
    for col in range(BOARD_WIDTH):
        if col not in (5, 6):  # O at col=4 fills columns 5 and 6
            game.board.grid[game.board.height - 1][col] = "X"
    force_piece(game, "O", row=game.board.height - 3, col=4)
    game.apply(Action.HARD_DROP)
    assert game.lines_cleared == 1


# ----------------------------------------------------------------------
# Game over
# ----------------------------------------------------------------------
def test_game_ends_when_a_new_piece_cannot_spawn(game):
    """The stack reaches the spawn area. Rows are left one cell short of
    full on purpose: a full row would clear on lock and free the space."""
    for row in range(BOARD_HIDDEN_ROWS, game.board.height):
        for col in range(BOARD_WIDTH - 1):  # leave the last column open
            game.board.grid[row][col] = "X"
    force_piece(game, "O", row=0, col=4)
    game.apply(Action.HARD_DROP)
    assert game.state is GameState.GAME_OVER


def test_actions_and_gravity_are_ignored_after_game_over(game):
    game.state = GameState.GAME_OVER
    force_piece(game, "T", row=5, col=4)
    game.apply(Action.MOVE_LEFT)
    game.tick(DEFAULT_GRAVITY_INTERVAL * 5)
    assert game.current == Piece("T", row=5, col=4)


# ----------------------------------------------------------------------
# Rendering support
# ----------------------------------------------------------------------
def test_visible_cells_hides_the_spawn_rows(game):
    assert len(game.visible_cells()) == game.board.height - BOARD_HIDDEN_ROWS


def test_visible_cells_composites_the_falling_piece(game):
    force_piece(game, "O", row=BOARD_HIDDEN_ROWS + 3, col=4)
    rows = game.visible_cells()
    assert rows[3][5] == "O"


def test_visible_cells_does_not_mutate_the_board(game):
    force_piece(game, "O", row=BOARD_HIDDEN_ROWS + 3, col=4)
    game.visible_cells()
    assert all(cell is None for row in game.board.grid for cell in row)
