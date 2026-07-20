"""Tests for the pure parts of the renderer: colour codes and box building."""

from tetris.core.constants import BOARD_WIDTH
from tetris.ui.renderer import COLORS, RESET, colored, fg, frame_box


def test_fg_builds_a_256_color_escape():
    assert fg(51) == "\033[38;5;51m"


def test_colored_wraps_and_resets():
    result = colored("hi", 200)
    assert result.startswith("\033[38;5;200m")
    assert result.endswith(RESET)
    assert "hi" in result


def test_every_tetromino_has_a_color():
    for letter in "IOTSZJL":
        assert letter in COLORS


def test_frame_box_has_expected_line_count():
    box = frame_box(BOARD_WIDTH * 2, 20)
    assert len(box) == 22  # top + 20 inner rows + bottom


def test_frame_box_title_is_embedded_in_the_top_line():
    box = frame_box(20, 5, title="TETRIS")
    assert "TETRIS" in box[0]
    assert box[0].count("┌") == 1 and box[0].count("┐") == 1
