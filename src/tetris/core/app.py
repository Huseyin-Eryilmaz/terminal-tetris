"""The screens around the game, and the transitions between them.

Phase 2 had a single loop that always played Tetris. A finished program
needs more: somewhere to choose a mode, somewhere to pause, somewhere to
see how the last game went. The obvious way to add those is a pile of
booleans — `paused`, `in_menu`, `showing_scores` — which works right up
until two of them are true at once and nobody knows what the screen
should look like.

A state machine makes that impossible by construction. The app is in
exactly one `Screen` at a time, and each screen decides which key leads
where:

    MENU ──► PLAYING ⇄ PAUSED
      ▲         │        │
      │         ▼        │
      └──── GAME_OVER ◄──┘
      │
      └──► HELP ──┘

Like the game core, this module has no idea what a terminal is. It takes
keys in and reports which screen it is on; the renderer asks what to draw.
"""

from __future__ import annotations

from enum import Enum, auto

from tetris.core.game import Action, Game, GameState
from tetris.core.highscores import HighScore, load_scores, record_score
from tetris.core.keys import Key
from tetris.core.rules import RULE_SETS, RuleSet


class Screen(Enum):
    MENU = auto()
    PLAYING = auto()
    PAUSED = auto()
    GAME_OVER = auto()
    HELP = auto()
    QUIT = auto()


# Keys that map straight onto a game action while playing.
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

MENU_MODE_KEYS = {Key.D1: "classic", Key.D2: "modern"}


class App:
    """Owns the current screen and the game behind it."""

    def __init__(self, seed: int | None = None) -> None:
        self.screen = Screen.MENU
        self.seed = seed
        self.game: Game | None = None
        self.rules: RuleSet = RULE_SETS["modern"]()
        self.scores = load_scores()
        self.last_rank: int | None = None

    # ------------------------------------------------------------------
    # Transitions
    # ------------------------------------------------------------------
    def start_game(self, mode: str) -> None:
        self.rules = RULE_SETS[mode]()
        self.game = Game(rules=self.rules, seed=self.seed)
        self.last_rank = None
        self.screen = Screen.PLAYING

    def _finish_game(self) -> None:
        """Records the finished game's score and moves to the summary."""
        if self.game is not None:
            entry = HighScore(
                score=self.game.scorer.score,
                lines=self.game.scorer.lines_cleared,
                level=self.game.scorer.level,
            )
            mode = self.rules.name.lower()
            table, rank = record_score(mode, entry)
            self.scores[mode] = table
            self.last_rank = rank
        self.screen = Screen.GAME_OVER

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------
    def handle_keys(self, keys: list[Key]) -> None:
        """Routes this frame's keys according to the current screen."""
        for key in keys:
            match self.screen:
                case Screen.MENU:
                    self._handle_menu_key(key)
                case Screen.PLAYING:
                    self._handle_playing_key(key)
                case Screen.PAUSED:
                    self._handle_paused_key(key)
                case Screen.GAME_OVER:
                    self._handle_game_over_key(key)
                case Screen.HELP:
                    if key in (Key.ESCAPE, Key.ENTER, Key.Q):
                        self.screen = Screen.MENU
                case Screen.QUIT:
                    pass

        # Soft drop lapses when the key stops arriving; see the frame loop.
        if self.screen is Screen.PLAYING and self.game and Key.DOWN not in keys:
            self.game.release_soft_drop()

    def _handle_menu_key(self, key: Key) -> None:
        if mode := MENU_MODE_KEYS.get(key):
            self.start_game(mode)
        elif key is Key.D3:
            self.screen = Screen.HELP
        elif key in (Key.D4, Key.Q, Key.ESCAPE):
            self.screen = Screen.QUIT

    def _handle_playing_key(self, key: Key) -> None:
        if key is Key.P:
            self.screen = Screen.PAUSED
        elif key is Key.ESCAPE:
            self.screen = Screen.MENU  # abandon the game, no score recorded
        elif key is Key.Q:
            self.screen = Screen.QUIT
        elif self.game is not None and (action := ACTION_KEYS.get(key)):
            self.game.apply(action)

    def _handle_paused_key(self, key: Key) -> None:
        if key in (Key.P, Key.ENTER):
            self.screen = Screen.PLAYING
        elif key is Key.ESCAPE:
            self.screen = Screen.MENU
        elif key is Key.Q:
            self.screen = Screen.QUIT

    def _handle_game_over_key(self, key: Key) -> None:
        if key is Key.R and self.game is not None:
            self.start_game(self.rules.name.lower())
        elif key in (Key.ENTER, Key.ESCAPE):
            self.screen = Screen.MENU
        elif key is Key.Q:
            self.screen = Screen.QUIT

    # ------------------------------------------------------------------
    # Time
    # ------------------------------------------------------------------
    def tick(self, dt: float) -> None:
        """Advances the game, but only on the screen where time flows.

        Pausing is not a flag the game checks — the game simply stops
        being ticked. Nothing inside the rules needs to know that pausing
        exists at all.
        """
        if self.screen is not Screen.PLAYING or self.game is None:
            return

        self.game.tick(dt)
        if self.game.state is GameState.GAME_OVER:
            self._finish_game()

    @property
    def is_running(self) -> bool:
        return self.screen is not Screen.QUIT
