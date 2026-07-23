"""Drawing to a terminal with nothing but escape codes.

A terminal is a stream of text, not a canvas — so "drawing" means printing
control sequences that a terminal emulator interprets: move the cursor,
change colour, clear the screen. They all start with ESC [ (`\\033[`).

Two techniques keep the picture stable:

1. **No clear-and-redraw.** Wiping the screen every frame makes it flicker,
   because for a moment there is nothing there. Instead the cursor is sent
   home (`\\033[H`) and the new frame is printed over the old one.
2. **One write per frame.** The whole frame is assembled in a list of
   strings and pushed out with a single `sys.stdout.write`. Many small
   prints let the terminal display a half-finished frame; one big write
   arrives as one piece.

Blocks are drawn as two characters wide ("██"), because terminal cells are
roughly twice as tall as they are wide — a "square" made of one cell would
look like a squashed rectangle.
"""

from __future__ import annotations

import shutil
import sys

ESC = "\033["

# Cursor and screen control.
CURSOR_HOME = f"{ESC}H"
CLEAR_SCREEN = f"{ESC}2J"
HIDE_CURSOR = f"{ESC}?25l"
SHOW_CURSOR = f"{ESC}?25h"
RESET = f"{ESC}0m"

# 256-colour palette entries, one per tetromino, plus UI shades.
COLORS = {
    "I": 51,  # cyan
    "O": 226,  # yellow
    "T": 129,  # purple
    "S": 46,  # green
    "Z": 196,  # red
    "J": 33,  # blue
    "L": 208,  # orange
    "ghost": 240,  # dim grey
    "frame": 244,
    "text": 250,
    "accent": 214,
}

BLOCK = "██"
EMPTY = " ."


def fg(color: int) -> str:
    """Foreground colour escape from the 256-colour palette."""
    return f"{ESC}38;5;{color}m"


def colored(text: str, color: int) -> str:
    return f"{fg(color)}{text}{RESET}"


class Screen:
    """Owns the terminal's state: cursor visibility, clearing, frame output."""

    def __enter__(self) -> Screen:
        sys.stdout.write(HIDE_CURSOR + CLEAR_SCREEN + CURSOR_HOME)
        sys.stdout.flush()
        return self

    def __exit__(self, *exc_info: object) -> None:
        # Always give the cursor back, even on a crash — otherwise the
        # player's shell is left with an invisible cursor.
        sys.stdout.write(SHOW_CURSOR + RESET + CLEAR_SCREEN + CURSOR_HOME)
        sys.stdout.flush()

    def draw(self, lines: list[str]) -> None:
        """Prints one frame: cursor home, then every line, in a single write.

        Two details keep the frame pinned in place:

        - Lines are separated by `\\r\\n`, not `\\n`: in cbreak mode the
          terminal does not translate a newline into a carriage return, so
          a bare `\\n` moves down a row while leaving the cursor in the
          same column.
        - The last line has no trailing newline at all. Ending a frame
          with one pushes the cursor past the bottom of the screen, the
          terminal scrolls, and "cursor home" then points somewhere above
          the frame — so the next frame lands underneath the previous one
          instead of on top of it.
        """
        height = shutil.get_terminal_size(fallback=(80, 24)).lines
        visible = lines[: height - 1]
        body = "\r\n".join(f"{line}{ESC}K" for line in visible)
        sys.stdout.write(CURSOR_HOME + body)
        sys.stdout.flush()


def frame_box(width: int, height: int, title: str = "") -> list[str]:
    """Builds a simple box of the given inner size, as a list of lines."""
    color = COLORS["frame"]
    top = colored("┌" + "─" * width + "┐", color)
    if title:
        label = f" {title} "
        top = colored("┌" + label.center(width, "─") + "┐", color)
    middle = [colored("│", color) + " " * width + colored("│", color)] * height
    bottom = colored("└" + "─" * width + "┘", color)
    return [top, *middle, bottom]
