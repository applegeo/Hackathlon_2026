import pygame
import sys
import random

pygame.init()

WIDTH, HEIGHT = 900, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Intersectii Multiple - Prioritate de Dreapta")

GRAY       = (60, 60, 60)
DARK_GRAY  = (40, 40, 40)
YELLOW     = (255, 220, 0)
GREEN_LAND = (34, 120, 34)

CAR_COLORS = [
    (200, 30,  30),
    (30,  30,  200),
    (200, 140,  0),
    (0,   180,  80),
    (180,  0,  180),
    (0,   200, 200),
    (220,  80,   0),
    (100,   0,  200),
]

ROAD_WIDTH  = 90
CAR_W       = 36
CAR_H       = 18
STOP_MARGIN  = 4
FOLLOW_GAP   = 6    # spatiu minim intre masini cand sunt fizic adiacente
APPROACH_WIN = 130  # fereastra (pixeli) in care se aplica prioritatea de dreapta

clock = pygame.time.Clock()

COL_X = [220, 450, 680]
ROW_Y = [200, 480]


def intersection_rect(col, row):
    x = COL_X[col] - ROAD_WIDTH // 2
    y = ROW_Y[row] - ROAD_WIDTH // 2
    return pygame.Rect(x, y, ROAD_WIDTH, ROAD_WIDTH)


class Car:
    id_counter = 0

    def __init__(self, direction, lane_index, speed=None, color=None):
        Car.id_counter += 1
        self.id         = Car.id_counter
        self.direction  = direction
        self.lane_index = lane_index
        self.speed      = speed if speed else random.uniform(1.8, 3.0)
        self.color      = color if color else random.choice(CAR_COLORS)
        self.waiting    = False

        offset = 12

        if direction == 'right':
            self.x = -CAR_W - random.randint(0, 300)
            self.y = ROW_Y[lane_index] - offset - CAR_H
            self.w, self.h = CAR_W, CAR_H
        elif direction == 'left':
            self.x = WIDTH + random.randint(0, 300)
            self.y = ROW_Y[lane_index] + offset
            self.w, self.h = CAR_W, CAR_H
        elif direction == 'down':
            self.x = COL_X[lane_index] + offset
            self.y = -CAR_W - random.randint(0, 300)
            self.w, self.h = CAR_H, CAR_W
        elif direction == 'up':
            self.x = COL_X[lane_index] - offset - CAR_H
            self.y = HEIGHT + random.randint(0, 300)
            self.w, self.h = CAR_H, CAR_W

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def front(self):
        if self.direction == 'right': return self.x + self.w
        if self.direction == 'left':  return self.x
        if self.direction == 'down':  return self.y + self.h
        if self.direction == 'up':    return self.y

    def is_off_screen(self):
        return (self.x > WIDTH + 80 or self.x < -80 or
                self.y > HEIGHT + 80 or self.y < -80)

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

    def move(self):
        if self.waiting:
            return
        if self.direction == 'right': self.x += self.speed
        elif self.direction == 'left':  self.x -= self.speed
        elif self.direction == 'down':  self.y += self.speed
        elif self.direction == 'up':    self.y -= self.speed

    def draw(self, surface):
        r = self.rect
        pygame.draw.rect(surface, self.color, r, border_radius=4)
        wc = (180, 220, 255)
        if self.direction in ('right', 'left'):
            pygame.draw.rect(surface, wc, (r.x+6, r.y+3, r.w-12, r.h-6), border_radius=2)
        else:
            pygame.draw.rect(surface, wc, (r.x+3, r.y+6, r.w-6, r.h-12), border_radius=2)
        if self.waiting:
            pygame.draw.circle(surface, (255, 50, 50), (r.centerx, r.centery), 5)


# ──────────────────────────────────────────────────────────────
#  Helpers pentru coada în bandă
# ──────────────────────────────────────────────────────────────
def same_lane(a, b):
    return a.direction == b.direction and a.lane_index == b.lane_index

def is_ahead_in_lane(leader, follower):
    if leader.direction == 'right': return leader.x > follower.x
    if leader.direction == 'left':  return leader.x < follower.x
    if leader.direction == 'down':  return leader.y > follower.y
    if leader.direction == 'up':    return leader.y < follower.y
    return False

def gap_to_leader(leader, follower):
    if follower.direction == 'right': return leader.x - (follower.x + follower.w)
    if follower.direction == 'left':  return follower.x - (leader.x + leader.w)
    if follower.direction == 'down':  return leader.y - (follower.y + follower.h)
    if follower.direction == 'up':    return follower.y - (leader.y + leader.h)
    return 999


