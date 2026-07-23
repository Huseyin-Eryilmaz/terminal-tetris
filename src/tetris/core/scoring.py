"""Scoring, levels, and the art of recognising a T-spin.

Classic scoring is a small table: one line is worth a little, four at
once is worth a lot, and everything scales with the level. The lesson it
teaches is patience — clearing rows one at a time throws points away.

Guideline scoring keeps that idea and adds a second axis: *how* the rows
were cleared. A T piece rotated into a slot it could not have fallen into
scores several times what the same rows would otherwise be worth. That
one rule is why modern Tetris looks the way it does at high level — the
players are not clearing lines, they are constructing situations.

Detecting a T-spin is a rule of thumb rather than a proof. The game
cannot know what the player intended, so it checks three things:

  1. the piece is a T,
  2. the last thing that moved it was a rotation,
  3. at least three of the four corners of its 3x3 box are occupied.

If a T ends up wedged that tightly, and turned its way in, it spun. The
distinction between a full T-spin and a "mini" comes from *which* three
corners: the two corners the T's tip points between are its front, and
when both of those are filled the spin was the real thing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

from tetris.core.board import Board
from tetris.core.piece import Piece

# Classic (Nintendo-style) line values, multiplied by level.
CLASSIC_LINE_SCORES = {0: 0, 1: 40, 2: 100, 3: 300, 4: 1200}

# Guideline values, multiplied by level.
GUIDELINE_LINE_SCORES = {0: 0, 1: 100, 2: 300, 3: 500, 4: 800}
GUIDELINE_TSPIN_SCORES = {0: 400, 1: 800, 2: 1200, 3: 1600}
GUIDELINE_TSPIN_MINI_SCORES = {0: 100, 1: 200, 2: 400}

SOFT_DROP_POINTS_PER_ROW = 1
HARD_DROP_POINTS_PER_ROW = 2

LINES_PER_LEVEL = 10
MAX_LEVEL = 20


class SpinType(Enum):
    NONE = auto()
    MINI = auto()
    FULL = auto()


# The four corners of a T piece's 3x3 box, relative to its origin.
_T_CORNERS = [(0, 0), (0, 2), (2, 0), (2, 2)]

# The two corners the T's tip points between, per rotation state.
_T_FRONT_CORNERS = {
    0: [(0, 0), (0, 2)],
    1: [(0, 2), (2, 2)],
    2: [(2, 0), (2, 2)],
    3: [(0, 0), (2, 0)],
}


def detect_spin(board: Board, piece: Piece, last_move_was_rotation: bool) -> SpinType:
    """Classifies how tightly a just-locked T piece is wedged in."""
    if piece.kind != "T" or not last_move_was_rotation:
        return SpinType.NONE

    def occupied(dr: int, dc: int) -> bool:
        row, col = piece.row + dr, piece.col + dc
        if not board.is_inside(row, col):
            return True  # walls and the floor count as filled corners
        return board.is_occupied(row, col)

    filled = sum(occupied(dr, dc) for dr, dc in _T_CORNERS)
    if filled < 3:
        return SpinType.NONE

    front = _T_FRONT_CORNERS[piece.rotation]
    front_filled = sum(occupied(dr, dc) for dr, dc in front)
    return SpinType.FULL if front_filled == 2 else SpinType.MINI


@dataclass
class ScoreEvent:
    """What one locked piece earned, and why — the HUD announces it."""

    lines: int = 0
    spin: SpinType = SpinType.NONE
    points: int = 0
    is_back_to_back: bool = False
    combo: int = 0

    def describe(self) -> str:
        names = {1: "SINGLE", 2: "DOUBLE", 3: "TRIPLE", 4: "TETRIS"}
        parts: list[str] = []
        if self.spin is SpinType.FULL:
            parts.append("T-SPIN")
        elif self.spin is SpinType.MINI:
            parts.append("T-SPIN MINI")
        if self.lines:
            parts.append(names[self.lines])
        if self.is_back_to_back:
            parts.append("B2B")
        if self.combo > 0:
            parts.append(f"COMBO x{self.combo}")
        return " ".join(parts)


@dataclass
class Scorer:
    """Running score, level, and the streak state Guideline scoring needs."""

    use_guideline: bool
    score: int = 0
    level: int = 1
    lines_cleared: int = 0
    combo: int = -1
    _back_to_back: bool = field(default=False, repr=False)

    def _line_points(self, lines: int, spin: SpinType) -> int:
        if not self.use_guideline:
            return CLASSIC_LINE_SCORES[lines] * self.level

        if spin is SpinType.FULL:
            return GUIDELINE_TSPIN_SCORES[lines] * self.level
        if spin is SpinType.MINI:
            return GUIDELINE_TSPIN_MINI_SCORES.get(lines, 0) * self.level
        return GUIDELINE_LINE_SCORES[lines] * self.level

    def register_lock(self, lines: int, spin: SpinType) -> ScoreEvent:
        """Scores one locked piece and advances level and streaks."""
        event = ScoreEvent(lines=lines, spin=spin)
        points = self._line_points(lines, spin)

        if self.use_guideline:
            # A "difficult" clear is a tetris, or a T-spin that cleared.
            difficult = lines == 4 or (spin is not SpinType.NONE and lines > 0)
            if difficult and self._back_to_back:
                points = points * 3 // 2  # 1.5x for chaining difficult clears
                event.is_back_to_back = True
            if lines:
                self._back_to_back = difficult

            # Combo: consecutive locks that each clear at least one row.
            self.combo = self.combo + 1 if lines else -1
            if self.combo > 0:
                points += 50 * self.combo * self.level
                event.combo = self.combo

        self.score += points
        self.lines_cleared += lines
        self.level = min(1 + self.lines_cleared // LINES_PER_LEVEL, MAX_LEVEL)

        event.points = points
        return event

    def add_drop_points(self, rows: int, hard: bool) -> None:
        """Dropping a piece yourself is worth a little, and rewards speed."""
        if not self.use_guideline:
            return
        per_row = HARD_DROP_POINTS_PER_ROW if hard else SOFT_DROP_POINTS_PER_ROW
        self.score += rows * per_row


def gravity_interval_for_level(level: int) -> float:
    """Seconds per row at a given level.

    The curve is exponential rather than linear: subtracting a fixed
    amount per level would hit zero and stay there, while multiplying by
    a factor below one approaches zero without ever arriving. Clamped at
    the bottom so a piece is always visible for at least a few frames.
    """
    return max(1.0 * (0.8 ** (level - 1)), 0.05)
