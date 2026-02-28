# ─────────────────────────────────────────────
#  renderer.py  –  Desenarea scenei si HUD
# ─────────────────────────────────────────────

import pygame
from config import (
    WIDTH, HEIGHT,
    GRAY, ROAD_COUNTY, DARK_GRAY, DARK_COUNTY,
    YELLOW, WHITE_LINE, GREEN_LAND,
    ROAD_WIDTH, COL_X, ROW_Y,
    COUNTY_ROW, TRAFFIC_COL, TRAFFIC_ROW,
)
from road import road_width_for_row, intersection_rect

_font_road  = None
_font_small = None
_font_tiny  = None

def _init_fonts():
    global _font_road, _font_small, _font_tiny
    if _font_road is None:
        _font_road  = pygame.font.SysFont("consolas", 11, bold=True)
        _font_small = pygame.font.SysFont("consolas", 14)
        _font_tiny  = pygame.font.SysFont("consolas", 12)


def draw_roads(surface):
    _init_fonts()
    surface.fill(GREEN_LAND)
    _draw_horizontal_roads(surface)
    _draw_vertical_roads(surface)
    _draw_intersections(surface)


def _draw_horizontal_roads(surface):
    for i, ry in enumerate(ROW_Y):
        rw  = road_width_for_row(i)
        col = ROAD_COUNTY if i == COUNTY_ROW else GRAY
        pygame.draw.rect(surface, col, (0, ry - rw//2, WIDTH, rw))
        if i == COUNTY_ROW:
            pygame.draw.line(surface, YELLOW,      (0, ry-2), (WIDTH, ry-2), 2)
            pygame.draw.line(surface, YELLOW,      (0, ry+2), (WIDTH, ry+2), 2)
            pygame.draw.line(surface, WHITE_LINE,  (0, ry-30), (WIDTH, ry-30), 1)
            pygame.draw.line(surface, WHITE_LINE,  (0, ry+30), (WIDTH, ry+30), 1)
            pygame.draw.line(surface, WHITE_LINE,  (0, ry-rw//2+3), (WIDTH, ry-rw//2+3), 2)
            pygame.draw.line(surface, WHITE_LINE,  (0, ry+rw//2-3), (WIDTH, ry+rw//2-3), 2)
            lbl = _font_road.render("DRUM JUDETEAN", True, (255,240,150))
            surface.blit(lbl, (6, ry - rw//2 + 4))
        else:
            pygame.draw.line(surface, YELLOW, (0, ry), (WIDTH, ry), 2)


def _draw_vertical_roads(surface):
    for cx in COL_X:
        pygame.draw.rect(surface, GRAY, (cx - ROAD_WIDTH//2, 0, ROAD_WIDTH, HEIGHT))
        pygame.draw.line(surface, YELLOW, (cx, 0), (cx, HEIGHT), 2)


def _draw_intersections(surface):
    for col in range(len(COL_X)):
        for row in range(len(ROW_Y)):
            ir   = intersection_rect(col, row)
            dcol = DARK_COUNTY if row == COUNTY_ROW else DARK_GRAY
            pygame.draw.rect(surface, dcol, ir)
            if row == COUNTY_ROW:
                for offset in range(4, ir.width, 12):
                    pygame.draw.line(surface, (90,88,76),
                                     (ir.left+offset, ir.top),
                                     (ir.left+offset, ir.bottom), 4)


def draw_hud(surface, cars, traffic_light, shared_dqn, debug_mode):
    _init_fonts()
    waiting  = sum(1 for c in cars if c.waiting)
    county   = sum(1 for c in cars if c.on_county_road())
    collisions = getattr(shared_dqn, 'total_collisions', 0)

    phase_labels = ["Orizontal verde", "Galben", "Vertical verde", "Galben"]
    phase_colors = [(0,200,0),(220,200,0),(0,200,0),(220,200,0)]
    secs_left    = max(1, traffic_light.frames_left()//60)

    # Panel stanga – trafic
    traffic_lines = [
        (f"Masini:     {len(cars)}",          (255,255,255)),
        (f"  Mers:     {len(cars)-waiting}",   (255,255,255)),
        (f"  Stop:     {waiting}",             (255,255,255)),
        (f"  Judetean: {county}",              (255,240,100)),
        ("",                                   (0,0,0)),
        ("Semafor central:",                   (200,200,200)),
        (f"  {phase_labels[traffic_light.phase]}", phase_colors[traffic_light.phase]),
        (f"  {secs_left}s ramasi",             (200,200,200)),
    ]
    bg = pygame.Surface((220, 158), pygame.SRCALPHA)
    bg.fill((0,0,0,150))
    surface.blit(bg, (8, 8))
    for i,(text,color) in enumerate(traffic_lines):
        if text:
            surface.blit(_font_small.render(text, True, color), (14, 12 + i*18))

    # Panel dreapta – DQN stats
    eps_pct = int(shared_dqn.epsilon * 100)
    mem_pct = int(len(shared_dqn.memory) / shared_dqn.memory.buffer.maxlen * 100)
    dqn_lines = [
        ("=== Agent DQN ===",               (150,220,255)),
        (f"Steps:     {shared_dqn.steps}",  (255,255,255)),
        (f"Epsilon:   {eps_pct}%",          (255, max(0,255-eps_pct*2), 0)),
        (f"Memorie:   {mem_pct}%",          (200,200,255)),
        (f"Loss avg:  {shared_dqn.avg_loss:.4f}", (255,255,200)),
        (f"Coliziuni: {collisions}",        (255,100,100)),
        ("",                               (0,0,0)),
        (f"D=debug   Q=reset stats",       (160,160,160)),
    ]
    bg2 = pygame.Surface((230, 158), pygame.SRCALPHA)
    bg2.fill((0,0,0,150))
    surface.blit(bg2, (WIDTH-238, 8))
    for i,(text,color) in enumerate(dqn_lines):
        if text:
            surface.blit(_font_small.render(text, True, color), (WIDTH-232, 12 + i*18))

    # ── Legenda cerc V2X ──────────────────────────────────────
    v2x_legend = [
        ((30,  160, 255), "Liber"),
        ((255, 220,   0), "Atentie"),
        ((255, 120,   0), "Apropiat"),
        ((255,  30,  30), "Pericol"),
    ]
    lx = WIDTH // 2 - 160
    ly = HEIGHT - 44
    leg_bg = pygame.Surface((320, 28), pygame.SRCALPHA)
    leg_bg.fill((0, 0, 0, 130))
    surface.blit(leg_bg, (lx - 6, ly - 4))
    lbl_hdr = _font_tiny.render("V2X cerc:", True, (180, 220, 255))
    surface.blit(lbl_hdr, (lx - 4, ly))
    lx2 = lx + 68
    for col, label in v2x_legend:
        pygame.draw.circle(surface, col, (lx2 + 5, ly + 6), 5)
        pygame.draw.circle(surface, col, (lx2 + 5, ly + 6), 5, 1)
        txt = _font_tiny.render(label, True, col)
        surface.blit(txt, (lx2 + 13, ly))
        lx2 += 13 + txt.get_width() + 8

    # Hint tastatura
    hint_parts = [
        ("SPACE", (200,220,255)),
        ("=masina  ", (180,180,180)),
        ("D", (200,220,255)),
        ("=debug  ", (180,180,180)),
        ("ESC", (200,220,255)),
        ("=iesire", (180,180,180)),
    ]
    x = WIDTH//2 - 130
    y = HEIGHT - 22
    for txt, col in hint_parts:
        s = _font_tiny.render(txt, True, col)
        surface.blit(s, (x, y))
        x += s.get_width() + 1

    # Indicator modul debug
    if debug_mode:
        dbg = _font_small.render("[ DEBUG ON – raze perceptie vizibile ]", True, (100,255,100))
        surface.blit(dbg, (WIDTH//2 - dbg.get_width()//2, HEIGHT - 42))
