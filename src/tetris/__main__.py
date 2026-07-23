"""Entry point: the frame loop.

Everything it does is plumbing. Keys go to the app state machine, elapsed
time goes to the app, and whatever the app is showing gets drawn. All the
decisions — which screen, which rules, what a key means — live elsewhere.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time

from tetris.core.app import App, Screen
from tetris.core.constants import FRAMES_PER_SECOND
from tetris.ui.input import KeyReader
from tetris.ui.renderer import Screen as Terminal
from tetris.ui.screens import render

FRAME_DURATION = 1 / FRAMES_PER_SECOND

# The tallest screen (playing: field + HUD) needs roughly this many rows.
REQUIRED_ROWS = 32


def _check_terminal_size() -> bool:
    """Warns and refuses to start if the window is too short.

    Drawing a frame taller than the terminal makes it scroll, and once it
    scrolls, "cursor home" no longer points at the top of the frame — every
    subsequent frame lands below the last one. Better to say so plainly
    than to render a broken screen.
    """
    rows = shutil.get_terminal_size(fallback=(80, 24)).lines
    if rows >= REQUIRED_ROWS:
        return True
    print(
        f"This game needs a terminal at least {REQUIRED_ROWS} rows tall; "
        f"this one is {rows}.\nPlease make the window taller and try again."
    )
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Tetris in the terminal")
    parser.add_argument(
        "--mode",
        choices=["classic", "modern"],
        help="skip the menu and start this mode straight away",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="fixed piece sequence, for reproducible games",
    )
    args = parser.parse_args()

    if not _check_terminal_size():
        sys.exit(1)

    app = App(seed=args.seed)
    if args.mode:
        app.start_game(args.mode)

    with Terminal() as terminal, KeyReader() as keyboard:
        previous = time.perf_counter()

        while app.is_running:
            frame_start = time.perf_counter()
            dt = frame_start - previous
            previous = frame_start

            app.handle_keys(keyboard.read())
            app.tick(dt)

            if app.screen is not Screen.QUIT:
                terminal.draw(render(app))

            elapsed = time.perf_counter() - frame_start
            if (remaining := FRAME_DURATION - elapsed) > 0:
                time.sleep(remaining)


if __name__ == "__main__":
    main()
