"""Screen rendering: the drawn piece previews and the composed layout.

Colour escapes are stripped before asserting, so the tests read as if
they were looking at the terminal.
"""

import re

import pytest

from tetris.core.app import App
from tetris.core.constants import BOARD_VISIBLE_HEIGHT
from tetris.core.piece import PIECE_TYPES
from tetris.ui.screens import (
    _labelled_box,
    _side_by_side,
    piece_rows,
    render,
    render_game_over,
    render_playing,
    render_side_panel,
)


def plain(lines: list[str]) -> list[str]:
    return [re.sub(r"\x1b\[[0-9;?]*[a-zA-Z]", "", line) for line in lines]


# ----------------------------------------------------------------------
# Drawn pieces
# ----------------------------------------------------------------------
@pytest.mark.parametrize("kind", PIECE_TYPES)
def test_every_piece_draws_four_blocks(kind):
    """A tetromino is four cells; the drawing must not lose or add any."""
    drawn = "".join(plain(piece_rows(kind)))
    assert drawn.count("█") == 8  # two characters per cell


@pytest.mark.parametrize("kind", PIECE_TYPES)
def test_preview_rows_are_a_fixed_width(kind):
    """Every preview occupies the same box, whatever the piece's shape,
    so the panel's border stays straight."""
    for row in plain(piece_rows(kind)):
        assert len(row) == 8


def test_the_flat_i_is_drawn_as_a_single_row():
    """Empty rows are trimmed: an I in its spawn shape is one line, not
    four with three blanks."""
    assert len(piece_rows("I")) == 1


def test_the_o_piece_is_centred():
    rows = plain(piece_rows("O"))
    assert rows[0] == "  ████  "


# ----------------------------------------------------------------------
# Panel composition
# ----------------------------------------------------------------------
def test_a_labelled_box_shows_its_title_and_closes():
    box = plain(_labelled_box("NEXT", ["O"]))
    assert "NEXT" in box[0]
    assert box[0].startswith("┌") and box[0].endswith("┐")
    assert box[-1].startswith("└") and box[-1].endswith("┘")


def test_an_empty_box_still_has_a_body():
    box = plain(_labelled_box("HOLD", []))
    assert len(box) >= 3  # top, one blank row, bottom


def test_side_by_side_pads_the_shorter_block():
    joined = _side_by_side(["a", "b", "c"], ["x"])
    assert len(joined) == 3
    assert joined[0].startswith("a")
    assert "x" in joined[0]


# ----------------------------------------------------------------------
# Whole screens
# ----------------------------------------------------------------------
@pytest.fixture()
def playing() -> App:
    app = App(seed=5)
    app.start_game("modern")
    return app


def test_the_playing_screen_shows_the_field_and_the_panel(playing):
    lines = plain(render_playing(playing))
    assert any("TETRIS" in line for line in lines)
    assert any("NEXT" in line for line in lines)
    assert any("HOLD" in line for line in lines)


def test_the_field_still_has_twenty_visible_rows(playing):
    lines = plain(render_playing(playing))
    field = [line for line in lines if line.startswith("│")]
    assert len(field) == BOARD_VISIBLE_HEIGHT


def test_classic_mode_has_no_hold_box():
    app = App(seed=5)
    app.start_game("classic")
    assert app.game is not None
    lines = plain(render_side_panel(app.game))
    assert any("NEXT" in line for line in lines)
    assert not any("HOLD" in line for line in lines)


def test_the_panel_previews_as_many_pieces_as_the_rules_allow(playing):
    lines = plain(render_side_panel(playing.game))
    drawn_rows = [line for line in lines if "█" in line]
    assert len(drawn_rows) >= playing.rules.next_queue_size


def test_the_game_over_screen_is_shorter_than_the_playing_screen(playing, monkeypatch):
    """The reason the renderer must erase below the frame: switching to a
    much shorter screen would otherwise leave the old field on display."""
    monkeypatch.setattr("tetris.core.app.record_score", lambda *a, **k: ([], None))
    playing_lines = render_playing(playing)

    playing._finish_game()
    over_lines = render_game_over(playing)

    assert len(over_lines) < len(playing_lines)


def test_render_dispatches_to_the_current_screen(playing):
    assert any("NEXT" in line for line in plain(render(playing)))
