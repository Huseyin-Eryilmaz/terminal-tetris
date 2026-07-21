"""The well: what is occupied, what fits, and what happens when rows fill.

The grid stores a piece letter (or None) per cell rather than a boolean,
because the renderer needs to know which colour a locked block was — the
information is free to keep and impossible to recover later.

Rows are indexed from the top: row 0 is the ceiling, row HEIGHT-1 the
floor. The first BOARD_HIDDEN_ROWS rows sit above the visible field; that
is where pieces spawn, and anything locked up there means the stack has
reached the top.
"""

from __future__ import annotations

from tetris.core.constants import BOARD_HEIGHT, BOARD_HIDDEN_ROWS, BOARD_WIDTH
from tetris.core.piece import Piece

Cell = str | None


class Board:
    """A grid of locked blocks, plus the rules for placing pieces into it."""

    def __init__(self, width: int = BOARD_WIDTH, height: int = BOARD_HEIGHT) -> None:
        self.width = width
        self.height = height
        self.grid: list[list[Cell]] = [[None] * width for _ in range(height)]

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def is_inside(self, row: int, col: int) -> bool:
        """Is this coordinate on the board at all?

        Note the asymmetry: the ceiling is *not* a wall. A piece may sit
        partly above row 0 while spawning or being kicked upward, so only
        the floor and the side walls block movement.
        """
        return 0 <= col < self.width and row < self.height

    def is_occupied(self, row: int, col: int) -> bool:
        """Is a locked block already here? Cells above the grid are empty."""
        if row < 0:
            return False
        return self.grid[row][col] is not None

    def can_place(self, piece: Piece) -> bool:
        """Can this piece exist here — inside the walls and not overlapping?

        Every movement, rotation and kick in the game asks this one
        question. Keeping it in a single place means the rules can never
        disagree with themselves.
        """
        return all(
            self.is_inside(row, col) and not self.is_occupied(row, col)
            for row, col in piece.cells
        )

    def is_row_full(self, row: int) -> bool:
        return all(cell is not None for cell in self.grid[row])

    def is_row_empty(self, row: int) -> bool:
        return all(cell is None for cell in self.grid[row])

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------
    def lock(self, piece: Piece) -> None:
        """Freezes a piece into the grid. Cells above the ceiling are dropped."""
        for row, col in piece.cells:
            if row >= 0:
                self.grid[row][col] = piece.kind

    def clear_lines(self) -> list[int]:
        """Removes every full row, drops everything above, returns the rows.

        Implemented by rebuilding rather than deleting in place: keep the
        rows that survive, then pad the top with empty ones. Deleting while
        iterating over the same list is the classic way to skip a row when
        two full rows are adjacent — this sidesteps it entirely.
        """
        full_rows = [r for r in range(self.height) if self.is_row_full(r)]
        if not full_rows:
            return []

        cleared = set(full_rows)
        survivors = [row for r, row in enumerate(self.grid) if r not in cleared]
        empty_rows: list[list[Cell]] = [
            [None] * self.width for _ in range(len(full_rows))
        ]
        self.grid = empty_rows + survivors
        return full_rows

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------
    def is_topped_out(self) -> bool:
        """Has the stack reached the hidden spawn rows?"""
        return any(not self.is_row_empty(row) for row in range(BOARD_HIDDEN_ROWS))

    def height_of_column(self, col: int) -> int:
        """Number of rows from the highest block in this column to the floor."""
        for row in range(self.height):
            if self.grid[row][col] is not None:
                return self.height - row
        return 0

    def __str__(self) -> str:
        """Text dump, for debugging and readable test failures."""
        return "\n".join("".join(cell or "." for cell in row) for row in self.grid)