# ──────────────────────────────────────────────────────────────
#  LOGICA PRINCIPALA DE PRIORITATE
# ──────────────────────────────────────────────────────────────
def apply_priority(cars):
    # Reset
    for c in cars:
        c.waiting = False

    # 1. Prioritate de dreapta la fiecare intersectie
    #    Masina cedeaza DOAR daca se afla in fereastra de apropiere
    for col in range(len(COL_X)):
        for row in range(len(ROW_Y)):
            ir = intersection_rect(col, row)

            relevant = [c for c in cars
                        if (c.direction in ('right', 'left') and c.lane_index == row) or
                           (c.direction in ('up', 'down')    and c.lane_index == col)]

            in_int = [c for c in relevant if c.is_in(ir)]
            near   = [c for c in relevant
                      if not c.is_in(ir)
                      and c.is_before(ir)
                      and c.is_approaching(ir, window=APPROACH_WIN)]

            if not near:
                continue

            for c in near:
                right_dir = c.right_direction()
                for other in (near + in_int):
                    if other is c:
                        continue
                    if other.direction == right_dir:
                        c.waiting = True
                        break

    # 2. Coada in banda: o masina se opreste DOAR daca liderul direct
    #    este fizic aproape (gap mic). Nu se propaga in cascada la distanta.
    for c in cars:
        if c.waiting:
            continue
        best_gap = 999
        for other in cars:
            if other is c:
                continue
            if same_lane(c, other) and is_ahead_in_lane(other, c):
                g = gap_to_leader(other, c)
                if g < best_gap:
                    best_gap = g
        if best_gap < FOLLOW_GAP:
            c.waiting = True


# ──────────────────────────────────────────────────────────────
#  SPAWN
# ──────────────────────────────────────────────────────────────
SPAWN_INTERVAL = 110
spawn_timer = 0

def spawn_car(cars):
    pool = (
        [('right', i) for i in range(len(ROW_Y))] +
        [('left',  i) for i in range(len(ROW_Y))] +
        [('down',  i) for i in range(len(COL_X))] +
        [('up',    i) for i in range(len(COL_X))]
    )
    random.shuffle(pool)
    for d, li in pool:
        candidate = Car(d, li)
        if not any(candidate.rect.inflate(14, 14).colliderect(c.rect) for c in cars):
            cars.append(candidate)
            return


# ──────────────────────────────────────────────────────────────
#  DESENARE
# ──────────────────────────────────────────────────────────────
def draw_roads(surface):
    surface.fill(GREEN_LAND)
    for ry in ROW_Y:
        pygame.draw.rect(surface, GRAY, (0, ry - ROAD_WIDTH//2, WIDTH, ROAD_WIDTH))
        pygame.draw.line(surface, YELLOW, (0, ry), (WIDTH, ry), 2)
    for cx in COL_X:
        pygame.draw.rect(surface, GRAY, (cx - ROAD_WIDTH//2, 0, ROAD_WIDTH, HEIGHT))
        pygame.draw.line(surface, YELLOW, (cx, 0), (cx, HEIGHT), 2)
    for col in range(len(COL_X)):
        for row in range(len(ROW_Y)):
            pygame.draw.rect(surface, DARK_GRAY, intersection_rect(col, row))


font_small = pygame.font.SysFont("consolas", 14)

def draw_hud(surface, cars):
    waiting = sum(1 for c in cars if c.waiting)
    lines = [
        f"Masini: {len(cars)}",
        f"  Mers: {len(cars)-waiting}",
        f"  Stop: {waiting}",
        "",
        "Prioritate de dreapta",
    ]
    bg = pygame.Surface((200, 100), pygame.SRCALPHA)
    bg.fill((0, 0, 0, 140))
    surface.blit(bg, (8, 8))
    for i, t in enumerate(lines):
        s = font_small.render(t, True, (255, 255, 255))
        surface.blit(s, (14, 12 + i*18))
    hint = font_small.render("SPACE = masina noua   ESC = iesire", True, (200, 200, 200))
    surface.blit(hint, (WIDTH//2 - hint.get_width()//2, HEIGHT - 22))


# ──────────────────────────────────────────────────────────────
#  MAIN LOOP
# ──────────────────────────────────────────────────────────────
cars = []
for _ in range(8):
    spawn_car(cars)

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            if event.key == pygame.K_SPACE:
                spawn_car(cars)

    spawn_timer += 1
    if spawn_timer >= SPAWN_INTERVAL:
        spawn_timer = 0
        if len(cars) < 22:
            spawn_car(cars)

    apply_priority(cars)

    for car in cars:
        car.move()

    cars = [c for c in cars if not c.is_off_screen()]

    draw_roads(screen)
    for car in cars:
        car.draw(screen)
    draw_hud(screen, cars)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()