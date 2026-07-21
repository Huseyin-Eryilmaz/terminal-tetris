"""Where the next piece comes from.

The obvious way to pick a tetromino is at random, and that is what the
1984 original did. It has a flaw players feel long before they can name
it: randomness clumps. Four S pieces in a row is unremarkable to a coin
flip and infuriating to a person, and a drought of I pieces can end a
game through no fault of the player.

The 7-bag generator fixes this without making the game predictable. Put
one of each tetromino in a bag, shuffle, deal all seven, refill. You can
never go more than twelve pieces without an I (worst case: it comes
first in one bag and last in the next), yet the order inside each bag is
still a surprise. Modern Tetris is built on this guarantee — planning
ahead only works if the future is bounded.

Both generators hide behind the same `next_piece()` call, so the game
never asks which one it is using.
"""

from __future__ import annotations

import random
from collections import deque

from tetris.core.piece import PIECE_TYPES


class PieceGenerator:
    """Common interface: hand out piece kinds, one at a time."""

    def next_piece(self) -> str:
        raise NotImplementedError


class RandomGenerator(PieceGenerator):
    """Classic behaviour: each piece is an independent random draw."""

    def __init__(self, rng: random.Random) -> None:
        self._rng = rng

    def next_piece(self) -> str:
        return self._rng.choice(PIECE_TYPES)


class BagGenerator(PieceGenerator):
    """Modern behaviour: deal a shuffled bag of all seven, then refill."""

    def __init__(self, rng: random.Random) -> None:
        self._rng = rng
        self._bag: deque[str] = deque()

    def _refill(self) -> None:
        pieces = list(PIECE_TYPES)
        self._rng.shuffle(pieces)
        self._bag.extend(pieces)

    def next_piece(self) -> str:
        if not self._bag:
            self._refill()
        return self._bag.popleft()


def make_generator(use_bag: bool, rng: random.Random) -> PieceGenerator:
    return BagGenerator(rng) if use_bag else RandomGenerator(rng)


class PieceQueue:
    """A generator plus a peekable window of upcoming pieces.

    The queue is always kept one longer than the player can see, so
    `pop()` never has to reach into the generator mid-frame — the preview
    the player is looking at is exactly what they will get.
    """

    def __init__(self, generator: PieceGenerator, preview_size: int) -> None:
        self._generator = generator
        self._preview_size = preview_size
        self._queue: deque[str] = deque()
        self._fill()

    def _fill(self) -> None:
        while len(self._queue) <= self._preview_size:
            self._queue.append(self._generator.next_piece())

    def pop(self) -> str:
        kind = self._queue.popleft()
        self._fill()
        return kind

    def preview(self) -> list[str]:
        """The next pieces, as many as this rule set shows."""
        return list(self._queue)[: self._preview_size]
