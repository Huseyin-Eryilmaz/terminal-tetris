"""Entry point: the frame loop that connects keyboard, rules and screen.

Its whole job is translation. Keys become `Action`s, elapsed time becomes
a `tick`, and game state becomes a list of strings. No rule of Tetris is
decided here — that logic lives in `core/`, which is what keeps this file
readable and the rules testable.
"""

from __future__ import annotations

import argparse
import time

from tetris.core.constants import BOARD_WIDTH, FRAMES_PER_SECOND
from tetris.core.game import Action, Game, GameState
from tetris.core.rules import RULE_SETS
from tetris.ui.input import Key, KeyReader
from tetris.ui.renderer import BLOCK, COLORS, EMPTY, Screen, colored

FRAME_DURATION = 1 / FRAMES_PER_SECOND

# Keys that map straight onto a game action.
ACTION_KEYS = {
    Key.LEFT: Action.MOVE_LEFT,
    Key.RIGHT: Action.MOVE_RIGHT,
    Key.UP: Action.ROTATE_CW,
    Key.X: Action.ROTATE_CW,
    Key.Z: Action.ROTATE_CCW,
    Key.SPACE: Action.HARD_DROP,
    Key.DOWN: Action.SOFT_DROP,
    Key.C: Action.HOLD,
}

GHOST_CELL = "░░"


def render_game(game: Game) -> list[str]:
    """Turns the game state into the lines of one frame."""
    frame_color = COLORS["frame"]
    inner_width = BOARD_WIDTH * 2
    ghost = game.ghost_cells()

    lines = [""]
    lines.append(colored("┌" + " TETRIS ".center(inner_width, "─") + "┐", frame_color))

    for row_index, row in enumerate(game.visible_cells()):
        cells = ""
        for col_index, cell in enumerate(row):
            if cell:
                cells += colored(BLOCK, COLORS[cell])
            elif (row_index, col_index) in ghost:
                cells += colored(GHOST_CELL, COLORS["ghost"])
            else:
                cells += colored(EMPTY, COLORS["ghost"])
        border = colored("│", frame_color)
        lines.append(border + cells + border)

    lines.append(colored("└" + "─" * inner_width + "┘", frame_color))
    lines.append("")

    scorer = game.scorer
    lines.append(colored(f"  MODE   {game.rules.name}", COLORS["accent"]))
    lines.append(colored(f"  SCORE  {scorer.score}", COLORS["accent"]))
    lines.append(colored(f"  LEVEL  {scorer.level}", COLORS["text"]))
    lines.append(colored(f"  LINES  {scorer.lines_cleared}", COLORS["text"]))

    if game.rules.allow_hold:
        lines.append(colored(f"  HOLD   {game.hold or '-'}", COLORS["text"]))
    lines.append(colored(f"  NEXT   {' '.join(game.queue.preview())}", COLORS["text"]))

    # The last scoring event, announced for as long as it stands.
    event = game.last_event
    headline = event.describe() if event else ""
    lines.append(colored(f"  {headline}", COLORS["accent"]) if headline else "")

    if game.state is GameState.GAME_OVER:
        lines.append(colored("  GAME OVER — R restart, Q quit", COLORS["accent"]))
    else:
        lines.append(colored("  <-/-> move   up/X rotate   Z ccw", COLORS["text"]))
        controls = "  down soft   SPACE drop   C hold   Q quit"
        lines.append(colored(controls, COLORS["text"]))
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description="Tetris in the terminal")
    parser.add_argument(
        "--mode",
        choices=sorted(RULE_SETS),
        default="modern",
        help="rule set: modern (Guideline) or classic (1984-style)",
    )
    args = parser.parse_args()
    rules = RULE_SETS[args.mode]()

    game = Game(rules=rules)

    with Screen() as screen, KeyReader() as keyboard:
        running = True
        previous = time.perf_counter()

        while running:
            frame_start = time.perf_counter()
            dt = frame_start - previous
            previous = frame_start

            keys = keyboard.read()
            if Key.Q in keys or Key.ESCAPE in keys:
                running = False
            if Key.R in keys:
                game = Game(rules=rules)

            for key in keys:
                if action := ACTION_KEYS.get(key):
                    game.apply(action)

            # Soft drop is a held key, but a terminal only reports presses,
            # never releases. So it lapses as soon as a frame arrives with
            # no DOWN in it — holding the key works because the OS repeats
            # the keystroke.
            if Key.DOWN not in keys:
                game.release_soft_drop()

            game.tick(dt)
            screen.draw(render_game(game))

            elapsed = time.perf_counter() - frame_start
            if (remaining := FRAME_DURATION - elapsed) > 0:
                time.sleep(remaining)


if __name__ == "__main__":
    main()
