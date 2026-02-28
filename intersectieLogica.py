# traffic_grid_lanes.py
# Simulator Pygame: multiple mașini, grid de intersecții, lane sticking,
# și yield logic îmbunătățit (nu se oprește degeaba).

import pygame
import sys
import random

pygame.init()

# ---------------------------
# Config fereastră & fps
# ---------------------------
WIDTH, HEIGHT = 1000, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Simulare trafic - Lanes & Smart Yield")
FPS = 60
clock = pygame.time.Clock()

# ---------------------------
# Culori & dimensiuni
# ---------------------------
BG = (34, 139, 34)
ROAD = (60, 60, 60)
LINE = (200, 200, 0)
CAR_COLORS = [(200, 20, 20), (20, 60, 200), (200, 160, 0), (120, 0, 120)]
WHITE = (255, 255, 255)

ROAD_WIDTH = 80
CAR_LENGTH = 36
CAR_WIDTH = 18

# offset pentru 'bandă' (vehicule E/W vor sta deasupra/sub centru etc.)
LANE_OFFSET = 18  # pixeli față de centrul drumului pentru a separa direcțiile

# ---------------------------
# Grid intersecții
# ---------------------------
GRID_COLS = 3   # coloane (x)
GRID_ROWS = 2   # rânduri (y)

CELL_W = 220
CELL_H = 220
MARGIN_X = 150
MARGIN_Y = 120

# coordonate centre intersecții (grid)
intersections = []
for r in range(GRID_ROWS):
    for c in range(GRID_COLS):
        cx = MARGIN_X + c * CELL_W
        cy = MARGIN_Y + r * CELL_H
        intersections.append((cx, cy))

