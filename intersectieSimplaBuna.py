import pygame
import sys

pygame.init()

WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Intersecție - Prioritate de dreapta corectă")

GRAY = (50, 50, 50)
WHITE = (255, 255, 255)
YELLOW = (255, 255, 0)
RED = (200, 0, 0)
BLUE = (0, 0, 200)
GREEN = (34, 139, 34)

ROAD_WIDTH = 100
CAR_WIDTH = 40
CAR_HEIGHT = 20

clock = pygame.time.Clock()

# Zona intersecției
ix = WIDTH // 2 - ROAD_WIDTH // 2
iy = HEIGHT // 2 - ROAD_WIDTH // 2
intersection_rect = pygame.Rect(ix, iy, ROAD_WIDTH, ROAD_WIDTH)

# =========================
# Masina 1 (vine din stânga)
# =========================
car1_x = -CAR_WIDTH
car1_y = HEIGHT // 2 - CAR_HEIGHT - 10
car1_speed = 2.5

# =========================
# Masina 2 (vine din jos)
# =========================
car2_x = WIDTH // 2 + 10
car2_y = HEIGHT + 40
car2_speed = 2

STOP_MARGIN = 5
car1_stop_line = ix - CAR_WIDTH - STOP_MARGIN
car2_stop_line = iy + ROAD_WIDTH + STOP_MARGIN

running = True
while running:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    car1_rect = pygame.Rect(car1_x, car1_y, CAR_WIDTH, CAR_HEIGHT)
    car2_rect = pygame.Rect(car2_x, car2_y, CAR_HEIGHT, CAR_WIDTH)

    # === STARE INTERSECȚIE ===
    car1_in = car1_rect.colliderect(intersection_rect)
    car2_in = car2_rect.colliderect(intersection_rect)

    car1_stop = False
    car2_stop = False

    # Dacă una este deja în intersecție, cealaltă așteaptă
    if car1_in and not car2_in:
        car2_stop = True
    if car2_in and not car1_in:
        car1_stop = True

    # Dacă ambele sunt în afara intersecției
    if not car1_in and not car2_in:

        car1_near = car1_x + CAR_WIDTH >= car1_stop_line
        car2_near = car2_y <= car2_stop_line

        # Mașina albastră vine din dreapta celei roșii
        # → are prioritate
        if car1_near and car2_near:
            car1_stop = True

    # =========================
    # MISCARE CONTROLATA
    # =========================

    # --- Masina 1 (vine din stanga) ---
    car1_before_intersection = car1_x + CAR_WIDTH <= ix

    if car1_stop and car1_before_intersection and car1_x + CAR_WIDTH >= car1_stop_line:
        pass  # oprește
    else:
        car1_x += car1_speed

    # --- Masina 2 (vine din jos) ---
    car2_before_intersection = car2_y >= iy + ROAD_WIDTH

    if car2_stop and car2_before_intersection and car2_y <= car2_stop_line:
        pass  # oprește
    else:
        car2_y -= car2_speed

    # =========================
    # DESENARE
    # =========================
    screen.fill(GREEN)

    # Drum orizontal
    pygame.draw.rect(screen, GRAY,
                     (0, HEIGHT//2 - ROAD_WIDTH//2, WIDTH, ROAD_WIDTH))

    # Drum vertical
    pygame.draw.rect(screen, GRAY,
                     (WIDTH//2 - ROAD_WIDTH//2, 0, ROAD_WIDTH, HEIGHT))

    pygame.draw.line(screen, YELLOW,
                     (0, HEIGHT//2),
                     (WIDTH, HEIGHT//2), 2)

    pygame.draw.rect(screen, RED,
                     (car1_x, car1_y, CAR_WIDTH, CAR_HEIGHT))

    pygame.draw.rect(screen, BLUE,
                     (car2_x, car2_y, CAR_HEIGHT, CAR_WIDTH))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()