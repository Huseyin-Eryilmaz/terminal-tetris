"""Remembering scores between sessions.

The whole store is one JSON file in the user's home directory. That is a
deliberate choice over a database: the data is a handful of numbers, it
is read once at startup and written once per game, and a file the player
can open, read, or delete is friendlier than an opaque binary.

Every read is defensive. A high score file is exactly the kind of thing
that gets hand-edited, half-written when a laptop sleeps, or copied from
an older version — and none of that should stop someone playing Tetris.
Anything unreadable is treated as "no scores yet".
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

SCORES_FILE = Path.home() / ".terminal_tetris_scores.json"
MAX_ENTRIES_PER_MODE = 5


@dataclass(frozen=True)
class HighScore:
    score: int
    lines: int
    level: int

    def as_row(self) -> str:
        return f"{self.score:>7}  {self.lines:>4} lines  lv {self.level}"


def load_scores(path: Path = SCORES_FILE) -> dict[str, list[HighScore]]:
    """Reads the score file, returning an empty table if anything is wrong."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return {
            mode: [HighScore(**entry) for entry in entries]
            for mode, entries in raw.items()
        }
    except (OSError, ValueError, TypeError):
        # Missing, unreadable, malformed, or written by another version.
        return {}


def save_scores(scores: dict[str, list[HighScore]], path: Path = SCORES_FILE) -> bool:
    """Writes the table. Returns False if the file could not be written.

    A read-only home directory is not a reason to crash after someone has
    just finished a good game — the caller can mention it and move on.
    """
    try:
        payload = {
            mode: [asdict(entry) for entry in entries]
            for mode, entries in scores.items()
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return True
    except OSError:
        return False


def record_score(
    mode: str, entry: HighScore, path: Path = SCORES_FILE
) -> tuple[list[HighScore], int | None]:
    """Adds a score to its mode's table, returning the table and the rank.

    The rank is None when the score did not make the cut, which is what
    the game-over screen uses to decide whether to celebrate.
    """
    scores = load_scores(path)
    table = scores.get(mode, [])
    table.append(entry)
    table.sort(key=lambda item: item.score, reverse=True)
    trimmed = table[:MAX_ENTRIES_PER_MODE]

    scores[mode] = trimmed
    save_scores(scores, path)

    rank = trimmed.index(entry) + 1 if entry in trimmed else None
    return trimmed, rank
