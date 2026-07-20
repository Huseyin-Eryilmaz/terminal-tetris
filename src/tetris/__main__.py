"""Entry point: the frame loop that will host the game.

Phase 0 proves the shell works end to end — a fixed-rate loop, a drawn
well, and live keyboard echo — without any game logic behind it yet.
"""

from __future__ import annotations

import time

from tetris.core.constants import (
    BOARD_VISIBLE_HEIGHT,
    BOARD_WIDTH,
    FRAMES_PER_SECOND,
)
from tetris.ui.input import Key, KeyReader
from tetris.ui.renderer import COLORS, EMPTY, Screen, colored, frame_box

FRAME_DURATION = 1 / FRAMES_PER_SECOND


def build_frame(last_keys: list[Key], frame_count: int) -> list[str]:
    """Assembles the Phase 0 test picture: an empty well plus diagnostics."""
    well = frame_box(BOARD_WIDTH * 2, BOARD_VISIBLE_HEIGHT, title="TETRIS")

    # Fill the inside of the box with the empty-cell pattern.
    for row in range(1, BOARD_VISIBLE_HEIGHT + 1):
        cells = colored(EMPTY * BOARD_WIDTH, COLORS["ghost"])
        border = colored("│", COLORS["frame"])
        well[row] = border + cells + border

    keys_text = " ".join(key.name for key in last_keys) if last_keys else "-"
    return [
        "",
        *well,
        "",
        colored(f"  frame {frame_count}", COLORS["text"]),
        colored(f"  keys  {keys_text}", COLORS["accent"]),
        colored("  Q to quit", COLORS["text"]),
    ]


def main() -> None:
    frame_count = 0
    last_keys: list[Key] = []

    with Screen() as screen, KeyReader() as keyboard:
        running = True
        while running:
            frame_start = time.perf_counter()

            keys = keyboard.read()
            if keys:
                last_keys = keys
            if Key.Q in keys or Key.ESCAPE in keys:
                running = False

            frame_count += 1
            screen.draw(build_frame(last_keys, frame_count))

            # Fixed-rate loop: sleep off whatever is left of the frame's
            # budget, so the game runs at the same speed on any machine.
            elapsed = time.perf_counter() - frame_start
            if (remaining := FRAME_DURATION - elapsed) > 0:
                time.sleep(remaining)


if __name__ == "__main__":
    main()
