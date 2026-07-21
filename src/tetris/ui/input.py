"""Non-blocking keyboard input, one interface over two very different worlds.

A game loop must never stop to wait for a keystroke: it has to keep falling
pieces, ticking timers and redrawing at a steady rate whether the player
touches the keyboard or not. Python's built-in `input()` is the opposite of
that — it blocks until Enter.

So each platform gets its own reader, hidden behind `KeyReader.read()`,
which answers one question: "which keys arrived since I last asked?"

- Windows: `msvcrt.kbhit()` tells us whether a keystroke is waiting; we
  drain them all with `getch()`.
- Unix: the terminal normally hands over input line by line, with echo.
  We switch it to "cbreak" mode (raw, no echo, no line buffering) and use
  `select()` with a zero timeout to poll without blocking.

Arrow keys are the awkward part: they aren't characters. Windows sends a
two-byte sequence (0x00 or 0xE0, then a code); Unix sends an ANSI escape
sequence (ESC [ A). Both are decoded into the same `Key` enum here, so the
rest of the game never learns which OS it is on.
"""

# pyright: reportAttributeAccessIssue=false

from __future__ import annotations

import sys
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


_CHAR_KEYS = {
    " ": Key.SPACE,
    "\r": Key.ENTER,
    "\n": Key.ENTER,
    "z": Key.Z,
    "x": Key.X,
    "c": Key.C,
    "p": Key.P,
    "q": Key.Q,
    "r": Key.R,
    "1": Key.D1,
    "2": Key.D2,
    "3": Key.D3,
    "4": Key.D4,
}

# Windows: arrows arrive as a prefix byte followed by a code byte.
_WINDOWS_ARROWS = {
    "H": Key.UP,
    "P": Key.DOWN,
    "K": Key.LEFT,
    "M": Key.RIGHT,
}

# Unix: arrows arrive as ESC [ <letter>.
_ANSI_ARROWS = {
    "A": Key.UP,
    "B": Key.DOWN,
    "C": Key.RIGHT,
    "D": Key.LEFT,
}


class KeyReader:
    """Polls the keyboard without blocking. Use as a context manager.

    On Unix the terminal mode must be restored on exit — including when the
    game crashes — or the player is left with a shell that doesn't echo
    what they type. The `with` block guarantees that.
    """

    def __init__(self) -> None:
        self._is_windows = sys.platform == "win32"
        self._fd: int | None = None
        self._original_mode: list | None = None

    def __enter__(self) -> KeyReader:
        if not self._is_windows:
            import termios
            import tty

            fd = sys.stdin.fileno()
            self._original_mode = termios.tcgetattr(fd)
            tty.setcbreak(fd)
            self._fd = fd
        return self

    def __exit__(self, *exc_info: object) -> None:
        if self._is_windows or self._fd is None or self._original_mode is None:
            return

        import termios

        termios.tcsetattr(self._fd, termios.TCSADRAIN, self._original_mode)

    def read(self) -> list[Key]:
        """Returns every key pressed since the last call (possibly empty)."""
        if self._is_windows:
            return self._read_windows()
        return self._read_unix()

    def _read_windows(self) -> list[Key]:
        import msvcrt

        keys: list[Key] = []
        while msvcrt.kbhit():
            char = msvcrt.getwch()
            if char in ("\x00", "\xe0"):  # arrow-key prefix
                if msvcrt.kbhit():
                    code = msvcrt.getwch()
                    if arrow := _WINDOWS_ARROWS.get(code):
                        keys.append(arrow)
                continue
            if char == "\x1b":
                keys.append(Key.ESCAPE)
                continue
            if key := _CHAR_KEYS.get(char.lower()):
                keys.append(key)
        return keys

    def _read_unix(self) -> list[Key]:
        import select

        keys: list[Key] = []
        while select.select([sys.stdin], [], [], 0)[0]:
            char = sys.stdin.read(1)
            if char == "\x1b":
                # Either a bare ESC, or the start of an arrow sequence.
                if not select.select([sys.stdin], [], [], 0)[0]:
                    keys.append(Key.ESCAPE)
                    continue
                bracket = sys.stdin.read(1)
                if bracket != "[":
                    keys.append(Key.ESCAPE)
                    continue
                code = sys.stdin.read(1)
                if arrow := _ANSI_ARROWS.get(code):
                    keys.append(arrow)
                continue
            if key := _CHAR_KEYS.get(char.lower()):
                keys.append(key)
        return keys
