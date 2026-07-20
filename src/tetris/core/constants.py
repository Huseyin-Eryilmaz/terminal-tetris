"""Dimensions shared by the whole game.

The well is 10 wide and 20 tall — the size every Tetris has used since
1984. The extra hidden rows above the visible field are where new pieces
spawn: a piece needs somewhere to exist before it enters the screen, and
"has the stack reached the ceiling?" becomes a simple question about
whether anything is locked in those rows.
"""

BOARD_WIDTH = 10
BOARD_VISIBLE_HEIGHT = 20
BOARD_HIDDEN_ROWS = 2
BOARD_HEIGHT = BOARD_VISIBLE_HEIGHT + BOARD_HIDDEN_ROWS

FRAMES_PER_SECOND = 60
