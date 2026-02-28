# ─────────────────────────────────────────────
#  agent.py  –  Agent DQN optimizat
#
#  Imbunatatiri fata de versiunea originala:
#    1. train_step() foloseste forward_batch() / backward_batch() din NeuralNet
#       → un singur forward pe tot batch-ul in loc de 32 forward-uri individuale
#    2. TRAIN_EVERY = 4 → antreneaza o data la 4 frame-uri (nu la fiecare frame)
#    3. BATCH_SIZE marit la 64
#    4. Perceptia returneaza np.array direct (evita conversii repetate)
#    5. Offline pretrain helper: train_offline(experiences, epochs)
# ─────────────────────────────────────────────

import random
import math
import numpy as np
from collections import deque
from neural_net import NeuralNet


# ──────────────────────────────────────────────
#  Constante agent
# ──────────────────────────────────────────────

PERCEPTION_RADIUS = 180
N_NEIGHBORS       = 5
STATE_SIZE        = N_NEIGHBORS * 6 + 4
ACTION_SIZE       = 2

GAMMA          = 0.95
LR             = 0.0005
EPSILON_START  = 1.0
EPSILON_MIN    = 0.05
EPSILON_DECAY  = 0.9995
BATCH_SIZE     = 64        # marit de la 32 → mai stabil + mai rapid per pas
MEMORY_SIZE    = 10000     # marit pentru mai multa diversitate
TARGET_UPDATE  = 200
TRAIN_EVERY    = 4         # antreneaza 1 data la 4 frame-uri → ~4x mai rapid

REWARD_MOVE       =  0.5
REWARD_WAIT       = -0.2
REWARD_COLLISION  = -15.0
REWARD_CLEAR_PASS =  2.0


# ──────────────────────────────────────────────
#  Replay Buffer
# ──────────────────────────────────────────────

class ReplayBuffer:
    def __init__(self, capacity: int = MEMORY_SIZE):
        self.buffer = deque(maxlen=capacity)

    def push(self, state, action, reward, next_state, done):
        self.buffer.append((state, action, reward, next_state, done))

    def sample_batch(self, batch_size: int):
        """
        Returneaza batch-ul ca arrays NumPy — gata pentru forward_batch().
        """
        batch   = random.sample(self.buffer, batch_size)
        states      = np.array([b[0] for b in batch], dtype=np.float32)
        actions     = np.array([b[1] for b in batch], dtype=np.int32)
        rewards     = np.array([b[2] for b in batch], dtype=np.float32)
        next_states = np.array([b[3] for b in batch], dtype=np.float32)
        dones       = np.array([b[4] for b in batch], dtype=np.float32)
        return states, actions, rewards, next_states, dones

    def __len__(self):
        return len(self.buffer)


# ──────────────────────────────────────────────
#  Agent DQN shared
# ──────────────────────────────────────────────

