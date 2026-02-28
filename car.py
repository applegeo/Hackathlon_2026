# ─────────────────────────────────────────────
#  car.py  –  Clasa Car cu agent autonom integrat
# ─────────────────────────────────────────────

import random
import pygame
from config import (
    WIDTH, HEIGHT, CAR_COLORS,
    CAR_W, CAR_H, CAR_W_BIG, CAR_H_BIG,
    STOP_MARGIN, COL_X, ROW_Y, COUNTY_ROW,
)
from road import road_width_for_row
from agent import PERCEPTION_RADIUS


class Car:
    """
    Masina autonoma. Fiecare instanta este un agent care:
      - percepe mediul (vecini, semafor, distante)
      - decide actiunea prin Q-network (sau reguli clasice ca fallback)
      - invata din experienta proprie si a celorlalti agenti
    """

    id_counter = 0

    def __init__(self, direction, lane_index, speed=None, color=None, shared_dqn=None):
        Car.id_counter += 1
        self.id         = Car.id_counter
        self.direction  = direction
        self.lane_index = lane_index
        self.color      = color if color else random.choice(CAR_COLORS)
        self.waiting    = False
        self.shared_dqn = shared_dqn

        self.is_county = (direction in ('right', 'left') and lane_index == COUNTY_ROW)
        if self.is_county:
            self.speed = speed if speed else random.uniform(2.8, 4.2)
            cw, ch = CAR_W_BIG, CAR_H_BIG
        else:
            self.speed = speed if speed else random.uniform(1.8, 3.0)
            cw, ch = CAR_W, CAR_H

        off = random.choice([16, 46]) if self.is_county else 12

        if direction == 'right':
            self.x = -cw - random.randint(0, 300)
            self.y = ROW_Y[lane_index] - off - ch
            self.w, self.h = cw, ch
        elif direction == 'left':
            self.x = WIDTH + random.randint(0, 300)
            self.y = ROW_Y[lane_index] + off
            self.w, self.h = cw, ch
        elif direction == 'down':
            self.x = COL_X[lane_index] + off
            self.y = -cw - random.randint(0, 300)
            self.w, self.h = ch, cw
        elif direction == 'up':
            self.x = COL_X[lane_index] - off - ch
            self.y = HEIGHT + random.randint(0, 300)
            self.w, self.h = ch, cw

        # Stare agent pentru DQN
        self.prev_state           = None
        self.prev_action          = None
        self.intersections_passed = 0
        self._in_intersection     = False

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def front(self):
        if self.direction == 'right': return self.x + self.w
        if self.direction == 'left':  return self.x
        if self.direction == 'down':  return self.y + self.h
        if self.direction == 'up':    return self.y

    def is_off_screen(self):
        return (self.x > WIDTH+80 or self.x < -80 or
                self.y > HEIGHT+80 or self.y < -80)

    def stop_line(self, ir):
        if self.direction == 'right': return ir.left   - STOP_MARGIN
        if self.direction == 'left':  return ir.right  + STOP_MARGIN
        if self.direction == 'down':  return ir.top    - STOP_MARGIN
        if self.direction == 'up':    return ir.bottom + STOP_MARGIN

    def is_before(self, ir):
        if self.direction == 'right': return self.x + self.w <= ir.left
        if self.direction == 'left':  return self.x          >= ir.right
        if self.direction == 'down':  return self.y + self.h <= ir.top
        if self.direction == 'up':    return self.y          >= ir.bottom

    def dist_to_stop(self, ir):
        sl = self.stop_line(ir)
        f  = self.front()
        if self.direction == 'right': return sl - f
        if self.direction == 'left':  return f  - sl
        if self.direction == 'down':  return sl - f
        if self.direction == 'up':    return f  - sl

    def is_approaching(self, ir, window=120):
        d = self.dist_to_stop(ir)
        return 0 <= d <= window

    def is_in(self, ir):
        return self.rect.colliderect(ir)

    def right_direction(self):
        return {'right': 'up', 'left': 'down', 'down': 'right', 'up': 'left'}[self.direction]

    def on_county_road(self):
        return self.is_county

    def update_intersection_counter(self, intersection_rects):
        """Detecteaza iesirea dintr-o intersectie si incrementeaza contorul."""
        in_any = any(self.is_in(ir) for ir in intersection_rects)
        if self._in_intersection and not in_any:
            self.intersections_passed += 1
        self._in_intersection = in_any

    def decide(self, state):
        """Interogheaza DQN-ul pentru actiune. 0=mergi, 1=opreste."""
        if self.shared_dqn is None:
            return 0
        return self.shared_dqn.select_action(state)

    def apply_action(self, action):
        """Aplica actiunea DQN, dar fara sa suprascrie o oprire fortata de reguli hard."""
        if not self.waiting:
            self.waiting = (action == 1)

    def move(self):
        if self.waiting:
            return
        if self.direction == 'right': self.x += self.speed
        elif self.direction == 'left':  self.x -= self.speed
        elif self.direction == 'down':  self.y += self.speed
        elif self.direction == 'up':    self.y -= self.speed

    def draw_perception(self, surface):
        alpha_surf = pygame.Surface((PERCEPTION_RADIUS*2, PERCEPTION_RADIUS*2), pygame.SRCALPHA)
        pygame.draw.circle(alpha_surf, (100, 200, 255, 20),
                           (PERCEPTION_RADIUS, PERCEPTION_RADIUS), PERCEPTION_RADIUS)
        pygame.draw.circle(alpha_surf, (100, 200, 255, 50),
                           (PERCEPTION_RADIUS, PERCEPTION_RADIUS), PERCEPTION_RADIUS, 1)
        surface.blit(alpha_surf,
                     (int(self.rect.centerx) - PERCEPTION_RADIUS,
                      int(self.rect.centery) - PERCEPTION_RADIUS))

    def draw(self, surface, debug=False):
        if debug:
            self.draw_perception(surface)
        r = self.rect
        if self.is_county:
            pygame.draw.rect(surface, (255,255,255), r.inflate(3,3), border_radius=5)
        pygame.draw.rect(surface, self.color, r, border_radius=4)
        wc = (180, 220, 255)
        if self.direction in ('right', 'left'):
            pygame.draw.rect(surface, wc, (r.x+6, r.y+3, r.w-12, r.h-6), border_radius=2)
        else:
            pygame.draw.rect(surface, wc, (r.x+3, r.y+6, r.w-6, r.h-12), border_radius=2)
        if self.waiting:
            pygame.draw.circle(surface, (255,50,50), (r.centerx, r.centery), 5)
        elif self.shared_dqn is not None:
            pygame.draw.circle(surface, (50,255,50), (r.centerx, r.centery), 3)
