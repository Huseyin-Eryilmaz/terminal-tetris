"""What separates classic Tetris from modern Tetris.

Tetris has no single specification. The 1984 original and the versions
that followed made different choices, and in 2001 the Tetris Guideline
standardised a rather different game. Both are worth playing, and both
are the same engine underneath — the differences fit in the handful of
flags below.

Rather than scattering `if classic:` checks through the rules, every
disagreement becomes a named field here. Adding a rule variant later
means adding a field, not hunting through the codebase.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuleSet:
    name: str

    use_bag_randomizer: bool
    """Piece order. True = 7-bag (each tetromino once per bag, shuffled);
    False = pure random, which can starve you of an I piece for a long,
    demoralising time."""

    lock_delay: float
    """Seconds a landed piece may still be moved before it freezes.
    0.0 = the classic behaviour: touch down, stick instantly."""

    max_lock_resets: int
    """How many times moving or rotating may restart the lock delay.
    Without a cap, a player could spin a piece on the floor forever."""

    next_queue_size: int
    """How many upcoming pieces the player is shown."""

    allow_hold: bool
    """Whether a piece can be stashed and swapped back in later."""

    show_ghost: bool
    """Whether the landing position is previewed."""

    use_srs: bool
    """Rotation system. True = Super Rotation System with wall kicks;
    False = classic, where a blocked rotation simply does not happen."""

    @classmethod
    def classic(cls) -> RuleSet:
        return cls(
            name="CLASSIC",
            use_bag_randomizer=False,
            lock_delay=0.0,
            max_lock_resets=0,
            next_queue_size=1,
            allow_hold=False,
            show_ghost=False,
            use_srs=False,
        )

    @classmethod
    def modern(cls) -> RuleSet:
        return cls(
            name="MODERN",
            use_bag_randomizer=True,
            lock_delay=0.5,
            max_lock_resets=15,
            next_queue_size=5,
            allow_hold=True,
            show_ghost=True,
            use_srs=True,
        )


RULE_SETS = {
    "classic": RuleSet.classic,
    "modern": RuleSet.modern,
}
