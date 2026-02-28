# ─────────────────────────────────────────────
#  priority.py  –  Reguli hard de trafic
#
#  Contine DOAR regulile absolute (semafor, judetean, coloana).
#  Prioritatea de dreapta este invatata de agentii DQN.
# ─────────────────────────────────────────────

import random
from config import (
    COL_X, ROW_Y,
    COUNTY_APPROACH_WIN, YIELD_TIME_WINDOW,
    FOLLOW_GAP,
    COUNTY_ROW, TRAFFIC_COL, TRAFFIC_ROW,
)
from road import intersection_rect, road_width_for_col, road_width_for_row
from car import Car


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
    return 999.0

def time_to_arrive(car, ir):
    d = car.dist_to_stop(ir)
    return 0.0 if d <= 0 else d / car.speed

def next_intersection_matches(car, col, row):
    if car.direction in ('right', 'left'):
        if car.lane_index != row: return False
        if car.direction == 'right':
            cands = [c for c in range(len(COL_X)) if COL_X[c] - road_width_for_col(c)//2 > car.x + car.w - 2]
        else:
            cands = [c for c in range(len(COL_X)) if COL_X[c] + road_width_for_col(c)//2 < car.x + 2]
            cands = list(reversed(cands))
        return bool(cands) and cands[0] == col
    else:
        if car.lane_index != col: return False
        if car.direction == 'down':
            cands = [r for r in range(len(ROW_Y)) if ROW_Y[r] - road_width_for_row(r)//2 > car.y + car.h - 2]
        else:
            cands = [r for r in range(len(ROW_Y)) if ROW_Y[r] + road_width_for_row(r)//2 < car.y + 2]
            cands = list(reversed(cands))
        return bool(cands) and cands[0] == row


def _apply_traffic_light(near, traffic_light):
    for c in near:
        if traffic_light.must_stop(c.direction):
            c.waiting = True


def _apply_county_priority(relevant, in_int, ir):
    near_county = [c for c in relevant
                   if not c.is_in(ir) and c.is_before(ir)
                   and c.is_approaching(ir, window=COUNTY_APPROACH_WIN)]
    for c in near_county:
        if c.direction not in ('up', 'down'): continue
        county_cars = [o for o in (near_county + in_int)
                       if o is not c and o.direction in ('right', 'left')]
        for o in county_cars:
            if o in in_int or abs(time_to_arrive(c, ir) - time_to_arrive(o, ir)) <= YIELD_TIME_WINDOW * 3:
                c.waiting = True
                break


def _apply_follow_distance(cars):
    for c in cars:
        if c.waiting: continue
        best_gap = 999.0
        for other in cars:
            if other is c: continue
            if same_lane(c, other) and is_ahead_in_lane(other, c):
                g = gap_to_leader(other, c)
                if g < best_gap: best_gap = g
        if best_gap < FOLLOW_GAP:
            c.waiting = True


def apply_hard_rules(cars, traffic_light):
    """
    Aplica regulile hard: semafor, judetean, coloana in banda.
    Apelata DUPA ce agentii DQN si-au setat propriile decizii,
    pentru ca regulile hard sa le poata suprascrie.
    """
    for col in range(len(COL_X)):
        for row in range(len(ROW_Y)):
            ir = intersection_rect(col, row)
            is_traffic = (col == TRAFFIC_COL and row == TRAFFIC_ROW)
            is_county  = (row == COUNTY_ROW)

            relevant = [c for c in cars
                        if next_intersection_matches(c, col, row) or c.is_in(ir)]
            in_int   = [c for c in relevant if c.is_in(ir)]
            near     = [c for c in relevant
                        if not c.is_in(ir) and c.is_before(ir)
                        and c.is_approaching(ir, window=45)]

            if is_traffic and near:
                _apply_traffic_light(near, traffic_light)
            elif is_county:
                _apply_county_priority(relevant, in_int, ir)

    _apply_follow_distance(cars)


def spawn_car(cars, shared_dqn=None):
    pool = (
        [('right', i) for i in range(len(ROW_Y))] +
        [('left',  i) for i in range(len(ROW_Y))] +
        [('down',  i) for i in range(len(COL_X))] +
        [('up',    i) for i in range(len(COL_X))]
    )
    random.shuffle(pool)
    for direction, lane_index in pool:
        candidate = Car(direction, lane_index, shared_dqn=shared_dqn)
        if not any(candidate.rect.inflate(14, 14).colliderect(c.rect) for c in cars):
            cars.append(candidate)
            return
