# ─────────────────────────────────────────────
#  road.py  –  Geometria retelei de drumuri
# ─────────────────────────────────────────────

import pygame
from config import (
    COL_X, ROW_Y,
    ROAD_WIDTH, COUNTY_ROAD_WIDTH,
    COUNTY_ROW,
)


def road_width_for_row(row: int) -> int:
    """Returneaza latimea drumului orizontal pentru randul dat."""
    return COUNTY_ROAD_WIDTH if row == COUNTY_ROW else ROAD_WIDTH


def road_width_for_col(col: int) -> int:
    """Returneaza latimea drumului vertical pentru coloana data.
    (Toate drumurile verticale au aceeasi latime in aceasta simulare.)
    """
    return ROAD_WIDTH


def intersection_rect(col: int, row: int) -> pygame.Rect:
    """
    Returneaza dreptunghiul intersectiei dintre coloana `col` si randul `row`.

    Latimea intersectiei = latimea drumului vertical (col).
    Inaltimea intersectiei = latimea drumului orizontal (row).
    """
    cw = road_width_for_col(col)
    rw = road_width_for_row(row)
    x  = COL_X[col] - cw // 2
    y  = ROW_Y[row] - rw // 2
    return pygame.Rect(x, y, cw, rw)
