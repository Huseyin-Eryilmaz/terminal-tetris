# terminal-tetris

Classic **and** modern Tetris, played in the terminal. Pure-Python game
core with zero runtime dependencies — the rules never touch the screen,
and the screen is nothing but ANSI escape codes.

> 🚧 **Status: Phase 0 (scaffolding).** The frame loop, the ANSI renderer
> and the cross-platform keyboard layer work; the game itself starts in
> Phase 1. See the [roadmap](ROADMAP.md).

## Two rule sets, one engine

The same core runs under two historically different sets of rules,
selected from the menu:

| | Classic | Modern |
|---|---|---|
| Rotation | simple (blocked = no rotation) | SRS with wall kicks |
| Piece order | pure random | 7-bag |
| Hold | — | yes |
| Ghost piece | — | yes |
| Next queue | 1 | 5 |
| Lock delay | — | yes |
| Scoring | 40 / 100 / 300 / 1200 × level | Guideline + T-spins |

## Quick start

```bash
uv sync
uv run tetris
```

Requires a terminal that understands ANSI escape codes — any modern
Windows Terminal, macOS Terminal, or Linux console will do.

## Architecture

```
src/tetris/
  core/     pure game rules — no printing, no input, no clocks
  ui/       terminal shell — ANSI rendering, keyboard polling
  __main__.py   the frame loop that connects them
```

`core/` is written so it can be tested without a terminal: feed it actions,
inspect the resulting state. That is what keeps rules like wall kicks and
T-spin detection honest.

## Development

```bash
uv run pytest --cov=tetris
uv run ruff check . && uv run ruff format .
```

## License

MIT
