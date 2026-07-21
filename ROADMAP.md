# Roadmap

Seven phases, each with acceptance criteria. `main` stays green; each
phase is a short-lived `feat/` branch ending in a tagged release.

## Phase 0 — Scaffolding & terminal shell `v0.0.1` ✅
- [x] Project skeleton: uv, ruff, pytest + coverage, pre-commit, CI
- [x] ANSI renderer: cursor control, 256-colour palette, box drawing,
      single-write frames
- [x] Cross-platform non-blocking keyboard (`msvcrt` / `termios` + `select`),
      both decoded into one `Key` enum
- [x] Fixed-rate frame loop with terminal state restored on exit

**Acceptance:** `uv run tetris` draws an empty well, echoes pressed keys
live, and `Q` quits leaving the terminal usable.

## Phase 1 — Board & piece model `v0.1.0-pre` ✅
- [X] 10x20 grid (+2 hidden spawn rows), cell occupancy
- [X] Seven tetrominoes with four rotation states each
- [X] Collision test (`can_place`), locking, line clearing with gravity
- [X] Unit tests: single/multiple/gap clears, out-of-bounds, overlap

**Acceptance:** the entire model is exercised headlessly; no rendering yet.

## Phase 2 — Playable loop `v0.1.0` ✅
- [X] Gravity, soft drop, hard drop, horizontal movement
- [X] Spawn → fall → lock → clear → spawn state machine
- [X] Top-out detection
- [X] Board rendering wired to the renderer

**Acceptance:** a playable game of classic Tetris in the terminal.

## Phase 3 — Rule sets `v0.2.0` ✅
- [X] `RuleSet` dataclass with `classic()` and `modern()` profiles
- [X] Two piece generators: pure random and 7-bag
- [X] Lock delay (modern only), reset on movement
- [X] Parametrized tests covering both profiles

**Acceptance:** both modes playable and behaviourally distinct in tests.

## Phase 4 — SRS & wall kicks `v0.3.0`
- [ ] SRS kick tables (JLSTZ set, I set, O exempt)
- [ ] Rotation tries five candidate offsets, applies the first that fits
- [ ] Tests for known kick scenarios, including the T-spin setup

**Acceptance:** wall-kick cases verified against the SRS specification.

## Phase 5 — Modern mechanics `v0.4.0`
- [ ] Hold piece (once per lock)
- [ ] Ghost piece projection
- [ ] Next queue (5 previews)
- [ ] Guideline scoring, level curve, T-spin detection

**Acceptance:** each mechanic unit-tested; scoring matches the table.

## Phase 6 — Menu & polish `v0.5.0`
- [ ] Menu state machine: MENU → PLAYING → PAUSED → GAME_OVER → MENU
- [ ] Mode selection, controls screen, pause, game-over summary
- [ ] High scores persisted to JSON (stdlib only)

## Phase 7 — Showcase `v1.0.0`
- [ ] README: architecture, rule comparison, SRS writeup
- [ ] Terminal gameplay GIF
- [ ] Release notes, About + topics

## Beyond 1.0 (ideas)
- Replay recording (seeded RNG makes runs reproducible)
- Simple AI player scoring board states
- Rust port sharing the same rule tests
