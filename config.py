# ─────────────────────────────────────────────
#  config.py  –  Toate constantele simularii
# ─────────────────────────────────────────────

# ── Fereastra ──────────────────────────────────
WIDTH  = 1270
HEIGHT = 720

# ── Culori ─────────────────────────────────────
GRAY         = (60,  60,  60)
ROAD_COUNTY  = (75,  70,  60)   # asfalt drum judetean
DARK_GRAY    = (40,  40,  40)
DARK_COUNTY  = (50,  48,  40)
YELLOW       = (255, 220,   0)
WHITE_LINE   = (230, 230, 230)
GREEN_LAND   = (34,  120,  34)

CAR_COLORS = [
    (200,  30,  30),   # rosu
    ( 30,  30, 200),   # albastru
    (200, 140,   0),   # portocaliu
    (  0, 180,  80),   # verde
    (180,   0, 180),   # mov
    (  0, 200, 200),   # cyan
    (220,  80,   0),   # portocaliu inchis
    (100,   0, 200),   # violet
]

# ── Dimensiuni drumuri ─────────────────────────
ROAD_WIDTH        = 80    # drum normal  (2 benzi total)
COUNTY_ROAD_WIDTH = 140   # drum judetean (4 benzi – 2 per sens)

# ── Dimensiuni masini ──────────────────────────
CAR_W     = 34   # latime masina normala
CAR_H     = 16   # inaltime masina normala
CAR_W_BIG = 44   # latime masina judetean
CAR_H_BIG = 20   # inaltime masina judetean

# ── Fizica trafic ──────────────────────────────
STOP_MARGIN       = 4    # spatiu intre fata masinii si linia de stop
FOLLOW_GAP        = 6    # spatiu minim fata de masina din fata (coloana)
APPROACH_WIN      = 45   # fereastra normala de detectie (pixeli pana la stop line)
COUNTY_APPROACH_WIN = 200  # fereastra extinsa pentru intersectiile cu judetean
YIELD_TIME_WINDOW = 90   # diferenta maxima de timp de sosire pentru conflict (frame-uri)

# ── Deadlock ───────────────────────────────────
DEADLOCK_DELAY = 180     # frame-uri de asteptare inainte de a debloca (~3s la 60fps)

# ── Grila de drumuri ───────────────────────────
COL_X = [200, 650, 1100]   # coordonate x ale drumurilor verticale
ROW_Y = [120, 390, 620]    # coordonate y ale drumurilor orizontale

# ── Indecsi speciali ───────────────────────────
COUNTY_ROW  = 0   # primul rand orizontal = drum judetean
TRAFFIC_COL = 1   # coloana intersectiei semaforizate
TRAFFIC_ROW = 1   # randul intersectiei semaforizate

# ── Semafor ────────────────────────────────────
# Faze: 0=orizontal verde, 1=galben, 2=vertical verde, 3=galben
PHASE_DURATIONS = [300, 60, 300, 60]   # durata fiecarei faze in frame-uri

# ── Spawn masini ───────────────────────────────
SPAWN_INTERVAL = 100   # frame-uri intre spawn-uri automate
MAX_CARS       = 25
INITIAL_CARS   = 10
