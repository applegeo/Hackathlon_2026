# ─────────────────────────────────────────────────────────────────────────────
#  pretrain.py  –  Preantrenare offline pe pNEUMA (versiune rapida)
#
#  Foloseste train_offline() din agent.py care proceseaza batch-uri intregi
#  cu NumPy → mult mai rapid decat versiunea originala.
#
#  UTILIZARE:
#    python pretrain.py
# ─────────────────────────────────────────────────────────────────────────────

import os
import json
import math
import random
import numpy as np

from agent import SharedDQN, STATE_SIZE, BATCH_SIZE, PERCEPTION_RADIUS

DATA_DIR     = os.path.join("data", "pNEUMA")
OUTPUT_MODEL = os.path.join("data", "dqn_pretrained.json")
MAX_FILES    = 3
MAX_TRACKS   = 500
EPOCHS       = 5

SIM_WIDTH, SIM_HEIGHT = 1270, 720
LAT_MIN, LAT_MAX = 37.975, 37.995
LON_MIN, LON_MAX = 23.720, 23.745
STOP_SPEED_THRESHOLD = 0.5

PNEUMA_TYPES = {
    "Car": "car", "Motorcycle": "car", "Taxi": "car",
    "Bus": "car", "Heavy Vehicle": "car", "Medium Vehicle": "car",
}


# ─────────────────────────────────────────────────────────────────────────────

def find_csv_files(data_dir):
    if not os.path.exists(data_dir):
        print(f"[EROARE] Folderul '{data_dir}' nu exista!")
        print("  mkdir -p data/pNEUMA  si pune fisierele CSV acolo.")
        print("  https://zenodo.org/record/7426506")
        return []
    files = [
        os.path.join(data_dir, f)
        for f in sorted(os.listdir(data_dir)) if f.endswith(".csv")
    ]
    return files


def parse_pneuma_csv(filepath, max_tracks=MAX_TRACKS):
    tracks = {}
    print(f"  Citesc: {os.path.basename(filepath)}")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f):
                if line_num == 0:
                    continue
                parts = line.strip().split(";")
                if len(parts) < 10:
                    continue
                try:
                    track_id = int(float(parts[0].strip()))
                    veh_type = parts[1].strip()
                    points   = []
                    for i in range(4, len(parts) - 5, 6):
                        try:
                            lat   = float(parts[i].strip())
                            lon   = float(parts[i+1].strip())
                            speed = float(parts[i+2].strip())
                            t     = float(parts[i+5].strip())
                            if lat != 0 and lon != 0:
                                points.append({"lat": lat, "lon": lon,
                                               "speed": speed, "time": t,
                                               "type": PNEUMA_TYPES.get(veh_type, "car")})
                        except (ValueError, IndexError):
                            continue
                    if len(points) >= 3:
                        tracks[track_id] = points
                        if len(tracks) >= max_tracks:
                            break
                except (ValueError, IndexError):
                    continue
    except Exception as e:
        print(f"  [WARN] {e}")
    print(f"  → {len(tracks)} traiectorii")
    return tracks


def gps_to_sim(lat, lon):
    nx = (lon - LON_MIN) / (LON_MAX - LON_MIN)
    ny = (lat - LAT_MIN) / (LAT_MAX - LAT_MIN)
    return nx * SIM_WIDTH, (1.0 - ny) * SIM_HEIGHT


