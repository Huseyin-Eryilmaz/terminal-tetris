"""Wall kick tests: the table's shape, and the scenarios it exists for.

Two kinds of test here. The table tests are structural — they catch a
mistyped row without anyone having to eyeball 80 numbers. The scenario
tests are the real proof: board positions where classic rotation gives
up and SRS succeeds, which is the whole point of the system.
"""

import pytest

from tetris.core.board import Board
from tetris.core.piece import PIECE_TYPES, ROTATION_STATES, Piece
from tetris.core.rotation import (
    I_KICKS,
    JLSTZ_KICKS,
    kick_candidates,
    rotate_classic,
    rotate_with_kicks,
)

ADJACENT_ROTATIONS = [
    (0, 1),
    (1, 0),
    (1, 2),
    (2, 1),
    (2, 3),
    (3, 2),
    (3, 0),
    (0, 3),
]


# ----------------------------------------------------------------------
# Table structure
# ----------------------------------------------------------------------
@pytest.mark.parametrize("table", [JLSTZ_KICKS, I_KICKS])
def test_tables_cover_every_adjacent_rotation(table):
    assert set(table) == set(ADJACENT_ROTATIONS)


@pytest.mark.parametrize("table", [JLSTZ_KICKS, I_KICKS])
def test_every_entry_offers_five_candidates(table):
    for transition, offsets in table.items():
        assert len(offsets) == 5, transition


@pytest.mark.parametrize("table", [JLSTZ_KICKS, I_KICKS])
def test_first_candidate_is_always_the_plain_rotation(table):
    """Candidate zero is 'no kick at all'. If it were missing, a rotation
    that already fits would be nudged sideways for no reason."""
    for transition, offsets in table.items():
        assert offsets[0] == (0, 0), transition


@pytest.mark.parametrize(("a", "b"), [(0, 1), (1, 2), (2, 3), (3, 0)])
def test_opposite_transitions_mirror_each_other(a, b):
    """Rotating A->B then B->A should offer opposite kicks; a sign error
    in one direction is the most likely way to mistype these tables."""
    forward = JLSTZ_KICKS[(a, b)]
    backward = JLSTZ_KICKS[(b, a)]
    for (fr, fc), (br, bc) in zip(forward, backward, strict=True):
        assert (fr, fc) == (-br, -bc)


def test_o_piece_never_kicks():
    """A square is identical in all four rotations, so it has nothing to
    kick around."""
    for rotation in range(ROTATION_STATES):
        target = (rotation + 1) % ROTATION_STATES
        assert kick_candidates("O", rotation, target) == [(0, 0)]


@pytest.mark.parametrize("kind", [k for k in PIECE_TYPES if k not in "OI"])
def test_jlstz_pieces_share_one_table(kind):
    assert kick_candidates(kind, 0, 1) == JLSTZ_KICKS[(0, 1)]


def test_the_i_piece_has_its_own_larger_kicks():
    """Being four cells long, the I piece must travel further to clear an
    obstacle — its table shifts by two columns where others shift by one."""
    assert kick_candidates("I", 0, 1) != kick_candidates("T", 0, 1)
    assert any(abs(dc) == 2 for _, dc in kick_candidates("I", 0, 1))


# ----------------------------------------------------------------------
# Behaviour in open space
# ----------------------------------------------------------------------
def test_unobstructed_rotation_uses_no_kick():
    board = Board()
    piece = Piece("T", row=10, col=4)
    result = rotate_with_kicks(piece, 1, board.can_place)
    assert result is not None
    rotated, kick_index = result
    assert kick_index == 0
    assert (rotated.row, rotated.col) == (piece.row, piece.col)


def test_rotation_returns_none_when_every_candidate_is_blocked():
    """A piece encased in blocks cannot rotate however generous SRS is."""
    board = Board()
    for row in range(board.height):
        for col in range(board.width):
            board.grid[row][col] = "X"
    piece = Piece("T", row=10, col=4)
    assert rotate_with_kicks(piece, 1, board.can_place) is None


# ----------------------------------------------------------------------
# The scenarios SRS exists for
# ----------------------------------------------------------------------
def test_vertical_i_kicks_out_of_a_narrow_well():
    """A vertical I standing next to a two-wide wall cannot lie flat where
    it is — classic rotation refuses. SRS shifts it clear and succeeds."""
    board = Board()
    bottom = board.height
    for row in range(bottom - 4, bottom):
        for col in (0, 1):
            board.grid[row][col] = "X"

    vertical = Piece("I", row=bottom - 4, col=0, rotation=1)
    assert board.can_place(vertical)

    assert rotate_classic(vertical, 1, board.can_place) is None

    result = rotate_with_kicks(vertical, 1, board.can_place)
    assert result is not None
    kicked, kick_index = result
    assert kick_index > 0  # a real kick, not the plain rotation
    assert board.can_place(kicked)


def test_t_spin_into_a_covered_slot():
    """The signature modern move: a T slides down a channel and spins into
    a hole it could never have dropped into, completing a line."""
    board = Board()
    bottom = board.height
    for col in range(board.width):
        if col != 4:
            board.grid[bottom - 1][col] = "X"
    for col in range(board.width):
        if col not in (3, 4, 5):
            board.grid[bottom - 2][col] = "X"
    board.grid[bottom - 3][3] = "X"  # the roof that makes it spin-only

    piece = Piece("T", row=bottom - 4, col=3, rotation=3)
    while board.can_place(piece.moved(drow=1)):
        piece = piece.moved(drow=1)

    result = rotate_with_kicks(piece, 1, board.can_place)
    assert result is not None
    spun, _ = result

    board.lock(spun)
    assert len(board.clear_lines()) == 1


def test_classic_rotation_refuses_where_srs_succeeds():
    """The two systems must actually differ — otherwise the rule set flag
    would be decorative."""
    board = Board()
    bottom = board.height
    for row in range(bottom - 4, bottom):
        for col in (0, 1):
            board.grid[row][col] = "X"
    vertical = Piece("I", row=bottom - 4, col=0, rotation=1)

    assert rotate_classic(vertical, 1, board.can_place) is None
    assert rotate_with_kicks(vertical, 1, board.can_place) is not None
