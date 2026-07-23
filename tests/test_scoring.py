"""Scoring, levels, and T-spin recognition.

The scoring tables are data, so most of these tests pin down the shape of
the rules rather than individual numbers: a tetris must beat four singles,
a T-spin must beat a plain clear, and the level curve must keep speeding
up without ever reaching zero.
"""

import pytest

from tetris.core.board import Board
from tetris.core.piece import Piece
from tetris.core.scoring import (
    CLASSIC_LINE_SCORES,
    GUIDELINE_LINE_SCORES,
    LINES_PER_LEVEL,
    MAX_LEVEL,
    ScoreEvent,
    Scorer,
    SpinType,
    detect_spin,
    gravity_interval_for_level,
)


# ----------------------------------------------------------------------
# Line scoring
# ----------------------------------------------------------------------
@pytest.mark.parametrize("table", [CLASSIC_LINE_SCORES, GUIDELINE_LINE_SCORES])
def test_clearing_more_at_once_is_worth_more(table):
    values = [table[n] for n in range(5)]
    assert values == sorted(values)


@pytest.mark.parametrize("table", [CLASSIC_LINE_SCORES, GUIDELINE_LINE_SCORES])
def test_a_tetris_beats_four_separate_singles(table):
    """The central incentive of the game: patience pays."""
    assert table[4] > 4 * table[1]


def test_classic_scores_scale_with_level():
    low = Scorer(use_guideline=False)
    high = Scorer(use_guideline=False, level=5)
    assert (
        high.register_lock(1, SpinType.NONE).points
        > low.register_lock(1, SpinType.NONE).points
    )


def test_clearing_nothing_scores_nothing():
    scorer = Scorer(use_guideline=True)
    assert scorer.register_lock(0, SpinType.NONE).points == 0


