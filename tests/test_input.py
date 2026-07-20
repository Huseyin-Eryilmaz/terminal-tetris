"""Tests for the platform-agnostic key decoding tables.

The readers themselves need a real terminal, so what is tested here is the
part that must not drift: that both platforms' encodings map onto the same
Key enum, and that every key the game uses has a decoding.
"""

from tetris.ui.input import _ANSI_ARROWS, _CHAR_KEYS, _WINDOWS_ARROWS, Key


def test_both_platforms_decode_the_same_four_arrows():
    assert set(_WINDOWS_ARROWS.values()) == set(_ANSI_ARROWS.values())
    assert set(_ANSI_ARROWS.values()) == {Key.UP, Key.DOWN, Key.LEFT, Key.RIGHT}


def test_char_table_covers_the_gameplay_keys():
    expected = {Key.SPACE, Key.ENTER, Key.Z, Key.X, Key.C, Key.P, Key.Q, Key.R}
    assert expected <= set(_CHAR_KEYS.values())


def test_menu_digits_are_decoded():
    assert _CHAR_KEYS["1"] is Key.D1
    assert _CHAR_KEYS["4"] is Key.D4


def test_char_keys_are_lowercase_only():
    """read() lowercases input before lookup, so uppercase entries would be
    dead weight — and a silent source of 'why doesn't X work?' bugs."""
    assert all(char == char.lower() for char in _CHAR_KEYS)