class SharedDQN:
    def __init__(self):
        self.q_net      = NeuralNet([STATE_SIZE, 32, 24, ACTION_SIZE])
        self.target_net = NeuralNet([STATE_SIZE, 32, 24, ACTION_SIZE])
        self.target_net.copy_from(self.q_net)

        self.memory  = ReplayBuffer()
        self.epsilon = EPSILON_START
        self.steps   = 0
        self._frame  = 0   # contor pentru TRAIN_EVERY

        self.total_loss     = 0.0
        self.loss_count     = 0
        self.episode_reward = 0.0
        self.total_collisions = 0

    def select_action(self, state) -> int:
        if random.random() < self.epsilon:
            return random.randint(0, ACTION_SIZE - 1)
        q_values = self.q_net.predict(state)
        return int(np.argmax(q_values))

    def store(self, state, action, reward, next_state, done):
        self.memory.push(state, action, reward, next_state, done)
        self.episode_reward += reward

    def train_step(self):
        """
        Antreneaza pe un batch intreg folosind operatii matriciale.
        Apelat o data la TRAIN_EVERY frame-uri.
        """
        self._frame += 1
        if self._frame % TRAIN_EVERY != 0:
            return
        if len(self.memory) < BATCH_SIZE:
            return

        states, actions, rewards, next_states, dones = self.memory.sample_batch(BATCH_SIZE)

        # Q-valorile curente pentru toate starile din batch (un singur forward)
        current_q_all = self.q_net.forward_batch(states)          # (batch, 2)

        # Q-valorile target pentru starile urmatoare (un singur forward)
        next_q_all    = self.target_net.forward_batch(next_states) # (batch, 2)
        next_q_max    = next_q_all.max(axis=1)                     # (batch,)

        # Ecuatia Bellman vectorizata
        target_q_vals = rewards + GAMMA * next_q_max * (1.0 - dones)

        # Construim target complet: copiem Q curent, modificam doar actiunea aleasa
        targets = current_q_all.copy()
        targets[np.arange(BATCH_SIZE), actions] = target_q_vals

        # Un singur backward pe tot batch-ul
        self.q_net.forward_batch(states)   # refacem forward pentru a stoca activarile
        self.q_net.backward_batch(targets, lr=LR)

        # Loss MSE pe actiunile alese
        loss = float(np.mean((current_q_all[np.arange(BATCH_SIZE), actions] - target_q_vals) ** 2))
        self.total_loss += loss
        self.loss_count += 1
        self.steps      += 1

        if self.steps % TARGET_UPDATE == 0:
            self.target_net.copy_from(self.q_net)

        if self.epsilon > EPSILON_MIN:
            self.epsilon *= EPSILON_DECAY

    def train_offline(self, experiences: list, epochs: int = 5, verbose: bool = True):
        """
        Antreneaza offline pe o lista de experiente (ex: din pNEUMA).
        Mai rapid decat train_step() individual — proceseaza tot buffer-ul
        in batch-uri mari.
        """
        # Incarca toate experientele in buffer
        for exp in experiences:
            self.memory.push(*exp)

        self.epsilon = 0.1   # explorare mica la preantrenare

        total_batches = max(100, len(experiences) // BATCH_SIZE)

        for epoch in range(epochs):
            epoch_loss = 0.0
            for _ in range(total_batches):
                if len(self.memory) < BATCH_SIZE:
                    break

                states, actions, rewards, next_states, dones = self.memory.sample_batch(BATCH_SIZE)

                next_q  = self.target_net.forward_batch(next_states).max(axis=1)
                tgt_val = rewards + GAMMA * next_q * (1.0 - dones)

                cur_q   = self.q_net.forward_batch(states)
                targets = cur_q.copy()
                targets[np.arange(BATCH_SIZE), actions] = tgt_val

                self.q_net.forward_batch(states)
                self.q_net.backward_batch(targets, lr=LR)

                epoch_loss += float(np.mean(
                    (cur_q[np.arange(BATCH_SIZE), actions] - tgt_val) ** 2
                ))
                self.steps += 1

            if self.steps % TARGET_UPDATE == 0:
                self.target_net.copy_from(self.q_net)

            if verbose:
                avg = epoch_loss / max(1, total_batches)
                print(f"  Epoch {epoch+1}/{epochs} | Loss: {avg:.5f} | Epsilon: {self.epsilon:.3f}")

    @property
    def avg_loss(self) -> float:
        return self.total_loss / max(1, self.loss_count)

    def reset_stats(self):
        self.total_loss     = 0.0
        self.loss_count     = 0
        self.episode_reward = 0.0


# ──────────────────────────────────────────────
#  Perceptie agent
# ──────────────────────────────────────────────

def perceive(car, all_cars: list, traffic_light, intersection_rects: list) -> list:
    dir_to_int = {'right': 0.0, 'left': 0.25, 'down': 0.5, 'up': 0.75}

    cx, cy = car.rect.centerx, car.rect.centery

    # Sortam vecinii dupa distanta euclidiana (evitam sqrt cu distanta patrata)
    others = [c for c in all_cars if c is not car]
    others.sort(key=lambda c: (c.rect.centerx - cx)**2 + (c.rect.centery - cy)**2)

    state = []
    for i in range(N_NEIGHBORS):
        if i < len(others):
            o    = others[i]
            dx   = max(-1.0, min(1.0, (o.x - car.x) / PERCEPTION_RADIUS))
            dy   = max(-1.0, min(1.0, (o.y - car.y) / PERCEPTION_RADIUS))
            spd  = max(0.0, min(1.0, o.speed / 5.0))
            dire = dir_to_int.get(o.direction, 0.0)
            wait = 1.0 if o.waiting else 0.0
            cnty = 1.0 if o.on_county_road() else 0.0
            state.extend([dx, dy, spd, dire, wait, cnty])
        else:
            state.extend([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

    tl_state = traffic_light.state_for(car.direction)
    tl_val   = {'green': 0.0, 'yellow': 0.5, 'red': 1.0}.get(tl_state, 0.0)
    state.append(tl_val)

    min_dist = 1.0
    for ir in intersection_rects:
        if car.is_before(ir):
            d = car.dist_to_stop(ir)
            if 0 <= d:
                norm = max(0.0, min(1.0, d / 300.0))
                if norm < min_dist:
                    min_dist = norm
    state.append(min_dist)
    state.append(dir_to_int.get(car.direction, 0.0))
    state.append(1.0 if car.on_county_road() else 0.0)

    return state


def compute_reward(car, all_cars: list, prev_intersections_passed: int) -> tuple:
    reward = 0.0
    done   = False

    for other in all_cars:
        if other is car:
            continue
        if car.rect.inflate(-4, -4).colliderect(other.rect.inflate(-4, -4)):
            return REWARD_COLLISION, True

    reward += REWARD_WAIT if car.waiting else REWARD_MOVE

    if car.intersections_passed > prev_intersections_passed:
        reward += REWARD_CLEAR_PASS

    return reward, done
