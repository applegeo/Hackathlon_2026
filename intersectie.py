import pygame
import sys

# 1. Inițializare Pygame
pygame.init()

# Configurații ecran
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Intersecție Simplă")

# Culori
GRAY = (50, 50, 50)
WHITE = (255, 255, 255)
YELLOW = (255, 255, 0)
RED = (200, 0, 0)
BLUE = (0, 0, 200)

# Configurații drum
ROAD_WIDTH = 100
ROAD_COLOR = GRAY

# Configurații mașini
CAR_WIDTH = 40
CAR_HEIGHT = 20
car1_x, car1_y = 0, HEIGHT // 2 - CAR_HEIGHT - 10 # Mașină pe orizontală
car2_x, car2_y = WIDTH // 2 + 10, HEIGHT # Mașină pe verticală

clock = pygame.time.Clock()

# --- Game Loop ---
running = True
while running:
    # 2. Gestionare Evenimente
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # 3. Actualizare Poziții (Mișcarea mașinilor)
    car1_x += 3
    car2_y -= 2

    # Resetare poziție dacă ies din ecran
    if car1_x > WIDTH: car1_x = -CAR_WIDTH
    if car2_y < -CAR_HEIGHT: car2_y = HEIGHT

    # 4. Desenare
    screen.fill((34, 139, 34)) # Fundal verde (iarbă)

    # Desenare drumuri (intersecția)
    # Drum orizontal
    pygame.draw.rect(screen, ROAD_COLOR, (0, HEIGHT // 2 - ROAD_WIDTH // 2, WIDTH, ROAD_WIDTH))
    # Drum vertical
    pygame.draw.rect(screen, ROAD_COLOR, (WIDTH // 2 - ROAD_WIDTH // 2, 0, ROAD_WIDTH, HEIGHT))

    # Linii de marcaj (opțional, pentru aspect)
    pygame.draw.line(screen, YELLOW, (0, HEIGHT // 2), (WIDTH // 2 - ROAD_WIDTH // 2, HEIGHT // 2), 2)
    pygame.draw.line(screen, YELLOW, (WIDTH // 2 + ROAD_WIDTH // 2, HEIGHT // 2), (WIDTH, HEIGHT // 2), 2)

    # Desenare mașini
    pygame.draw.rect(screen, RED, (car1_x, car1_y, CAR_WIDTH, CAR_HEIGHT))
    pygame.draw.rect(screen, BLUE, (car2_x, car2_y, CAR_HEIGHT, CAR_WIDTH)) # Rotită pentru verticală

    # Actualizare ecran
    pygame.display.flip()
    clock.tick(60) # 60 FPS

pygame.quit()
sys.exit()