"""The Super Rotation System: how a rotation is allowed to cheat.

Classic rotation is honest and unforgiving — turn the piece, and if it
overlaps anything, nothing happens. SRS is generous instead. When the
straightforward rotation fails, it tries the piece shifted slightly: up,
down, left, right, in a specific order. The first offset that fits wins.
Those shifts are the "wall kicks", and they are why a modern player can
spin a piece into a slot that looks too tight, or stand an I piece up
while it is flush against the wall.

The numbers below are not derived from geometry. SRS rotates pieces
around origins that were chosen by hand in the 1990s because they felt
right, and the kick sequences follow from those choices. They are data,
copied faithfully from the specification — the same lesson as the CHIP-8
quirks: some behaviour is history, not mathematics.

Two tables exist because the I piece is four cells long and needs to
travel further than the others to clear an obstacle. The O piece is
absent: a square looks identical in every rotation, so it never kicks.

Coordinate note: the published tables use (x, y) with y pointing UP.
This project indexes rows downward, so every y is negated on the way in.
"""

from __future__ import annotations

from tetris.core.piece import Piece

# (from_rotation, to_rotation) -> five (drow, dcol) candidates.
# The first candidate is always (0, 0): the plain rotation, no kick.
JLSTZ_KICKS: dict[tuple[int, int], list[tuple[int, int]]] = {
    (0, 1): [(0, 0), (0, -1), (-1, -1), (2, 0), (2, -1)],
    (1, 0): [(0, 0), (0, 1), (1, 1), (-2, 0), (-2, 1)],
    (1, 2): [(0, 0), (0, 1), (1, 1), (-2, 0), (-2, 1)],
    (2, 1): [(0, 0), (0, -1), (-1, -1), (2, 0), (2, -1)],
    (2, 3): [(0, 0), (0, 1), (-1, 1), (2, 0), (2, 1)],
    (3, 2): [(0, 0), (0, -1), (1, -1), (-2, 0), (-2, -1)],
    (3, 0): [(0, 0), (0, -1), (1, -1), (-2, 0), (-2, -1)],
    (0, 3): [(0, 0), (0, 1), (-1, 1), (2, 0), (2, 1)],
}

I_KICKS: dict[tuple[int, int], list[tuple[int, int]]] = {
    (0, 1): [(0, 0), (0, -2), (0, 1), (1, -2), (-2, 1)],
    (1, 0): [(0, 0), (0, 2), (0, -1), (-1, 2), (2, -1)],
    (1, 2): [(0, 0), (0, -1), (0, 2), (-2, -1), (1, 2)],
    (2, 1): [(0, 0), (0, 1), (0, -2), (2, 1), (-1, -2)],
    (2, 3): [(0, 0), (0, 2), (0, -1), (-1, 2), (2, -1)],
    (3, 2): [(0, 0), (0, -2), (0, 1), (1, -2), (-2, 1)],
    (3, 0): [(0, 0), (0, 1), (0, -2), (2, 1), (-1, -2)],
    (0, 3): [(0, 0), (0, -1), (0, 2), (-2, -1), (1, 2)],
}

NO_KICKS: list[tuple[int, int]] = [(0, 0)]


def kick_candidates(
    kind: str, from_rotation: int, to_rotation: int
) -> list[tuple[int, int]]:
    """The offsets to try, in order, for this particular rotation."""
    if kind == "O":
        return NO_KICKS  # a square never needs to move to turn
    table = I_KICKS if kind == "I" else JLSTZ_KICKS
    return table.get((from_rotation, to_rotation), NO_KICKS)


def rotate_with_kicks(piece: Piece, steps: int, fits) -> tuple[Piece, int] | None:
    """Attempts an SRS rotation, returning the accepted piece and which
    kick index succeeded — or None if every candidate was blocked.

    `fits` is a predicate (usually `board.can_place`), so this function
    stays independent of the board: it is pure rotation logic that can be
    tested against any notion of "does this position work?".

    The returned kick index matters beyond debugging: a T piece that locks
    after a rotation whose kick index was the last one is the classic
    signature of a T-spin, which Phase 5 scores separately.
    """
    rotated = piece.rotated(steps)
    candidates = kick_candidates(piece.kind, piece.rotation, rotated.rotation)

    for index, (drow, dcol) in enumerate(candidates):
        attempt = rotated.moved(drow, dcol)
        if fits(attempt):
            return attempt, index
    return None


def rotate_classic(piece: Piece, steps: int, fits) -> tuple[Piece, int] | None:
    """Classic rotation: the plain turn, or nothing at all."""
    rotated = piece.rotated(steps)
    if fits(rotated):
        return rotated, 0
    return None