def infer_direction(points):
    n = min(5, len(points) // 2)
    s_lat = sum(p["lat"] for p in points[:n]) / n
    s_lon = sum(p["lon"] for p in points[:n]) / n
    e_lat = sum(p["lat"] for p in points[-n:]) / n
    e_lon = sum(p["lon"] for p in points[-n:]) / n
    dlat, dlon = e_lat - s_lat, e_lon - s_lon
    if abs(dlon) >= abs(dlat):
        return "right" if dlon > 0 else "left"
    return "down" if dlat < 0 else "up"


def build_experiences_vectorized(all_tracks: dict) -> list:
    """
    Construieste experientele DQN mai rapid folosind NumPy pentru calcule de distanta.
    """
    experiences = []
    dir_to_int  = {'right': 0.0, 'left': 0.25, 'down': 0.5, 'up': 0.75}
    N_NEIGH     = 5
    track_ids   = list(all_tracks.keys())

    # Pre-calculam pozitiile sim pentru toate trackurile
    track_positions = {}
    track_directions = {}
    for tid, pts in all_tracks.items():
        positions = np.array([gps_to_sim(p["lat"], p["lon"]) for p in pts], dtype=np.float32)
        track_positions[tid]  = positions
        track_directions[tid] = infer_direction(pts)

    print(f"  Construiesc experiente din {len(track_ids)} traiectorii...")

    for idx, tid in enumerate(track_ids):
        if idx % 100 == 0:
            print(f"    {idx}/{len(track_ids)} traiectorii procesate | {len(experiences)} experiente")

        points    = all_tracks[tid]
        positions = track_positions[tid]
        direction = track_directions[tid]
        dir_val   = dir_to_int.get(direction, 0.0)

        for i in range(len(points) - 1):
            x_c, y_c = float(positions[i][0]),   float(positions[i][1])
            x_n, y_n = float(positions[i+1][0]), float(positions[i+1][1])

            spd_c = min(5.0, points[i]["speed"]   / 15.0 * 4.0)
            spd_n = min(5.0, points[i+1]["speed"] / 15.0 * 4.0)
            wait_c = points[i]["speed"]   < STOP_SPEED_THRESHOLD
            wait_n = points[i+1]["speed"] < STOP_SPEED_THRESHOLD

            # Gasim vecinii apropiati la acelasi moment de timp (vectorizat)
            state_c = [0.0] * (N_NEIGH * 6)
            neighbor_count = 0

            for other_id, other_pts in all_tracks.items():
                if other_id == tid or neighbor_count >= N_NEIGH:
                    break
                # Punct cel mai aproape in timp
                t_curr = points[i]["time"]
                times  = np.array([p["time"] for p in other_pts], dtype=np.float32)
                closest_idx = int(np.argmin(np.abs(times - t_curr)))
                if abs(times[closest_idx] - t_curr) > 2.0:
                    continue
                ox = float(track_positions[other_id][closest_idx][0])
                oy = float(track_positions[other_id][closest_idx][1])
                dist = math.hypot(ox - x_c, oy - y_c)
                if dist > PERCEPTION_RADIUS:
                    continue

                o_spd  = min(5.0, other_pts[closest_idx]["speed"] / 15.0 * 4.0)
                o_dir  = dir_to_int.get(track_directions[other_id], 0.0)
                o_wait = other_pts[closest_idx]["speed"] < STOP_SPEED_THRESHOLD

                off = neighbor_count * 6
                state_c[off]   = max(-1.0, min(1.0, (ox - x_c) / PERCEPTION_RADIUS))
                state_c[off+1] = max(-1.0, min(1.0, (oy - y_c) / PERCEPTION_RADIUS))
                state_c[off+2] = max(0.0,  min(1.0, o_spd / 5.0))
                state_c[off+3] = o_dir
                state_c[off+4] = 1.0 if o_wait else 0.0
                state_c[off+5] = 0.0  # nu stim daca e judetean
                neighbor_count += 1

            # Semafor inferrat + distanta + directie + judetean
            dist_to_int = math.hypot(x_c - SIM_WIDTH/2, y_c - SIM_HEIGHT/2)
            tl_val = 1.0 if (dist_to_int < 30 and wait_c) else (0.5 if (dist_to_int < 60 and spd_c < 1.0) else 0.0)

            state_c += [tl_val, min(1.0, dist_to_int / 300.0), dir_val, 0.0]
            state_n  = state_c.copy()  # simplificat pentru starea urmatoare

            action = 1 if wait_c else 0
            reward = -0.2 if wait_c else 0.5
            if dist_to_int < 80 and not wait_c:
                reward += 1.0

            done = (i == len(points) - 2)
            experiences.append((state_c, action, reward, state_n, done))

    return experiences


def save_model(dqn: SharedDQN, filepath: str):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    data = {
        "q_net":      dqn.q_net.get_params(),
        "target_net": dqn.target_net.get_params(),
        "epsilon":    dqn.epsilon,
        "steps":      dqn.steps,
        "trained_on": "pNEUMA",
    }
    with open(filepath, "w") as f:
        json.dump(data, f)
    print(f"[SAVE] Model salvat: {filepath} ({os.path.getsize(filepath)//1024} KB)")


def load_model(dqn: SharedDQN, filepath: str) -> bool:
    if not os.path.exists(filepath):
        return False
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
        dqn.q_net.set_params(data["q_net"])
        dqn.target_net.set_params(data["target_net"])
        dqn.epsilon = float(data.get("epsilon", 0.1))
        dqn.steps   = int(data.get("steps", 0))
        print(f"[LOAD] Model preantrenat incarcat: {filepath} | Epsilon: {dqn.epsilon:.3f}")
        return True
    except Exception as e:
        print(f"[WARN] Nu s-a putut incarca: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  pNEUMA Pretraining (versiune rapida cu NumPy)")
    print("=" * 60)

    csv_files = find_csv_files(DATA_DIR)
    if not csv_files:
        exit(1)

    all_tracks = {}
    for f in csv_files[:MAX_FILES]:
        all_tracks.update(parse_pneuma_csv(f, MAX_TRACKS))
    print(f"\nTotal traiectorii: {len(all_tracks)}")

    experiences = build_experiences_vectorized(all_tracks)
    print(f"Total experiente: {len(experiences)}")

    if len(experiences) < BATCH_SIZE:
        print("[EROARE] Prea putine date.")
        exit(1)

    dqn = SharedDQN()
    print("\n[PRETRAIN] Start antrenament offline...")
    dqn.train_offline(experiences, epochs=EPOCHS, verbose=True)

    save_model(dqn, OUTPUT_MODEL)
    print("\nGata! Ruleaza main.py.")
