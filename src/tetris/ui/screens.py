"""Drawing each screen: the menu, the field, and everything around it.

Every function here has the same shape — state in, list of strings out —
which keeps them pure and testable. Nothing in this module writes to the
terminal; `Screen.draw` in the renderer does that, once per frame.
"""

from __future__ import annotations

from tetris.core.app import App, Screen
from tetris.core.constants import BOARD_WIDTH
from tetris.core.game import Game
from tetris.core.highscores import HighScore
from tetris.ui.renderer import BLOCK, COLORS, EMPTY, colored

GHOST_CELL = "░░"
FIELD_WIDTH = BOARD_WIDTH * 2

TITLE = [
    "  ▀█▀ █▀▀ ▀█▀ █▀█ █ █▀",
    "   █  ██▄  █  █▀▄ █ ▄█",
]


def _panel(title: str, width: int = FIELD_WIDTH) -> str:
    return colored("┌" + f" {title} ".center(width, "─") + "┐", COLORS["frame"])


def _bottom(width: int = FIELD_WIDTH) -> str:
    return colored("└" + "─" * width + "┘", COLORS["frame"])


def render_menu(app: App) -> list[str]:
    """The title screen: pick a mode, read the controls, or leave."""
    lines = [""]
    lines += [colored(row, COLORS["accent"]) for row in TITLE]
    lines.append("")
    lines.append(colored("  1   CLASSIC   1984 rules", COLORS["text"]))
    lines.append(colored("  2   MODERN    SRS, hold, ghost", COLORS["text"]))
    lines.append(colored("  3   CONTROLS", COLORS["text"]))
    lines.append(colored("  4   QUIT", COLORS["text"]))
    lines.append("")

    for mode in ("classic", "modern"):
        table = app.scores.get(mode, [])
        best = table[0].score if table else 0
        lines.append(colored(f"  best {mode:<8} {best}", COLORS["frame"]))
    return lines


def render_help() -> list[str]:
    lines = ["", colored("  CONTROLS", COLORS["accent"]), ""]
    rows = [
        ("left / right", "move"),
        ("up  or  X", "rotate clockwise"),
        ("Z", "rotate counter-clockwise"),
        ("down", "soft drop"),
        ("SPACE", "hard drop"),
        ("C", "hold piece (modern only)"),
        ("P", "pause"),
        ("ESC", "back to menu"),
        ("Q", "quit"),
    ]
    for key, description in rows:
        lines.append(colored(f"  {key:<14} {description}", COLORS["text"]))
    lines.append("")
    lines.append(colored("  ENTER to go back", COLORS["frame"]))
    return lines


def render_field(game: Game) -> list[str]:
    """The well itself, with the falling piece and its ghost composited in."""
    ghost = game.ghost_cells()
    lines = [_panel("TETRIS")]

    for row_index, row in enumerate(game.visible_cells()):
        cells = ""
        for col_index, cell in enumerate(row):
            if cell:
                cells += colored(BLOCK, COLORS[cell])
            elif (row_index, col_index) in ghost:
                cells += colored(GHOST_CELL, COLORS["ghost"])
            else:
                cells += colored(EMPTY, COLORS["ghost"])
        border = colored("│", COLORS["frame"])
        lines.append(border + cells + border)

    lines.append(_bottom())
    return lines


def render_hud(game: Game) -> list[str]:
    scorer = game.scorer
    lines = [
        colored(f"  MODE   {game.rules.name}", COLORS["accent"]),
        colored(f"  SCORE  {scorer.score}", COLORS["accent"]),
        colored(f"  LEVEL  {scorer.level}", COLORS["text"]),
        colored(f"  LINES  {scorer.lines_cleared}", COLORS["text"]),
    ]
    if game.rules.allow_hold:
        lines.append(colored(f"  HOLD   {game.hold or '-'}", COLORS["text"]))
    lines.append(colored(f"  NEXT   {' '.join(game.queue.preview())}", COLORS["text"]))

    event = game.last_event
    headline = event.describe() if event else ""
    lines.append(colored(f"  {headline}", COLORS["accent"]) if headline else "")
    return lines


def render_playing(app: App) -> list[str]:
    assert app.game is not None
    lines = [""] + render_field(app.game) + [""] + render_hud(app.game)
    lines.append(colored("  P pause   ESC menu   Q quit", COLORS["frame"]))
    return lines


def render_paused(app: App) -> list[str]:
    """The frozen field, with the pause notice replacing the controls."""
    assert app.game is not None
    lines = [""] + render_field(app.game) + [""] + render_hud(app.game)
    lines.append(colored("  PAUSED — P resume   ESC menu   Q quit", COLORS["accent"]))
    return lines


def _score_table(entries: list[HighScore], highlight: int | None) -> list[str]:
    if not entries:
        return [colored("  no scores yet", COLORS["frame"])]
    rows = []
    for index, entry in enumerate(entries, start=1):
        color = COLORS["accent"] if index == highlight else COLORS["text"]
        rows.append(colored(f"  {index}. {entry.as_row()}", color))
    return rows


def render_game_over(app: App) -> list[str]:
    assert app.game is not None
    scorer = app.game.scorer
    lines = ["", colored("  GAME OVER", COLORS["accent"]), ""]
    lines.append(colored(f"  score  {scorer.score}", COLORS["text"]))
    lines.append(colored(f"  lines  {scorer.lines_cleared}", COLORS["text"]))
    lines.append(colored(f"  level  {scorer.level}", COLORS["text"]))
    lines.append("")

    if app.last_rank:
        headline = f"  NEW HIGH SCORE — rank {app.last_rank}"
        lines.append(colored(headline, COLORS["accent"]))
    lines.append(colored(f"  BEST  {app.rules.name}", COLORS["frame"]))
    lines += _score_table(app.scores.get(app.rules.name.lower(), []), app.last_rank)

    lines.append("")
    lines.append(colored("  R play again   ENTER menu   Q quit", COLORS["frame"]))
    return lines


def render(app: App) -> list[str]:
    """Dispatches to whichever screen the app is currently showing."""
    match app.screen:
        case Screen.MENU:
            return render_menu(app)
        case Screen.HELP:
            return render_help()
        case Screen.PLAYING:
            return render_playing(app)
        case Screen.PAUSED:
            return render_paused(app)
        case Screen.GAME_OVER:
            return render_game_over(app)
        case _:
            return []