# ----------------------------------------------------------------------
# Levels and gravity
# ----------------------------------------------------------------------
def test_level_rises_every_ten_lines():
    scorer = Scorer(use_guideline=True)
    assert scorer.level == 1
    for _ in range(LINES_PER_LEVEL // 2):
        scorer.register_lock(2, SpinType.NONE)
    assert scorer.level == 2


def test_level_is_capped():
    scorer = Scorer(use_guideline=True)
    for _ in range(300):
        scorer.register_lock(4, SpinType.NONE)
    assert scorer.level == MAX_LEVEL


def test_gravity_speeds_up_with_level():
    intervals = [gravity_interval_for_level(level) for level in range(1, 16)]
    assert intervals == sorted(intervals, reverse=True)


def test_gravity_never_reaches_zero():
    """A piece must always be visible for at least a frame or two — an
    interval of zero would make the game unplayable, not merely hard."""
    assert gravity_interval_for_level(99) > 0.0


# ----------------------------------------------------------------------
# T-spin detection
# ----------------------------------------------------------------------
def corner_board(corners: list[tuple[int, int]]) -> Board:
    """A board with blocks at the given absolute coordinates."""
    board = Board()
    for row, col in corners:
        board.grid[row][col] = "X"
    return board


def test_a_t_wedged_in_three_corners_after_rotating_is_a_spin():
    # T at (10, 4): its 3x3 box corners are (10,4) (10,6) (12,4) (12,6).
    board = corner_board([(10, 4), (10, 6), (12, 4)])
    piece = Piece("T", row=10, col=4, rotation=0)
    assert detect_spin(board, piece, last_move_was_rotation=True) is SpinType.FULL


def test_the_same_position_without_a_rotation_is_not_a_spin():
    """A piece that merely fell into a tight gap did not spin into it."""
    board = corner_board([(10, 4), (10, 6), (12, 4)])
    piece = Piece("T", row=10, col=4, rotation=0)
    assert detect_spin(board, piece, last_move_was_rotation=False) is SpinType.NONE


def test_two_filled_corners_are_not_enough():
    board = corner_board([(10, 4), (12, 4)])
    piece = Piece("T", row=10, col=4, rotation=0)
    assert detect_spin(board, piece, last_move_was_rotation=True) is SpinType.NONE


def test_only_the_t_piece_can_spin():
    board = corner_board([(10, 4), (10, 6), (12, 4), (12, 6)])
    for kind in "IOSZJL":
        piece = Piece(kind, row=10, col=4)
        assert detect_spin(board, piece, last_move_was_rotation=True) is SpinType.NONE


def test_a_spin_with_only_one_front_corner_is_a_mini():
    """Rotation 0 points its tip up, so its front corners are the top two.
    Filling only one of them makes this the lesser 'mini' spin."""
    board = corner_board([(10, 4), (12, 4), (12, 6)])
    piece = Piece("T", row=10, col=4, rotation=0)
    assert detect_spin(board, piece, last_move_was_rotation=True) is SpinType.MINI


def test_walls_count_as_filled_corners():
    """A T spun into the bottom corner of the well is wedged by the wall
    and the floor, even though no blocks are there: two corners sit past
    the left wall and one past the floor."""
    board = Board()
    piece = Piece("T", row=board.height - 2, col=-1, rotation=1)
    assert detect_spin(board, piece, last_move_was_rotation=True) is not SpinType.NONE


# ----------------------------------------------------------------------
# Guideline extras
# ----------------------------------------------------------------------
def test_a_t_spin_outscores_a_plain_clear_of_the_same_size():
    plain = Scorer(use_guideline=True).register_lock(1, SpinType.NONE).points
    spin = Scorer(use_guideline=True).register_lock(1, SpinType.FULL).points
    assert spin > plain


def test_back_to_back_difficult_clears_pay_a_bonus():
    plain_scorer = Scorer(use_guideline=True)
    first = plain_scorer.register_lock(4, SpinType.NONE)
    second = plain_scorer.register_lock(4, SpinType.NONE)
    assert not first.is_back_to_back
    assert second.is_back_to_back
    assert second.points > first.points


def test_an_easy_clear_breaks_the_back_to_back_streak():
    scorer = Scorer(use_guideline=True)
    scorer.register_lock(4, SpinType.NONE)  # difficult
    scorer.register_lock(1, SpinType.NONE)  # easy: streak broken
    third = scorer.register_lock(4, SpinType.NONE)
    assert not third.is_back_to_back


def test_consecutive_clears_build_a_combo():
    scorer = Scorer(use_guideline=True)
    scorer.register_lock(1, SpinType.NONE)
    second = scorer.register_lock(1, SpinType.NONE)
    assert second.combo == 1
    assert second.points > GUIDELINE_LINE_SCORES[1] * scorer.level - 1


def test_a_lock_without_a_clear_resets_the_combo():
    scorer = Scorer(use_guideline=True)
    scorer.register_lock(1, SpinType.NONE)
    scorer.register_lock(0, SpinType.NONE)
    assert scorer.combo == -1


def test_classic_scoring_has_no_combos_or_drop_points():
    """Those are Guideline inventions; classic keeps to its table."""
    scorer = Scorer(use_guideline=False)
    scorer.register_lock(1, SpinType.NONE)
    before = scorer.score
    scorer.add_drop_points(20, hard=True)
    assert scorer.score == before


def test_hard_drops_pay_more_per_row_than_soft_drops():
    hard = Scorer(use_guideline=True)
    soft = Scorer(use_guideline=True)
    hard.add_drop_points(10, hard=True)
    soft.add_drop_points(10, hard=False)
    assert hard.score > soft.score


# ----------------------------------------------------------------------
# Event descriptions
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("event", "expected"),
    [
        (ScoreEvent(lines=4), "TETRIS"),
        (ScoreEvent(lines=1), "SINGLE"),
        (ScoreEvent(lines=2, spin=SpinType.FULL), "T-SPIN DOUBLE"),
        (ScoreEvent(lines=1, spin=SpinType.MINI), "T-SPIN MINI SINGLE"),
        (ScoreEvent(lines=4, is_back_to_back=True), "TETRIS B2B"),
        (ScoreEvent(lines=1, combo=3), "SINGLE COMBO x3"),
    ],
)
def test_events_describe_themselves(event, expected):
    assert event.describe() == expected


def test_an_empty_event_says_nothing():
    assert ScoreEvent().describe() == ""
