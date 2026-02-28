# ─────────────────────────────────────────────
#  main.py  –  Bucla principala
#
#  Flux per frame:
#    1. Evenimente pygame
#    2. Perceptie: fiecare agent isi construieste starea
#    3. Decizie:   agentul alege actiunea (DQN sau explorare)
#    4. Reguli hard: semafor, judetean, coloana (pot suprascrie decizia)
#    5. Miscare
#    6. Recompensa + stocare experienta in replay buffer
#    7. Antrenament DQN (un batch per frame)
#    8. Desenare
#
#  Persistenta model:
#    - La pornire:   incarca automat inchidere/dqn_pretrained.json
#    - La inchidere: salveaza automat inchidere/dqn_pretrained.json
#    - La fiecare ~60s: autosave silentios
#    - Tasta S: salveaza manual
#    - Tasta R: reseteaza modelul la zero
# ─────────────────────────────────────────────

import pygame
import sys
import os
import json

from config import (
    WIDTH, HEIGHT,
    MAX_CARS,
    TRAFFIC_COL, TRAFFIC_ROW, COL_X, ROW_Y,
)
from road import intersection_rect
from traffic_light import TrafficLight
from priority import apply_hard_rules, spawn_car
from renderer import draw_roads, draw_hud
from agent import SharedDQN, perceive, compute_reward

# ── Calea unica pentru model ──────────────────
# Calea absoluta catre folderul "inchidere" aflat langa main.py
# Functioneaza indiferent din ce director rulezi scriptul
BASE_DIR          = os.path.dirname(os.path.abspath(__file__))
INCHIDERE_DIR     = os.path.join(BASE_DIR, "inchidere")
os.makedirs(INCHIDERE_DIR, exist_ok=True)
MODEL_PATH        = os.path.join(INCHIDERE_DIR, "dqn_pretrained.json")
AUTOSAVE_INTERVAL = 3600   # frame-uri (~60s la 60fps)


def save_model(dqn, filepath, silent=False):
    data = {
        "q_net":            dqn.q_net.get_params(),
        "target_net":       dqn.target_net.get_params(),
        "epsilon":          dqn.epsilon,
        "steps":            dqn.steps,
        "total_collisions": dqn.total_collisions,
    }
    with open(filepath, "w") as f:
        json.dump(data, f)
    if not silent:
        kb = os.path.getsize(filepath) // 1024
        print(f"[SAVE] {filepath}  ({kb} KB | {dqn.steps} steps | epsilon={dqn.epsilon:.3f})")


def load_model(dqn, filepath):
    if not os.path.exists(filepath):
        return False
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
        dqn.q_net.set_params(data["q_net"])
        dqn.target_net.set_params(data["target_net"])
        dqn.epsilon          = float(data.get("epsilon", 0.1))
        dqn.steps            = int(data.get("steps", 0))
        dqn.total_collisions = int(data.get("total_collisions", 0))
        return True
    except Exception as e:
        print(f"[WARN] Nu s-a putut incarca {filepath}: {e}")
        return False


pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Simulare Trafic - Agenti DQN")
clock  = pygame.time.Clock()

traffic_light = TrafficLight()
shared_dqn    = SharedDQN()
shared_dqn.total_collisions = 0

if load_model(shared_dqn, MODEL_PATH):
    print(f"[MAIN] Model incarcat din: {MODEL_PATH}")
    print(f"       Steps: {shared_dqn.steps} | Epsilon: {shared_dqn.epsilon:.3f} | Coliziuni: {shared_dqn.total_collisions}")
else:
    print(f"[MAIN] {MODEL_PATH} nu exista -> pornire de la zero (epsilon=1.0)")

all_intersection_rects = [
    intersection_rect(col, row)
    for col in range(len(COL_X))
    for row in range(len(ROW_Y))
]

TARGET_CARS    = 10   # numarul de masini care trebuie mentinut tot timpul

cars           = []
autosave_timer = 0
debug_mode     = False

# Genereaza initial TARGET_CARS masini
while len(cars) < TARGET_CARS:
    spawn_car(cars, shared_dqn=shared_dqn)

running = True
while running:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            if event.key == pygame.K_SPACE:
                spawn_car(cars, shared_dqn=shared_dqn)
            if event.key == pygame.K_d:
                debug_mode = not debug_mode
            if event.key == pygame.K_q:
                shared_dqn.reset_stats()
            if event.key == pygame.K_s:
                save_model(shared_dqn, MODEL_PATH)
            if event.key == pygame.K_r:
                shared_dqn = SharedDQN()
                shared_dqn.total_collisions = 0
                save_model(shared_dqn, MODEL_PATH, silent=True)
                print("[MAIN] Model resetat la zero.")

    traffic_light.update()
    autosave_timer += 1

    # Mentine mereu TARGET_CARS masini pe drum
    # Spawneaza imediat cate una pentru fiecare masina disparuta
    while len(cars) < TARGET_CARS:
        spawn_car(cars, shared_dqn=shared_dqn)

    if autosave_timer >= AUTOSAVE_INTERVAL:
        autosave_timer = 0
        save_model(shared_dqn, MODEL_PATH, silent=True)

    for car in cars:
        car.update_intersection_counter(all_intersection_rects)

    for car in cars:
        car.waiting = False

    states  = {}
    actions = {}
    for car in cars:
        state  = perceive(car, cars, traffic_light, all_intersection_rects)
        action = car.decide(state)
        states[car.id]  = state
        actions[car.id] = action
        car.apply_action(action)

    apply_hard_rules(cars, traffic_light)

    prev_passed = {car.id: car.intersections_passed for car in cars}
    for car in cars:
        car.move()

    to_remove = []
    for car in cars:
        if car.shared_dqn is None:
            continue

        reward, done = compute_reward(car, cars, prev_passed[car.id])
        if done:
            shared_dqn.total_collisions += 1

        next_state = perceive(car, cars, traffic_light, all_intersection_rects)

        if car.prev_state is not None:
            shared_dqn.store(
                car.prev_state,
                car.prev_action,
                reward,
                next_state,
                done or car.is_off_screen()
            )

        car.prev_state  = states[car.id]
        car.prev_action = actions[car.id]

        if done:
            to_remove.append(car)

    for car in to_remove:
        if car in cars:
            cars.remove(car)

    shared_dqn.train_step()

    cars = [c for c in cars if not c.is_off_screen()]

    draw_roads(screen)

    traffic_ir = intersection_rect(TRAFFIC_COL, TRAFFIC_ROW)
    traffic_light.draw(screen, traffic_ir)

    for car in cars:
        car.draw(screen, debug=debug_mode)

    draw_hud(screen, cars, traffic_light, shared_dqn, debug_mode)

    pygame.display.flip()
    clock.tick(60)

# Salvare automata la inchidere
save_model(shared_dqn, MODEL_PATH)
print("[MAIN] Sesiune salvata in", MODEL_PATH)

pygame.quit()
sys.exit()
