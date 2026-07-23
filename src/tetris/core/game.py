"""The game itself: gravity, player actions, and the spawn-lock-clear cycle.

This is where the rules live, and it still knows nothing about terminals
or keyboards. It takes an `Action` (what the player wants) and a time
delta (how much time passed), and returns nothing — the caller inspects
the resulting state. That shape is what makes a game of Tetris something
you can write a test about.

The falling-piece lifecycle is a small state machine:

    spawn ──► falling ──► lock ──► clear lines ──► spawn ──► ...
                 │                                    │
                 └────────── top out ◄────────────────┘

Timing note: gravity is measured in seconds, not frames. Tying it to
frames would mean the game runs at different speeds on machines that
can't keep up — and at high levels, a piece needs to fall faster than
one row per frame anyway.
"""

from __future__ import annotations

import random
from enum import Enum, auto

from tetris.core.bag import PieceQueue, make_generator
from tetris.core.board import Board
from tetris.core.constants import BOARD_HIDDEN_ROWS, BOARD_WIDTH
from tetris.core.piece import Piece
from tetris.core.rotation import rotate_classic, rotate_with_kicks
from tetris.core.rules import RuleSet
from tetris.core.scoring import (
    ScoreEvent,
    Scorer,
    SpinType,
    detect_spin,
    gravity_interval_for_level,
)


class Action(Enum):
    """What the player asked for this frame."""

    MOVE_LEFT = auto()
    MOVE_RIGHT = auto()
    ROTATE_CW = auto()
    ROTATE_CCW = auto()
    SOFT_DROP = auto()
    HARD_DROP = auto()
    HOLD = auto()


class GameState(Enum):
    PLAYING = auto()
    GAME_OVER = auto()


# Seconds per row at level 1, before the level curve takes over.
DEFAULT_GRAVITY_INTERVAL = 1.0

# Soft drop falls this many times faster than normal gravity.
SOFT_DROP_MULTIPLIER = 20


