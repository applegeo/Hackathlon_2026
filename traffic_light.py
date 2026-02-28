# ─────────────────────────────────────────────
#  traffic_light.py  –  Clasa TrafficLight
# ─────────────────────────────────────────────

import pygame
from config import PHASE_DURATIONS


class TrafficLight:
    """
    Semafor cu 4 faze pentru intersectia centrala:
        Faza 0 – orizontal VERDE,  vertical ROSU
        Faza 1 – orizontal GALBEN, vertical ROSU   (tranzitie)
        Faza 2 – orizontal ROSU,   vertical VERDE
        Faza 3 – orizontal ROSU,   vertical GALBEN (tranzitie)
    """

    def __init__(self):
        self.phase = 0
        self.timer = 0

    # ── Actualizare stare ──────────────────────────────────────

    def update(self):
        """Avanseaza timerul cu un frame si schimba faza daca e cazul."""
        self.timer += 1
        if self.timer >= PHASE_DURATIONS[self.phase]:
            self.timer = 0
            self.phase = (self.phase + 1) % 4

    # ── Starea culorii pe directie ─────────────────────────────

    def horiz_state(self) -> str:
        """Culoarea pentru directiile orizontale (right / left)."""
        if self.phase == 0: return 'green'
        if self.phase == 1: return 'yellow'
        return 'red'

    def vert_state(self) -> str:
        """Culoarea pentru directiile verticale (up / down)."""
        if self.phase == 2: return 'green'
        if self.phase == 3: return 'yellow'
        return 'red'

    def state_for(self, direction: str) -> str:
        """Returneaza starea semaforului pentru o directie data."""
        return self.horiz_state() if direction in ('right', 'left') else self.vert_state()

    def must_stop(self, direction: str) -> bool:
        """True daca o masina cu directia data trebuie sa se opreasca."""
        return self.state_for(direction) in ('red', 'yellow')

    def frames_left(self) -> int:
        """Frame-uri ramase pana la urmatoarea schimbare de faza."""
        return PHASE_DURATIONS[self.phase] - self.timer

    # ── Desenare ──────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, ir: pygame.Rect):
        """
        Deseneaza 4 stalpi de semafor la colturile intersectiei `ir`
        si un countdown deasupra.
        """
        hw = self.horiz_state()
        vt = self.vert_state()

        def draw_pole(x: int, y: int, state: str):
            """Deseneaza un stalp de semafor cu 3 leduri la pozitia (x, y)."""
            bw, bh = 20, 54
            pygame.draw.rect(surface, (30, 30, 30), (x, y, bw, bh), border_radius=4)
            cx = x + bw // 2
            pygame.draw.circle(surface,
                                (200, 0, 0)   if state == 'red'    else (60, 0, 0),
                                (cx, y + 10), 7)
            pygame.draw.circle(surface,
                                (220, 200, 0) if state == 'yellow' else (60, 55, 0),
                                (cx, y + 27), 7)
            pygame.draw.circle(surface,
                                (0, 200, 0)   if state == 'green'  else (0, 60, 0),
                                (cx, y + 44), 7)

        # Stanga-sus si dreapta-jos → pentru directia orizontala
        draw_pole(ir.left - 30, ir.top  - 62, hw)
        draw_pole(ir.right + 10, ir.bottom + 8, hw)
        # Dreapta-sus si stanga-jos → pentru directia verticala
        draw_pole(ir.right + 10, ir.top  - 62, vt)
        draw_pole(ir.left  - 30, ir.bottom + 8, vt)

        # Countdown in secunde
        font = pygame.font.SysFont("consolas", 13, bold=True)
        secs = max(1, self.frames_left() // 60)
        txt  = font.render(f"{secs}s", True, (255, 255, 255))
        surface.blit(txt, (ir.centerx - txt.get_width() // 2, ir.top - 18))
