# ─────────────────────────────────────────────
#  car.py  –  Clasa Car cu agent autonom integrat
#
#  Cerc de perceptie V2X MEREU vizibil:
#    ALBASTRU   – liber
#    GALBEN     – masina detectata in raza
#    PORTOCALIU – masina apropiata in fata
#    ROSU       – pericol iminent
# ─────────────────────────────────────────────

import math
import random
import pygame
from config import (
    WIDTH, HEIGHT, CAR_COLORS,
    CAR_W, CAR_H, CAR_W_BIG, CAR_H_BIG,
    STOP_MARGIN, COL_X, ROW_Y, COUNTY_ROW,
)
from road import road_width_for_row
from agent import PERCEPTION_RADIUS

DANGER_RADIUS = PERCEPTION_RADIUS // 3


class Car:
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

        self.prev_state           = None
        self.prev_action          = None
        self.intersections_passed = 0
        self._in_intersection     = False

        # V2X state
        self.threat_level   = 0
        self.nearby_cars    = []
        self.danger_cars    = []
        self._pulse_timer   = 0
        self._pulse_growing = True

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

    def update_v2x_perception(self, all_cars: list):
        cx, cy = self.rect.centerx, self.rect.centery
        self.nearby_cars = []
        self.danger_cars = []
        max_threat = 0

        dir_vec = {'right':(1,0), 'left':(-1,0), 'down':(0,1), 'up':(0,-1)}
        my_dx, my_dy = dir_vec.get(self.direction, (1, 0))

        for other in all_cars:
            if other is self:
                continue
            ox, oy = other.rect.centerx, other.rect.centery
            dx, dy = ox - cx, oy - cy
            dist   = math.hypot(dx, dy)
            if dist > PERCEPTION_RADIUS:
                continue

            self.nearby_cars.append(other)
            dot      = dx * my_dx + dy * my_dy
            in_front = dot > 0

            if dist <= DANGER_RADIUS:
                threat = 3
                self.danger_cars.append(other)
            elif dist <= PERCEPTION_RADIUS * 0.55 and in_front:
                threat = 2
            else:
                threat = 1

            if threat > max_threat:
                max_threat = threat

        self.threat_level = max_threat

        if self.threat_level >= 2:
            if self._pulse_growing:
                self._pulse_timer += 3
                if self._pulse_timer >= 18:
                    self._pulse_growing = False
            else:
                self._pulse_timer -= 3
                if self._pulse_timer <= 0:
                    self._pulse_growing = True
        else:
            self._pulse_timer = max(0, self._pulse_timer - 1)
            self._pulse_growing = True

    def update_intersection_counter(self, intersection_rects):
        in_any = any(self.is_in(ir) for ir in intersection_rects)
        if self._in_intersection and not in_any:
            self.intersections_passed += 1
        self._in_intersection = in_any

    def decide(self, state):
        if self.shared_dqn is None:
            return 0
        return self.shared_dqn.select_action(state)

    def apply_action(self, action):
        if not self.waiting:
            self.waiting = (action == 1)

    def move(self):
        if self.waiting:
            return
        if self.direction == 'right': self.x += self.speed
        elif self.direction == 'left':  self.x -= self.speed
        elif self.direction == 'down':  self.y += self.speed
        elif self.direction == 'up':    self.y -= self.speed

    def _threat_rgb(self):
        if self.threat_level == 0:
            return (30,  160, 255)
        elif self.threat_level == 1:
            return (255, 220,   0)
        elif self.threat_level == 2:
            return (255, 120,   0)
        else:
            return (255,  30,  30)

    def draw_perception(self, surface):
        cx, cy = self.rect.centerx, self.rect.centery
        rgb    = self._threat_rgb()
        pulse  = self._pulse_timer

        r_out = PERCEPTION_RADIUS + pulse + 4
        size  = r_out * 2 + 1
        surf  = pygame.Surface((size, size), pygame.SRCALPHA)
        mid   = r_out

        # Cerc exterior
        fill_a = 14 + self.threat_level * 5
        ring_a = 70 + self.threat_level * 30
        pygame.draw.circle(surf, (rgb[0], rgb[1], rgb[2], fill_a), (mid, mid), r_out)
        pygame.draw.circle(surf, (rgb[0], rgb[1], rgb[2], ring_a), (mid, mid), r_out, 2)

        # Cerc interior (zona pericol)
        r_in   = DANGER_RADIUS + pulse // 2
        fill_ia = 25 + self.threat_level * 10
        ring_ia = 110 + self.threat_level * 35
        pygame.draw.circle(surf, (rgb[0], rgb[1], rgb[2], fill_ia), (mid, mid), r_in)
        pygame.draw.circle(surf, (rgb[0], rgb[1], rgb[2], ring_ia), (mid, mid), r_in, 2)

        # Linii V2X catre vecini
        for other in self.nearby_cars:
            ox, oy = other.rect.centerx, other.rect.centery
            dist   = math.hypot(ox - cx, oy - cy)
            if dist < 1:
                continue
            a = int(180 * (1.0 - dist / PERCEPTION_RADIUS))
            if other in self.danger_cars:
                lc = (255, 40, 40, min(220, a + 80))
                lw = 2
            elif self.threat_level == 2:
                lc = (255, 160, 0, min(190, a + 50))
                lw = 1
            else:
                lc = (rgb[0], rgb[1], rgb[2], min(150, a + 30))
                lw = 1
            tx = mid + int(ox - cx)
            ty = mid + int(oy - cy)
            # Clip la suprafata pentru a evita desenul in afara
            tx = max(0, min(size - 1, tx))
            ty = max(0, min(size - 1, ty))
            pygame.draw.line(surf, lc, (mid, mid), (tx, ty), lw)

        # Sageata directie
        dir_vec = {'right':(1,0), 'left':(-1,0), 'down':(0,1), 'up':(0,-1)}
        dvx, dvy = dir_vec.get(self.direction, (1, 0))
        arr_end  = max(r_in - 6, 4)
        tip_x = mid + dvx * arr_end
        tip_y = mid + dvy * arr_end
        ac = (rgb[0], rgb[1], rgb[2], 180)
        pygame.draw.line(surf, ac, (mid, mid), (int(tip_x), int(tip_y)), 2)
        px, py = -dvy, dvx
        pygame.draw.polygon(surf, ac, [
            (int(tip_x),                        int(tip_y)),
            (int(tip_x - dvx*8 + px*4),        int(tip_y - dvy*8 + py*4)),
            (int(tip_x - dvx*8 - px*4),        int(tip_y - dvy*8 - py*4)),
        ])

        surface.blit(surf, (cx - mid, cy - mid))

    def draw(self, surface, debug=False):
        self.draw_perception(surface)

        r = self.rect
        if self.is_county:
            pygame.draw.rect(surface, (255, 255, 255), r.inflate(3, 3), border_radius=5)
        pygame.draw.rect(surface, self.color, r, border_radius=4)

        wc = (180, 220, 255)
        if self.direction in ('right', 'left'):
            pygame.draw.rect(surface, wc, (r.x+6, r.y+3, r.w-12, r.h-6), border_radius=2)
        else:
            pygame.draw.rect(surface, wc, (r.x+3, r.y+6, r.w-6, r.h-12), border_radius=2)

        if self.waiting:
            pygame.draw.circle(surface, (255, 50, 50),  (r.centerx, r.centery), 5)
        elif self.threat_level >= 3:
            col = (255, 80, 80) if (self._pulse_timer % 6) < 3 else (255, 255, 255)
            pygame.draw.circle(surface, col,             (r.centerx, r.centery), 5)
        elif self.threat_level == 2:
            pygame.draw.circle(surface, (255, 140, 0),  (r.centerx, r.centery), 4)
        elif self.shared_dqn is not None:
            pygame.draw.circle(surface, (50, 255, 50),  (r.centerx, r.centery), 3)

        if debug:
            try:
                font = pygame.font.SysFont("consolas", 10)
                id_surf = font.render(str(self.id), True, (255, 255, 255))
                surface.blit(id_surf, (r.centerx - id_surf.get_width()//2,
                                       r.centery - id_surf.get_height()//2))
            except Exception:
                pass
