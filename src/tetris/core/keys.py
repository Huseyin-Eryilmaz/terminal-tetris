"""The inputs the game understands, independent of any keyboard.

This lives in `core` rather than `ui` because it is a game concept, not a
terminal one: the rules care that the player asked to rotate, not that a
particular byte arrived on stdin. Keeping it here lets the app state
machine stay free of UI imports — and would let a different frontend
(a GUI, a network client) drive the same game.
"""

from __future__ import annotations

from enum import Enum, auto


class Key(Enum):
    """Every input the game understands, independent of platform encoding."""

    LEFT = auto()
    RIGHT = auto()
    UP = auto()
    DOWN = auto()
    SPACE = auto()
    ENTER = auto()
    ESCAPE = auto()
    Z = auto()
    X = auto()
    C = auto()
    P = auto()
    Q = auto()
    R = auto()

    # Digits, for menu selection.
    D1 = auto()
    D2 = auto()
    D3 = auto()
    D4 = auto()
