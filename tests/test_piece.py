"""Tests for tetromino geometry.

These lock down properties that must hold for every piece in every
rotation — the kind of invariants that catch a typo in the shape tables,
which is otherwise very hard to spot by reading.
"""

import pytest

from tetris.core.piece import PIECE_TYPES, ROTATION_STATES, SHAPES, Piece


@pytest.mark.parametrize("kind", PIECE_TYPES)
def test_every_piece_has_four_rotation_states(kind):
    assert len(SHAPES[kind]) == ROTATION_STATES


@pytest.mark.parametrize("kind", PIECE_TYPES)
@pytest.mark.parametrize("rotation", range(ROTATION_STATES))
def test_every_rotation_has_exactly_four_cells(kind, rotation):
    """A tetromino is four blocks — 'tetra'. A typo that drops or repeats
    an offset would silently create a three- or five-block piece."""
    offsets = SHAPES[kind][rotation]
    assert len(offsets) == 4
    assert len(set(offsets)) == 4  # no duplicated cell


@pytest.mark.parametrize("kind", PIECE_TYPES)
@pytest.mark.parametrize("rotation", range(ROTATION_STATES))
def test_offsets_fit_in_a_four_by_four_box(kind, rotation):
    for row, col in SHAPES[kind][rotation]:
        assert 0 <= row < 4
        assert 0 <= col < 4


@pytest.mark.parametrize("kind", PIECE_TYPES)
@pytest.mark.parametrize("rotation", range(ROTATION_STATES))
def test_all_cells_are_connected(kind, rotation):
    """Every block must touch another block edge-to-edge; a diagonal-only
    'piece' would be a shape table error."""
    cells = set(SHAPES[kind][rotation])
    reached = {next(iter(cells))}
    frontier = list(reached)
    while frontier:
        row, col = frontier.pop()
        neighbors = ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1))
        for neighbor in neighbors:
            if neighbor in cells and neighbor not in reached:
                reached.add(neighbor)
                frontier.append(neighbor)
    assert reached == cells


def test_o_piece_never_changes_shape():
    """The square is rotationally symmetric; all four states are identical."""
    states = SHAPES["O"]
    assert all(state == states[0] for state in states)


@pytest.mark.parametrize("kind", ["I", "S", "Z"])
def test_two_fold_symmetric_pieces_repeat_after_two_turns(kind):
    """I, S and Z look the same rotated 180 degrees, just shifted — so
    their cell *patterns* (normalized to the origin) repeat."""

    def normalized(offsets):
        min_row = min(r for r, _ in offsets)
        min_col = min(c for _, c in offsets)
        return sorted((r - min_row, c - min_col) for r, c in offsets)

    assert normalized(SHAPES[kind][0]) == normalized(SHAPES[kind][2])
    assert normalized(SHAPES[kind][1]) == normalized(SHAPES[kind][3])


def test_cells_are_offsets_plus_position():
    piece = Piece("T", row=5, col=3)
    expected = [(5 + dr, 3 + dc) for dr, dc in SHAPES["T"][0]]
    assert piece.cells == expected


def test_moved_returns_a_new_piece_and_leaves_the_original_alone():
    original = Piece("L", row=2, col=2)
    moved = original.moved(drow=1, dcol=-1)
    assert (moved.row, moved.col) == (3, 1)
    assert (original.row, original.col) == (2, 2)
    assert moved is not original


def test_rotation_wraps_around_in_both_directions():
    piece = Piece("J", rotation=3)
    assert piece.rotated().rotation == 0
    assert Piece("J", rotation=0).rotated(-1).rotation == 3


def test_four_rotations_return_to_the_start():
    piece = Piece("S", row=4, col=4, rotation=0)
    result = piece.rotated().rotated().rotated().rotated()
    assert result == piece  # frozen dataclass compares by value
