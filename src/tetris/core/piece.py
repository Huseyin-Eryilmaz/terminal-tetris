"""The seven tetrominoes and their rotation states.

A tetromino could be stored as a grid of booleans, but this uses a much
lighter representation: a list of (row, column) offsets relative to the
piece's origin. "Where is this piece?" then becomes a handful of integer
additions, and rotation becomes a lookup rather than a matrix operation.

Each piece carries all four of its rotation states, spelled out up front.
Computing rotations on the fly is possible, but the Super Rotation System
(Phase 4) does not rotate pieces around their geometric centre — it uses
specific, historically chosen shapes for each state. Writing them out is
both simpler and more faithful than deriving them.

Coordinates: row grows downward, column grows to the right, matching the
way the board is indexed and the way a terminal draws.
"""

from __future__ import annotations

from dataclasses import dataclass

# Offsets per rotation state, indexed 0..3 (spawn, right, 180, left).
# Shapes follow the Tetris Guideline's spawn orientations.
SHAPES: dict[str, list[list[tuple[int, int]]]] = {
    "I": [
        [(1, 0), (1, 1), (1, 2), (1, 3)],
        [(0, 2), (1, 2), (2, 2), (3, 2)],
        [(2, 0), (2, 1), (2, 2), (2, 3)],
        [(0, 1), (1, 1), (2, 1), (3, 1)],
    ],
    "O": [
        [(0, 1), (0, 2), (1, 1), (1, 2)],
        [(0, 1), (0, 2), (1, 1), (1, 2)],
        [(0, 1), (0, 2), (1, 1), (1, 2)],
        [(0, 1), (0, 2), (1, 1), (1, 2)],
    ],
    "T": [
        [(0, 1), (1, 0), (1, 1), (1, 2)],
        [(0, 1), (1, 1), (1, 2), (2, 1)],
        [(1, 0), (1, 1), (1, 2), (2, 1)],
        [(0, 1), (1, 0), (1, 1), (2, 1)],
    ],
    "S": [
        [(0, 1), (0, 2), (1, 0), (1, 1)],
        [(0, 1), (1, 1), (1, 2), (2, 2)],
        [(1, 1), (1, 2), (2, 0), (2, 1)],
        [(0, 0), (1, 0), (1, 1), (2, 1)],
    ],
    "Z": [
        [(0, 0), (0, 1), (1, 1), (1, 2)],
        [(0, 2), (1, 1), (1, 2), (2, 1)],
        [(1, 0), (1, 1), (2, 1), (2, 2)],
        [(0, 1), (1, 0), (1, 1), (2, 0)],
    ],
    "J": [
        [(0, 0), (1, 0), (1, 1), (1, 2)],
        [(0, 1), (0, 2), (1, 1), (2, 1)],
        [(1, 0), (1, 1), (1, 2), (2, 2)],
        [(0, 1), (1, 1), (2, 0), (2, 1)],
    ],
    "L": [
        [(0, 2), (1, 0), (1, 1), (1, 2)],
        [(0, 1), (1, 1), (2, 1), (2, 2)],
        [(1, 0), (1, 1), (1, 2), (2, 0)],
        [(0, 0), (0, 1), (1, 1), (2, 1)],
    ],
}

PIECE_TYPES = "IOTSZJL"

ROTATION_STATES = 4


@dataclass(frozen=True)
class Piece:
    """A tetromino at a position on the board.

    Frozen on purpose: movement and rotation return *new* pieces instead of
    mutating this one. That makes "try a move, see if it fits, keep it only
    if it does" trivial — which is exactly what collision handling and wall
    kicks need — with no undo logic anywhere.
    """

    kind: str
    row: int = 0
    col: int = 0
    rotation: int = 0

    @property
    def cells(self) -> list[tuple[int, int]]:
        """Absolute board coordinates of the piece's four blocks."""
        offsets = SHAPES[self.kind][self.rotation]
        return [(self.row + dr, self.col + dc) for dr, dc in offsets]

    def moved(self, drow: int = 0, dcol: int = 0) -> Piece:
        return Piece(self.kind, self.row + drow, self.col + dcol, self.rotation)

    def rotated(self, steps: int = 1) -> Piece:
        """Rotates clockwise by `steps` quarter turns (negative = counter)."""
        new_rotation = (self.rotation + steps) % ROTATION_STATES
        return Piece(self.kind, self.row, self.col, new_rotation)