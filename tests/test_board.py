"""Tests for the well: collision, locking, and line clearing.

Boards are built from text art so the setup is visible at a glance —
'X' is a locked block, '.' is empty. A failing test then prints something
a human can actually read.
"""

import pytest

from tetris.core.board import Board
from tetris.core.constants import BOARD_HEIGHT, BOARD_HIDDEN_ROWS, BOARD_WIDTH
from tetris.core.piece import Piece


def board_from_rows(rows: list[str]) -> Board:
    """Builds a board whose bottom rows are the given art (top-padded)."""
    board = Board()
    offset = board.height - len(rows)
    for r, line in enumerate(rows):
        for c, char in enumerate(line):
            if char != ".":
                board.grid[offset + r][c] = "X"
    return board


def bottom_rows(board: Board, count: int) -> list[str]:
    return ["".join(cell or "." for cell in row) for row in board.grid[-count:]]


# ----------------------------------------------------------------------
# Geometry & collision
# ----------------------------------------------------------------------
def test_new_board_is_empty_and_correctly_sized():
    board = Board()
    assert board.width == BOARD_WIDTH
    assert board.height == BOARD_HEIGHT
    assert all(cell is None for row in board.grid for cell in row)


def test_side_walls_and_floor_block_placement():
    board = Board()
    assert not board.can_place(Piece("O", row=0, col=-2))  # through left wall
    assert not board.can_place(Piece("O", row=0, col=BOARD_WIDTH - 1))  # right
    assert not board.can_place(Piece("O", row=BOARD_HEIGHT, col=3))  # floor


def test_ceiling_is_open_so_pieces_can_spawn_and_kick_upward():
    """Unlike the walls, the top is not a barrier: a piece may hang above
    row 0. Treating it as a wall would break spawning and SRS kicks."""
    board = Board()
    assert board.can_place(Piece("I", row=-1, col=3))


def test_placement_fails_when_overlapping_a_locked_block():
    board = Board()
    board.grid[10][4] = "X"
    overlapping = Piece("O", row=9, col=3)  # covers (9,4),(9,5),(10,4),(10,5)
    assert not board.can_place(overlapping)
    assert board.can_place(overlapping.moved(dcol=2))


# ----------------------------------------------------------------------
# Locking
# ----------------------------------------------------------------------
def test_lock_writes_the_piece_kind_into_the_grid():
    board = Board()
    piece = Piece("T", row=5, col=3)
    board.lock(piece)
    for row, col in piece.cells:
        assert board.grid[row][col] == "T"


def test_lock_ignores_cells_above_the_ceiling():
    """A piece can be partly above row 0; those blocks simply vanish
    instead of crashing on a negative index (which in Python would
    silently write to the *bottom* of the grid — a nasty bug)."""
    board = Board()
    piece = Piece("I", row=-1, col=3)
    board.lock(piece)
    assert all(cell is None for cell in board.grid[-1])  # nothing at the floor
    assert any(cell is not None for cell in board.grid[0])


# ----------------------------------------------------------------------
# Line clearing
# ----------------------------------------------------------------------
def test_no_full_rows_clears_nothing():
    board = board_from_rows(["XXXXXXXXX."])
    assert board.clear_lines() == []


def test_single_full_row_is_removed():
    board = board_from_rows(["XXXXXXXXXX"])
    cleared = board.clear_lines()
    assert len(cleared) == 1
    assert board.is_row_empty(board.height - 1)


def test_rows_above_fall_down_by_the_number_cleared():
    board = board_from_rows(
        [
            "X.........",  # survivor
            "XXXXXXXXXX",  # cleared
        ]
    )
    board.clear_lines()
    assert bottom_rows(board, 2) == ["..........", "X........."]


def test_multiple_adjacent_rows_clear_together():
    """A tetris: four rows at once. Deleting rows in place while iterating
    is where naive implementations skip one — this must remove all four."""
    board = board_from_rows(["XXXXXXXXXX"] * 4)
    cleared = board.clear_lines()
    assert len(cleared) == 4
    assert all(board.is_row_empty(r) for r in range(board.height))


def test_non_adjacent_rows_clear_and_the_gap_row_survives():
    board = board_from_rows(
        [
            "XXXXXXXXXX",  # cleared
            "..XX......",  # survives, falls by one
            "XXXXXXXXXX",  # cleared
        ]
    )
    cleared = board.clear_lines()
    assert len(cleared) == 2
    assert bottom_rows(board, 3) == ["..........", "..........", "..XX......"]


def test_clearing_preserves_the_colour_of_surviving_blocks():
    board = Board()
    board.grid[-2][0] = "T"
    for col in range(BOARD_WIDTH):
        board.grid[-1][col] = "I"
    board.clear_lines()
    assert board.grid[-1][0] == "T"  # the T block fell, still a T


# ----------------------------------------------------------------------
# Introspection
# ----------------------------------------------------------------------
def test_top_out_is_detected_only_in_the_hidden_rows():
    board = Board()
    board.grid[BOARD_HIDDEN_ROWS][0] = "X"  # first visible row
    assert not board.is_topped_out()
    board.grid[BOARD_HIDDEN_ROWS - 1][0] = "X"  # hidden spawn row
    assert board.is_topped_out()


@pytest.mark.parametrize(("filled_row", "expected"), [(None, 0), (-1, 1), (-4, 4)])
def test_column_height(filled_row, expected):
    board = Board()
    if filled_row is not None:
        board.grid[filled_row][2] = "X"
    assert board.height_of_column(2) == expected


def test_str_renders_a_readable_grid():
    board = board_from_rows(["X.X......."])
    assert board.__str__().splitlines()[-1] == "X.X......."