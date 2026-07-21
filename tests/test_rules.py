"""The rule matrix: every difference between classic and modern, tested
under both settings.

Same shape as the quirks tests in the CHIP-8 project — one behaviour, two
configurations, parametrized so neither can drift without the other
noticing.
"""

import random

import pytest

from tetris.core.bag import make_generator
from tetris.core.game import (
    DEFAULT_GRAVITY_INTERVAL,
    Action,
    Game,
    GameState,
)
from tetris.core.piece import Piece
from tetris.core.rules import RULE_SETS, RuleSet


def grounded_game(rules: RuleSet, seed: int = 1) -> Game:
    """A game whose current piece is resting on the floor."""
    game = Game(rules=rules, seed=seed)
    game.current = Piece("O", row=game.board.height - 2, col=4)
    return game


# ----------------------------------------------------------------------
# Lock delay
# ----------------------------------------------------------------------
def test_classic_locks_the_instant_a_piece_lands():
    game = grounded_game(RuleSet.classic())
    game.tick(0.001)
    assert game.pieces_placed == 1


def test_modern_gives_the_player_time_before_locking():
    rules = RuleSet.modern()
    game = grounded_game(rules)
    game.tick(rules.lock_delay * 0.5)
    assert game.pieces_placed == 0  # still movable
    game.tick(rules.lock_delay * 0.6)
    assert game.pieces_placed == 1


def test_moving_a_grounded_piece_restarts_the_lock_delay():
    rules = RuleSet.modern()
    game = grounded_game(rules)
    game.tick(rules.lock_delay * 0.9)
    game.apply(Action.MOVE_LEFT)  # a nudge buys more time
    game.tick(rules.lock_delay * 0.9)
    assert game.pieces_placed == 0
    game.tick(rules.lock_delay * 0.2)
    assert game.pieces_placed == 1


def test_lock_resets_are_capped_so_spinning_cannot_stall_forever():
    """Without a cap, a player could rotate on the floor indefinitely.
    Once the budget runs out, the countdown continues regardless."""
    rules = RuleSet.modern()
    game = grounded_game(rules)
    for _ in range(rules.max_lock_resets + 5):
        game.apply(Action.ROTATE_CW)
    game.tick(rules.lock_delay + 0.01)
    assert game.pieces_placed == 1


def test_a_piece_that_slides_off_an_edge_gets_its_delay_back():
    """Grounded, then airborne again: the lock clock must reset, or the
    piece would freeze in mid-air a moment later."""
    rules = RuleSet.modern()
    game = Game(rules=rules, seed=1)
    game.board.grid[game.board.height - 1][5] = "X"
    game.current = Piece("O", row=game.board.height - 3, col=4)  # cols 5-6
    assert game._is_grounded()

    game.tick(rules.lock_delay * 0.9)
    game.apply(Action.MOVE_RIGHT)  # now hanging over empty space
    assert not game._is_grounded()

    game.tick(rules.lock_delay * 0.9)
    assert game.pieces_placed == 0


# ----------------------------------------------------------------------
# Piece generation
# ----------------------------------------------------------------------
def test_modern_deals_every_piece_once_per_bag():
    """Tested on the generator directly: a Game has already taken one
    piece for the field, so counting from its queue would straddle two
    bags and see a repeat that is perfectly legal."""
    generator = make_generator(use_bag=True, rng=random.Random(3))
    first_bag = [generator.next_piece() for _ in range(7)]
    second_bag = [generator.next_piece() for _ in range(7)]
    assert sorted(first_bag) == sorted("IOTSZJL")
    assert sorted(second_bag) == sorted("IOTSZJL")


def test_classic_generator_has_no_such_guarantee():
    generator = make_generator(use_bag=False, rng=random.Random(3))
    drawn = [generator.next_piece() for _ in range(7)]
    assert sorted(drawn) != sorted("IOTSZJL")  # near-certain to differ


def test_modern_never_starves_the_player_of_a_piece():
    """The 7-bag guarantee: at most 12 pieces between two I pieces."""
    game = Game(rules=RuleSet.modern(), seed=9)
    sequence = [game.queue.pop() for _ in range(200)]
    gaps = []
    last_i = None
    for index, kind in enumerate(sequence):
        if kind == "I":
            if last_i is not None:
                gaps.append(index - last_i - 1)
            last_i = index
    assert max(gaps) <= 12


def test_classic_randomness_is_unconstrained():
    """Pure random can repeat a piece back to back — the very thing the
    bag exists to prevent. Over a long run it is near-certain."""
    game = Game(rules=RuleSet.classic(), seed=4)
    sequence = [game.queue.pop() for _ in range(200)]
    pairs = zip(sequence, sequence[1:], strict=False)
    assert any(a == b for a, b in pairs)


@pytest.mark.parametrize("name", RULE_SETS)
def test_same_seed_replays_identically_in_both_modes(name):
    rules = RULE_SETS[name]()
    first = [Game(rules=rules, seed=11).queue.pop() for _ in range(1)]
    a = Game(rules=rules, seed=11)
    b = Game(rules=rules, seed=11)
    assert [a.queue.pop() for _ in range(30)] == [b.queue.pop() for _ in range(30)]
    assert first  # sanity


# ----------------------------------------------------------------------
# Preview queue
# ----------------------------------------------------------------------
@pytest.mark.parametrize(("name", "expected"), [("classic", 1), ("modern", 5)])
def test_preview_length_matches_the_rule_set(name, expected):
    game = Game(rules=RULE_SETS[name](), seed=2)
    assert len(game.queue.preview()) == expected


def test_preview_shows_exactly_what_arrives_next():
    """The preview is a promise: whatever is shown first must be the very
    next piece the player receives."""
    game = Game(rules=RuleSet.modern(), seed=6)
    promised = game.queue.preview()[0]
    assert game.queue.pop() == promised


# ----------------------------------------------------------------------
# Profiles
# ----------------------------------------------------------------------
def test_the_two_profiles_disagree_on_every_flag():
    classic = RuleSet.classic().__dict__
    modern = RuleSet.modern().__dict__
    differing = [k for k in classic if k != "name" and classic[k] != modern[k]]
    assert len(differing) == len(classic) - 1


def test_default_game_uses_modern_rules():
    assert Game(seed=1).rules.name == "MODERN"


@pytest.mark.parametrize("name", RULE_SETS)
def test_both_modes_can_be_played_to_a_game_over(name):
    """An end-to-end smoke test: hard-drop pieces until the stack tops out,
    proving the whole loop works under either rule set."""
    game = Game(rules=RULE_SETS[name](), seed=5)
    for _ in range(500):
        if game.state is GameState.GAME_OVER:
            break
        game.apply(Action.HARD_DROP)
    assert game.state is GameState.GAME_OVER
    assert game.pieces_placed > 10


def test_gravity_still_works_under_both_rule_sets():
    for name in RULE_SETS:
        game = Game(rules=RULE_SETS[name](), seed=8)
        game.current = Piece("T", row=3, col=4)
        game.tick(DEFAULT_GRAVITY_INTERVAL)
        assert game.current.row == 4
