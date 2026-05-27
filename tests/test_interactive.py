"""
test_interactive.py - GUI interactive de test (PLAN B POUR LA DEMO)
Usage: python3 test_interactive.py
Controles: Clic pour modifier les valeurs, R=reset, Q=quitter
"""
import pygame
import sys
import time

sys.path.insert(0, '../src')
from carrefour_kmeans_v2 import GestionnaireCarrefour
from gpio_controller_v2 import ControleurFeuxV2

# Init
pygame.init()
ecran = pygame.display.set_mode((800, 600))
pygame.display.set_caption("PLBD-12 | Test Interactif")
font = pygame.font.SysFont("Arial", 20)
font_big = pygame.font.SysFont("Arial", 30, bold=True)
clock = pygame.time.Clock()

gestionnaire = GestionnaireCarrefour()
gestionnaire.entrainer()
controleur = ControleurFeuxV2()

DIRECTIONS = ['NORD', 'SUD', 'EST', 'OUEST']
pietons = [0, 0, 0, 0]
vehicules = [0, 0, 0, 0]

NOIR = (0, 0, 0)
BLANC = (255, 255, 255)
GRIS = (50, 50, 50)
VERT = (50, 200, 50)
ROUGE = (200, 50, 50)
BLEU = (50, 130, 220)

# Zones cliquables
zones_pietons = [(100 + i*170, 200, 60, 40) for i in range(4)]
zones_vehicules = [(100 + i*170, 280, 60, 40) for i in range(4)]

print("=== Test Interactif ===")
print("Cliquez pour modifier pietons/vehicules")
print("R=reset, Q=quitter\n")

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_q:
                running = False
            elif event.key == pygame.K_r:
                pietons = [0, 0, 0, 0]
                vehicules = [0, 0, 0, 0]
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            for i, (x, y, w, h) in enumerate(zones_pietons):
                if x <= mx <= x+w and y <= my <= y+h:
                    pietons[i] = (pietons[i] + 1) % 2
            for i, (x, y, w, h) in enumerate(zones_vehicules):
                if x <= mx <= x+w and y <= my <= y+h:
                    vehicules[i] = (vehicules[i] + 1) % 3

    # Decision
    vecteur = pietons + vehicules
    action, confiance = gestionnaire.decider(vecteur)
    controleur.changer(action)

    # Affichage
    ecran.fill(NOIR)
    titre = font_big.render("Test Interactif PLBD-12", True, BLEU)
    ecran.blit(titre, (220, 20))

    # Labels directions
    for i, d in enumerate(DIRECTIONS):
        label = font.render(d, True, BLANC)
        ecran.blit(label, (100 + i*170, 150))

    # Pietons (cliquables)
    label_p = font.render("Pietons:", True, GRIS)
    ecran.blit(label_p, (10, 208))
    for i, (x, y, w, h) in enumerate(zones_pietons):
        couleur = VERT if pietons[i] else ROUGE
        pygame.draw.rect(ecran, couleur, (x, y, w, h), border_radius=5)
        txt = font.render(str(pietons[i]), True, BLANC)
        ecran.blit(txt, (x+22, y+8))

    # Vehicules (cliquables)
    label_v = font.render("Vehic.:", True, GRIS)
    ecran.blit(label_v, (10, 288))
    for i, (x, y, w, h) in enumerate(zones_vehicules):
        couleur = VERT if vehicules[i] > 0 else ROUGE
        pygame.draw.rect(ecran, couleur, (x, y, w, h), border_radius=5)
        txt = font.render(str(vehicules[i]), True, BLANC)
        ecran.blit(txt, (x+22, y+8))

    # Vecteur
    vec_txt = font.render(f"Vecteur: {vecteur}", True, BLANC)
    ecran.blit(vec_txt, (100, 360))

    # Decision
    dec_txt = font_big.render(f"-> {action}", True, VERT)
    ecran.blit(dec_txt, (100, 400))

    conf_txt = font.render(f"Confiance: {confiance:.1%}", True, BLANC)
    ecran.blit(conf_txt, (100, 450))

    # Instructions
    instr = font.render("Clic=modifier | R=reset | Q=quitter", True, GRIS)
    ecran.blit(instr, (200, 550))

    pygame.display.flip()
    clock.tick(30)

controleur.cleanup()
pygame.quit()