class Game:
    """A single game in progress."""

    def __init__(self, rules: RuleSet | None = None, seed: int | None = None) -> None:
        # Seeded RNG: a given seed replays the exact same sequence of
        # pieces, which makes bugs reproducible and tests deterministic.
        self.rng = random.Random(seed)
        self.rules = rules if rules is not None else RuleSet.modern()

        self.board = Board()
        self.state = GameState.PLAYING
        self.lines_cleared = 0
        self.pieces_placed = 0

        self.scorer = Scorer(use_guideline=self.rules.use_srs)
        self.last_event: ScoreEvent | None = None

        # Hold: a piece parked for later. `_hold_used` enforces the rule
        # that you may only swap once per piece — without it, holding
        # repeatedly would let a player cycle the queue for free.
        self.hold: str | None = None
        self._hold_used = False

        self.queue = PieceQueue(
            make_generator(self.rules.use_bag_randomizer, self.rng),
            preview_size=self.rules.next_queue_size,
        )

        self.gravity_interval = DEFAULT_GRAVITY_INTERVAL
        self._fall_timer = 0.0
        self._soft_dropping = False

        # Lock delay bookkeeping. `_lock_timer` counts up while the piece
        # rests on something; `_lock_resets` caps how often the player may
        # restart that countdown by nudging the piece.
        self._lock_timer = 0.0
        self._lock_resets = 0

        # T-spin detection needs to know how the piece arrived at its
        # final position: only a rotation can produce a spin.
        self.last_action_was_rotation = False
        self.last_kick_index = 0

        self.current: Piece = self._spawn_piece()

    # ------------------------------------------------------------------
    # Piece lifecycle
    # ------------------------------------------------------------------
    def _next_kind(self) -> str:
        """Which tetromino comes next, according to this rule set."""
        return self.queue.pop()

    def _spawn_piece(self, kind: str | None = None) -> Piece:
        """Places a new piece in the hidden rows, horizontally centred.

        Spawning above the visible field gives the player a moment of
        warning: the piece slides into view rather than appearing on top
        of the stack. An explicit `kind` bypasses the queue, which is how
        a held piece comes back.
        """
        if kind is None:
            kind = self._next_kind()
        col = (BOARD_WIDTH - 4) // 2
        return Piece(kind, row=0, col=col)

    def _reset_piece_state(self) -> None:
        """Clears the per-piece timers and flags."""
        self._fall_timer = 0.0
        self._lock_timer = 0.0
        self._lock_resets = 0
        self.last_action_was_rotation = False
        self.last_kick_index = 0

    def _lock_current(self) -> None:
        """Freezes the piece, clears full rows, and brings in the next one.

        Top-out is checked *after* spawning: the game ends when a freshly
        spawned piece has nowhere to go, which is the moment the player
        actually loses control — not when blocks merely reach high.
        """
        # The spin must be judged before the rows disappear: clearing
        # lines changes the very corners the detection looks at.
        spin = (
            detect_spin(self.board, self.current, self.last_action_was_rotation)
            if self.rules.use_srs
            else SpinType.NONE
        )

        self.board.lock(self.current)
        self.pieces_placed += 1

        cleared = self.board.clear_lines()
        self.lines_cleared += len(cleared)

        self.last_event = self.scorer.register_lock(len(cleared), spin)
        self.gravity_interval = gravity_interval_for_level(self.scorer.level)

        self.current = self._spawn_piece()
        self._reset_piece_state()
        self._hold_used = False

        if not self.board.can_place(self.current):
            self.state = GameState.GAME_OVER

    def _try_hold(self) -> bool:
        """Swaps the current piece with the held one — once per piece.

        With an empty hold slot the current piece is stashed and the next
        one arrives; otherwise the two trade places. Either way the new
        piece starts at spawn position: holding is not a way to teleport
        a piece you have already manoeuvred into place.
        """
        if not self.rules.allow_hold or self._hold_used:
            return False

        stashed = self.hold
        self.hold = self.current.kind
        self.current = self._spawn_piece(stashed) if stashed else self._spawn_piece()
        self._hold_used = True
        self._reset_piece_state()

        if not self.board.can_place(self.current):
            self.state = GameState.GAME_OVER
        return True

    # ------------------------------------------------------------------
    # Movement primitives
    # ------------------------------------------------------------------
    def _try_move(self, drow: int = 0, dcol: int = 0) -> bool:
        """Moves the piece if the target position is free. Returns success.

        Every movement funnels through here, so "can it go there?" is asked
        in exactly one place — and because pieces are immutable, a failed
        attempt costs nothing and leaves no mess to undo.
        """
        candidate = self.current.moved(drow, dcol)
        if self.board.can_place(candidate):
            self.current = candidate
            self.last_action_was_rotation = False
            self._on_piece_moved()
            return True
        return False

    def _try_rotate(self, steps: int) -> bool:
        """Rotates the piece according to the active rotation system."""
        rotate = rotate_with_kicks if self.rules.use_srs else rotate_classic
        result = rotate(self.current, steps, self.board.can_place)
        if result is None:
            return False

        self.current, self.last_kick_index = result
        self.last_action_was_rotation = True
        self._on_piece_moved()
        return True

    def _on_piece_moved(self) -> None:
        """Restarts the lock countdown after a successful move.

        This is what makes modern Tetris forgiving: a piece resting on the
        stack can still be slid or spun into place. The reset only counts
        while the piece is actually grounded, and only `max_lock_resets`
        times — otherwise spinning in place would postpone locking forever.
        """
        if self.rules.lock_delay <= 0 or not self._is_grounded():
            return
        if self._lock_resets < self.rules.max_lock_resets:
            self._lock_resets += 1
            self._lock_timer = 0.0

    def _is_grounded(self) -> bool:
        """Is the piece resting on the stack or the floor right now?"""
        return not self.board.can_place(self.current.moved(drow=1))

    def ghost_position(self) -> Piece:
        """Where the current piece would land if dropped right now."""
        ghost = self.current
        while self.board.can_place(ghost.moved(drow=1)):
            ghost = ghost.moved(drow=1)
        return ghost

    # ------------------------------------------------------------------
    # Player actions
    # ------------------------------------------------------------------
    def apply(self, action: Action) -> None:
        """Handles one player action. Ignored once the game is over."""
        if self.state is not GameState.PLAYING:
            return

        match action:
            case Action.MOVE_LEFT:
                self._try_move(dcol=-1)
            case Action.MOVE_RIGHT:
                self._try_move(dcol=1)
            case Action.ROTATE_CW:
                self._try_rotate(1)
            case Action.ROTATE_CCW:
                self._try_rotate(-1)
            case Action.SOFT_DROP:
                # Soft drop is a *state*, not a one-shot move: it stays on
                # while the key is held and speeds up gravity.
                self._soft_dropping = True
            case Action.HARD_DROP:
                landing = self.ghost_position()
                self.scorer.add_drop_points(landing.row - self.current.row, hard=True)
                self.current = landing
                self._lock_current()
            case Action.HOLD:
                self._try_hold()

    def release_soft_drop(self) -> None:
        self._soft_dropping = False

    # ------------------------------------------------------------------
    # Time
    # ------------------------------------------------------------------
    def tick(self, dt: float) -> None:
        """Advances the game by `dt` seconds.

        The fall timer accumulates elapsed time and fires whenever it
        crosses the interval. A `while` loop rather than an `if`: if a
        frame runs long (or gravity is very fast), the piece must fall
        every row it owes, not just one.
        """
        if self.state is not GameState.PLAYING:
            return

        # A grounded piece is on the lock clock, not the fall clock.
        if self._is_grounded():
            if self.rules.lock_delay <= 0:
                self._lock_current()  # classic: lands and sticks at once
                return
            self._lock_timer += dt
            if self._lock_timer >= self.rules.lock_delay:
                self._lock_current()
            return

        # Airborne: reset the lock clock so a piece that slides off an
        # edge gets its full delay back when it lands again.
        self._lock_timer = 0.0

        interval = self.gravity_interval
        if self._soft_dropping:
            interval /= SOFT_DROP_MULTIPLIER

        self._fall_timer += dt
        while self._fall_timer >= interval:
            self._fall_timer -= interval
            if not self._try_move(drow=1):
                return  # landed; the lock clock takes over next tick
            if self._soft_dropping:
                self.scorer.add_drop_points(1, hard=False)

    # ------------------------------------------------------------------
    # Rendering support
    # ------------------------------------------------------------------
    def ghost_cells(self) -> set[tuple[int, int]]:
        """Visible-field coordinates of the landing preview, if enabled."""
        if not self.rules.show_ghost:
            return set()
        ghost = self.ghost_position()
        if ghost == self.current:
            return set()  # already resting: no point drawing a shadow
        return {
            (row - BOARD_HIDDEN_ROWS, col)
            for row, col in ghost.cells
            if row >= BOARD_HIDDEN_ROWS
        }

    def visible_cells(self) -> list[list[str | None]]:
        """The visible field with the current piece composited in.

        Returns a fresh grid rather than drawing onto the board, keeping
        the falling piece out of the locked-block state entirely.
        """
        rows = [row.copy() for row in self.board.grid[BOARD_HIDDEN_ROWS:]]
        for row, col in self.current.cells:
            visible_row = row - BOARD_HIDDEN_ROWS
            if 0 <= visible_row < len(rows):
                rows[visible_row][col] = self.current.kind
        return rows