INTER_SIZE = ROAD_WIDTH
intersection_rects = [pygame.Rect(x - INTER_SIZE//2, y - INTER_SIZE//2, INTER_SIZE, INTER_SIZE)
                      for (x, y) in intersections]

# mapping right-of (pentru regula de dreapta)
right_of = {
    'E': 'N',
    'N': 'W',
    'W': 'S',
    'S': 'E'
}

# ---------------------------
# Intersection manager (permite multiple intrări non-conflictuale)
# ---------------------------
class Intersection:
    def __init__(self, idx, rect):
        self.idx = idx
        self.rect = rect
        self.occupied_by = set()  # set de vehicle ids

    def can_enter(self, vehicle, vehicles_map):
        """
        Permite intrarea dacă niciun ocupant existent nu are traseu conflictual
        cu vehicle. vehicles_map: dict id->Vehicle pentru a vedea direcțiile occupant.
        """
        for occ_id in self.occupied_by:
            other = vehicles_map.get(occ_id)
            if other and paths_conflict(vehicle.dir, other.dir):
                return False
        return True

    def enter(self, vehicle_id):
        self.occupied_by.add(vehicle_id)

    def leave(self, vehicle_id):
        self.occupied_by.discard(vehicle_id)

intersection_objs = [Intersection(i, r) for i, r in enumerate(intersection_rects)]

# ---------------------------
# Funcții utilitare
# ---------------------------
def paths_conflict(dir1, dir2):
    """
    Returnează True dacă două direcții intră în conflict în interiorul intersecției.
    Simplificare: direcții perpendiculare (E/W vs N/S) se consideră conflictuale.
    Direcții opuse (E vs W sau N vs S) NU se consideră conflictuale în această simulare
    (permit trecerea simultană).
    """
    if dir1 in ('E', 'W') and dir2 in ('N', 'S'):
        return True
    if dir1 in ('N', 'S') and dir2 in ('E', 'W'):
        return True
    return False

# ---------------------------
# Clasa Vehicle
# ---------------------------
class Vehicle:
    _id_counter = 0
    def __init__(self, x, y, direction, lane_index, color):
        self.id = Vehicle._id_counter
        Vehicle._id_counter += 1

        self.x = x
        self.y = y
        self.dir = direction  # 'E','W','N','S'
        self.lane_index = lane_index  # rând (pentru E/W) sau col (pentru N/S)
        self.color = color

        self.speed = 0.0
        self.max_speed = 2.6 if direction in ('E', 'W') else 2.1
        self.acc = 0.08
        self.brake = 0.18

        self.length = CAR_LENGTH
        self.width = CAR_WIDTH

        # plan intersecții pe care le va traversa (lista index-uri)
        self.path = self.compute_path()
        self.next_intersection_idx = None
        self.state = 'moving'  # 'moving', 'stopped', 'in_intersection'

    def compute_path(self):
        # determină lista intersecțiilor pe linia/coloana sa (merge drept)
        path = []
        if self.dir in ('E', 'W'):
            row = self.lane_index
            row_idxs = [row * GRID_COLS + c for c in range(GRID_COLS)]
            if self.dir == 'E':
                path = row_idxs[:]
            else:
                path = row_idxs[::-1]
        else:
            col = self.lane_index
            col_idxs = [r * GRID_COLS + col for r in range(GRID_ROWS)]
            if self.dir == 'S':
                path = col_idxs[:]
            else:
                path = col_idxs[::-1]
        return path

    def rect(self):
        if self.dir in ('E', 'W'):
            return pygame.Rect(self.x, self.y, self.length, self.width)
        else:
            return pygame.Rect(self.x, self.y, self.width, self.length)

    def front_pos(self):
        if self.dir == 'E':
            return (self.x + self.length, self.y + self.width/2)
        if self.dir == 'W':
            return (self.x, self.y + self.width/2)
        if self.dir == 'N':
            return (self.x + self.width/2, self.y)
        if self.dir == 'S':
            return (self.x + self.width/2, self.y + self.length)

    def update(self, dt):
        # actualizează poziția
        if self.dir == 'E':
            self.x += self.speed
        elif self.dir == 'W':
            self.x -= self.speed
        elif self.dir == 'N':
            self.y -= self.speed
        elif self.dir == 'S':
            self.y += self.speed

    def accelerate_towards(self, target_speed):
        if self.speed < target_speed:
            self.speed = min(self.speed + self.acc, target_speed)
        else:
            self.speed = max(self.speed - self.brake, target_speed)

    def is_before_intersection(self, inter_idx):
        cx, cy = intersections[inter_idx]
        half = INTER_SIZE//2
        if self.dir == 'E':
            entry_x = cx - half
            return (self.x + self.length) <= entry_x
        if self.dir == 'W':
            entry_x = cx + half
            return self.x >= entry_x
        if self.dir == 'N':
            entry_y = cy + half
            return self.y >= entry_y
        if self.dir == 'S':
            entry_y = cy - half
            return (self.y + self.length) <= entry_y
        return False

    def distance_to_intersection_front(self, inter_idx):
        cx, cy = intersections[inter_idx]
        half = INTER_SIZE//2
        fx, fy = self.front_pos()
        if self.dir == 'E':
            entry_x = cx - half
            return entry_x - fx
        if self.dir == 'W':
            entry_x = cx + half
            return fx - entry_x
        if self.dir == 'N':
            entry_y = cy + half
            return fy - entry_y
        if self.dir == 'S':
            entry_y = cy - half
            return entry_y - fy
        return float('inf')

# ---------------------------
# Gestionare vehicule + spawn
# ---------------------------
vehicles = []
vehicles_map = {}  # id -> vehicle (folosit pentru verificări rapide)

SPAWN_INTERVAL = 900  # ms
MAX_VEHICLES = 40
last_spawn_time = pygame.time.get_ticks()

def spawn_vehicle_edge():
    side = random.choice(['left', 'right', 'top', 'bottom'])
    color = random.choice(CAR_COLORS)
    if side == 'left':
        # vine din stânga spre E -> alege un rând
        row = random.randrange(0, GRID_ROWS)
        cx, cy = intersections[row * GRID_COLS + 0]
        # plasare pe banda "E" (deasupra centrului)
        y = cy - LANE_OFFSET - CAR_WIDTH/2
        x = -80 - random.uniform(0, 160)
        v = Vehicle(x, y, 'E', row, color)
    elif side == 'right':
        row = random.randrange(0, GRID_ROWS)
        cx_last = intersections[row * GRID_COLS + (GRID_COLS-1)][0]
        y = intersections[row * GRID_COLS + 0][1] + LANE_OFFSET - CAR_WIDTH/2
        x = WIDTH + random.uniform(20, 160)
        v = Vehicle(x, y, 'W', row, color)
    elif side == 'top':
        col = random.randrange(0, GRID_COLS)
        x = intersections[col][0] - LANE_OFFSET - CAR_WIDTH/2
        y = -80 - random.uniform(0, 160)
        v = Vehicle(x, y, 'S', col, color)
    else:  # bottom
        col = random.randrange(0, GRID_COLS)
        x = intersections[(GRID_ROWS-1) * GRID_COLS + col][0] + LANE_OFFSET - CAR_WIDTH/2
        y = HEIGHT + random.uniform(20, 160)
        v = Vehicle(x, y, 'N', col, color)

    vehicles.append(v)
    vehicles_map[v.id] = v

# ---------------------------
# Parametri yield
# ---------------------------
YIELD_DIST = 48  # pixeli distanța la intrare când se ia decizia de yield
SAFETY_MARGIN = 8  # pixeli

# ---------------------------
# Game loop
# ---------------------------
running = True

while running:
    dt = clock.tick(FPS) / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # spawn periodic
    now = pygame.time.get_ticks()
    if now - last_spawn_time >= SPAWN_INTERVAL and len(vehicles) < MAX_VEHICLES:
        spawn_vehicle_edge()
        last_spawn_time = now

    # 1) determinăm next_intersection pentru fiecare vehicul
    for v in vehicles:
        next_idx = None
        for inter_idx in v.path:
            if v.is_before_intersection(inter_idx):
                next_idx = inter_idx
                break
        v.next_intersection_idx = next_idx

    # 2) decidem viteza țintă pentru fiecare vehicul pe baza regulilor
    for v in vehicles:
        target_speed = v.max_speed

        if v.next_intersection_idx is None:
            v.accelerate_towards(target_speed)
            continue

        inter_idx = v.next_intersection_idx
        inter_obj = intersection_objs[inter_idx]

        # Dacă intersecția are ocupanți conflictuali -> oprești (dacă ești înainte)
        if not inter_obj.can_enter(v, vehicles_map) and v.is_before_intersection(inter_idx):
            target_speed = 0.0
        else:
            # căutăm ceilalți care au aceeași next_intersection (posibili contendere)
            contenders = [o for o in vehicles if o is not v and getattr(o, 'next_intersection_idx', None) == inter_idx]

            must_yield = False
            for other in contenders:
                # considerăm doar alții a căror traiectorie conflictă cu a ta
                if not paths_conflict(v.dir, other.dir):
                    # nu conflict la traseu -> nu ceda pentru ei
                    continue

                # dacă other este pe dreapta ta (regula de dreapta)
                if other.dir == right_of.get(v.dir):
                    d_self = v.distance_to_intersection_front(inter_idx)
                    d_other = other.distance_to_intersection_front(inter_idx)

                    # other trebuie să fie într-o poziție în care intrarea lui e probabilă
                    # (mai aproape decât tine sau în intervalul YIELD_DIST)
                    if other.is_before_intersection(inter_idx) and (d_other < max(YIELD_DIST, d_self - SAFETY_MARGIN)):
                        must_yield = True
                        break

            if must_yield and v.is_before_intersection(inter_idx):
                target_speed = 0.0
            else:
                target_speed = v.max_speed

        v.accelerate_towards(target_speed)

    # 3) actualizăm pozițiile, tratăm intrarea/ieșirea din intersecții
    for v in list(vehicles):
        prev_rect = v.rect()
        v.update(dt)
        cur_rect = v.rect()

        # verificăm coliziunea cu fiecare intersecție
        for inter in intersection_objs:
            if cur_rect.colliderect(inter.rect):
                # încearcă să intre — dacă poate, ocupă; altfel, frânează și revine puțin
                if inter.can_enter(v, vehicles_map) or (v.id in inter.occupied_by):
                    if v.id not in inter.occupied_by:
                        inter.enter(v.id)
                    v.state = 'in_intersection'
                else:
                    # nu are voie să intre: frânăm (corectiv — poziționare puțin înainte)
                    v.speed = 0.0
                    v.state = 'stopped'
                    # corecție: împingem vehiculul ușor înapoi, pentru a nu rămâne intersectat de rect
                    # (doar dacă a pătruns un pic)
                    # readaptare în funcție de direcție
                    if v.dir == 'E':
                        v.x = min(v.x, inter.rect.left - v.length - 1)
                    elif v.dir == 'W':
                        v.x = max(v.x, inter.rect.right + 1)
                    elif v.dir == 'N':
                        v.y = max(v.y, inter.rect.bottom + 1)
                    elif v.dir == 'S':
                        v.y = min(v.y, inter.rect.top - v.length - 1)

            else:
                # dacă a părăsit intersecția pe care o ocupase, eliberăm
                if v.id in inter.occupied_by and not cur_rect.colliderect(inter.rect):
                    inter.leave(v.id)
                    v.state = 'moving'

        # eliminăm vehicule offscreen (fără re-spawn)
        off_left = (v.x + v.length) < -300
        off_right = v.x > WIDTH + 300
        off_top = (v.y + v.length) < -300
        off_bottom = v.y > HEIGHT + 300
        if off_left or off_right or off_top or off_bottom:
            # eliberăm orice intersecție ocupată
            for inter in intersection_objs:
                if v.id in inter.occupied_by:
                    inter.leave(v.id)
            vehicles.remove(v)
            vehicles_map.pop(v.id, None)

    # -------------------------
    # 4) Desenare
    # -------------------------
    screen.fill(BG)

    # desen drumuri orizontale (pentru fiecare rând)
    for r in range(GRID_ROWS):
        y = MARGIN_Y + r * CELL_H
        pygame.draw.rect(screen, ROAD, (0, y - ROAD_WIDTH//2, WIDTH, ROAD_WIDTH))
        pygame.draw.line(screen, LINE, (0, y), (WIDTH, y), 2)

    # desen drumuri verticale (pentru fiecare coloană)
    for c in range(GRID_COLS):
        x = MARGIN_X + c * CELL_W
        pygame.draw.rect(screen, ROAD, (x - ROAD_WIDTH//2, 0, ROAD_WIDTH, HEIGHT))
        pygame.draw.line(screen, LINE, (x, 0), (x, HEIGHT), 2)

    # desen intersecții (contur diferit dacă ocupată)
    for inter in intersection_objs:
        rect = inter.rect
        color = (180, 50, 50) if len(inter.occupied_by) > 0 else (100, 100, 100)
        pygame.draw.rect(screen, color, rect)

    # desen vehicule
    for v in vehicles:
        r = v.rect()
        pygame.draw.rect(screen, v.color, r)
        fx, fy = v.front_pos()
        pygame.draw.circle(screen, WHITE, (int(fx), int(fy)), 2)

    # text info
    font = pygame.font.SysFont(None, 20)
    txt = font.render(f"Vehicule: {len(vehicles)}  | Grid: {GRID_COLS}x{GRID_ROWS}", True, WHITE)
    screen.blit(txt, (10, 10))

    pygame.display.flip()

pygame.quit()
sys.exit()