"""
dashboard.py - Affichage temps reel du systeme de carrefour
=============================================================
Affiche sur HDMI via pygame :
  - 4 miniatures cameras avec annotations
  - Carte du carrefour avec feux animes (pulsation verte)
  - Decision K-Means + barre de confiance
  - Historique des 6 dernieres decisions
  - Latence du pipeline (NOUVEAU)
  - Statistiques cameras (NOUVEAU)

UTILISATION :
  from dashboard import Dashboard
  dash = Dashboard(fullscreen=False)
  dash.mettre_a_jour(images, action, confiance, vecteur, latence)

  # Standalone (mode demo) : python3 dashboard.py
"""

import pygame
import math
import time
import sys
import numpy as np

# === Configuration ===
LARGEUR = 1280
HAUTEUR = 720
FPS = 30

# Couleurs
NOIR = (0, 0, 0)
BLANC = (255, 255, 255)
GRIS = (40, 40, 40)
GRIS_CLAIR = (60, 60, 60)
ROUGE = (220, 50, 50)
JAUNE = (220, 200, 50)
VERT = (50, 200, 50)
VERT_FONCE = (30, 130, 30)
BLEU = (50, 130, 220)
ORANGE = (230, 130, 50)

# Mapping action -> directions vertes
ACTIONS_VERTS = {
    'NORD_SEUL': ['NORD'],
    'SUD_SEUL': ['SUD'],
    'EST_SEUL': ['EST'],
    'OUEST_SEUL': ['OUEST'],
    'NORD_SUD': ['NORD', 'SUD'],
    'EST_OUEST': ['EST', 'OUEST'],
}


class Dashboard:
    """Dashboard temps reel pour le systeme de carrefour."""

    def __init__(self, fullscreen=False):
        pygame.init()

        if fullscreen:
            self.ecran = pygame.display.set_mode((LARGEUR, HAUTEUR), pygame.FULLSCREEN)
        else:
            self.ecran = pygame.display.set_mode((LARGEUR, HAUTEUR))

        pygame.display.set_caption("PLBD-12 | Feux Rouges, Idees Vertes")
        self.clock = pygame.time.Clock()
        self.font_titre = pygame.font.SysFont("Arial", 28, bold=True)
        self.font_normal = pygame.font.SysFont("Arial", 18)
        self.font_petit = pygame.font.SysFont("Arial", 14)
        self.font_grand = pygame.font.SysFont("Arial", 36, bold=True)

        # Historique
        self.historique = []

        # Animation
        self.t_animation = 0

    def _dessiner_feu(self, x, y, direction, action):
        """Dessine un feu tricolore pour une direction."""
        directions_vertes = ACTIONS_VERTS.get(action, [])
        est_vert = direction in directions_vertes

        # Boitier du feu
        pygame.draw.rect(self.ecran, GRIS_CLAIR, (x, y, 30, 80), border_radius=5)

        # LED Rouge
        couleur_r = ROUGE if not est_vert else (80, 20, 20)
        pygame.draw.circle(self.ecran, couleur_r, (x+15, y+15), 10)

        # LED Jaune
        pygame.draw.circle(self.ecran, (80, 70, 20), (x+15, y+40), 10)

        # LED Verte (avec pulsation si active)
        if est_vert:
            pulse = (math.sin(self.t_animation * 3) + 1) / 2  # 0 a 1
            g = int(150 + 105 * pulse)
            couleur_v = (30, g, 30)
        else:
            couleur_v = (20, 50, 20)
        pygame.draw.circle(self.ecran, couleur_v, (x+15, y+65), 10)

        # Label direction
        label = self.font_petit.render(direction[:1], True, BLANC)
        self.ecran.blit(label, (x+10, y+85))

    def _dessiner_carrefour(self, action):
        """Dessine le plan du carrefour avec les feux."""
        cx, cy = 640, 300  # Centre du carrefour

        # Routes
        pygame.draw.rect(self.ecran, GRIS_CLAIR, (cx-40, cy-150, 80, 300))  # N-S
        pygame.draw.rect(self.ecran, GRIS_CLAIR, (cx-150, cy-40, 300, 80))  # E-O

        # Marquage central
        pygame.draw.rect(self.ecran, JAUNE, (cx-1, cy-40, 2, 80))
        pygame.draw.rect(self.ecran, JAUNE, (cx-40, cy-1, 80, 2))

        # Feux
        self._dessiner_feu(cx-15, cy-150, 'NORD', action)    # Nord (haut)
        self._dessiner_feu(cx-15, cy+80, 'SUD', action)      # Sud (bas)
        self._dessiner_feu(cx-150, cy-15, 'OUEST', action)   # Ouest (gauche)
        self._dessiner_feu(cx+80, cy-15, 'EST', action)      # Est (droite)

        # Labels directions
        labels_pos = {
            'NORD': (cx-20, cy-180), 'SUD': (cx-15, cy+170),
            'EST': (cx+120, cy-5), 'OUEST': (cx-170, cy-5)
        }
        for d, pos in labels_pos.items():
            label = self.font_petit.render(d, True, BLANC)
            self.ecran.blit(label, pos)

    def _dessiner_cameras(self, images):
        """Dessine les 4 miniatures cameras."""
        positions = {
            'NORD': (20, 50), 'SUD': (170, 50),
            'EST': (20, 200), 'OUEST': (170, 200)
        }

        for direction, (x, y) in positions.items():
            # Cadre
            pygame.draw.rect(self.ecran, GRIS_CLAIR, (x, y, 140, 105), border_radius=3)

            img = images.get(direction) if images else None
            if img is not None:
                try:
                    img_small = self._cv2_to_pygame(img, (136, 96))
                    self.ecran.blit(img_small, (x+2, y+2))
                except:
                    label = self.font_petit.render("Erreur", True, ROUGE)
                    self.ecran.blit(label, (x+40, y+40))
            else:
                label = self.font_petit.render("HORS LIGNE", True, ROUGE)
                self.ecran.blit(label, (x+25, y+40))

            # Label
            label = self.font_petit.render(direction, True, BLANC)
            self.ecran.blit(label, (x+5, y+108))

    def _cv2_to_pygame(self, img_cv2, size):
        """Convertit une image OpenCV en surface pygame."""
        import cv2
        img_rgb = cv2.cvtColor(img_cv2, cv2.COLOR_BGR2RGB)
        img_resized = cv2.resize(img_rgb, size)
        return pygame.surfarray.make_surface(np.transpose(img_resized, (1, 0, 2)))

    def _dessiner_decision(self, action, confiance, vecteur):
        """Affiche la decision courante et la confiance."""
        x, y = 850, 50

        # Titre
        titre = self.font_titre.render("DECISION", True, BLEU)
        self.ecran.blit(titre, (x, y))

        # Action
        action_text = self.font_grand.render(action or "---", True, VERT if action else GRIS)
        self.ecran.blit(action_text, (x, y+40))

        # Barre de confiance
        pygame.draw.rect(self.ecran, GRIS_CLAIR, (x, y+90, 300, 25), border_radius=3)
        largeur_barre = int(300 * confiance)
        couleur_barre = VERT if confiance > 0.7 else (ORANGE if confiance > 0.4 else ROUGE)
        pygame.draw.rect(self.ecran, couleur_barre, (x, y+90, largeur_barre, 25), border_radius=3)
        conf_text = self.font_normal.render(f"Confiance: {confiance:.1%}", True, BLANC)
        self.ecran.blit(conf_text, (x+5, y+92))

        # Vecteur
        if vecteur:
            vec_text = self.font_petit.render(f"Features: {vecteur}", True, GRIS_CLAIR)
            self.ecran.blit(vec_text, (x, y+125))

    def _dessiner_historique(self):
        """Affiche l'historique des 6 dernieres decisions."""
        x, y = 850, 250
        titre = self.font_normal.render("Historique:", True, BLANC)
        self.ecran.blit(titre, (x, y))

        for i, entry in enumerate(self.historique[-6:]):
            txt = self.font_petit.render(
                f"{entry['action']} (conf={entry['confiance']:.0%})",
                True, GRIS_CLAIR if i < 5 else BLANC
            )
            self.ecran.blit(txt, (x+10, y+25+i*20))

    def _dessiner_latence(self, latence):
        """Affiche les metriques de latence."""
        x, y = 850, 430
        titre = self.font_normal.render("Latence pipeline:", True, BLANC)
        self.ecran.blit(titre, (x, y))

        if latence:
            etapes = ['capture', 'yolo', 'kmeans', 'gpio', 'dashboard', 'total']
            for i, etape in enumerate(etapes):
                val = latence.get(etape, 0)
                couleur = ROUGE if (etape == 'total' and val > 5000) else BLANC
                txt = self.font_petit.render(f"{etape}: {val:.0f}ms", True, couleur)
                self.ecran.blit(txt, (x+10, y+25+i*18))

    def mettre_a_jour(self, images=None, action=None, confiance=0, vecteur=None, latence=None):
        """
        Met a jour l'affichage complet.

        Args:
            images: dict {direction: numpy_array} ou None
            action: str (nom de l'action)
            confiance: float (0-1)
            vecteur: list [pN,pS,pE,pW,vN,vS,vE,vW]
            latence: dict {etape: ms}
        """
        # Gestion evenements pygame
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

        self.t_animation = time.time()

        # Fond
        self.ecran.fill(NOIR)

        # Titre
        titre = self.font_titre.render("PLBD-12 | Feux Rouges, Idees Vertes", True, BLEU)
        self.ecran.blit(titre, (20, 10))

        # Elements
        self._dessiner_cameras(images)
        self._dessiner_carrefour(action)
        self._dessiner_decision(action, confiance, vecteur)
        self._dessiner_historique()
        self._dessiner_latence(latence)

        # Historique
        if action:
            self.historique.append({
                'action': action,
                'confiance': confiance,
                'time': time.time()
            })

        pygame.display.flip()
        self.clock.tick(FPS)


# === MODE DEMO STANDALONE ===
if __name__ == "__main__":
    import random

    print("=== Dashboard Demo Mode ===")
    print("Appuyez sur Q ou ESC pour quitter\n")

    dash = Dashboard(fullscreen=False)
    actions = ['NORD_SEUL', 'SUD_SEUL', 'EST_SEUL', 'OUEST_SEUL', 'NORD_SUD', 'EST_OUEST']

    try:
        while True:
            action = random.choice(actions)
            confiance = random.uniform(0.4, 0.95)
            vecteur = [random.randint(0, 1) for _ in range(4)] + [random.randint(0, 2) for _ in range(4)]
            latence = {
                'capture': random.uniform(400, 800),
                'yolo': random.uniform(800, 1500),
                'kmeans': random.uniform(1, 10),
                'gpio': random.uniform(1, 5),
                'dashboard': random.uniform(20, 40),
                'total': random.uniform(1500, 3000),
            }

            dash.mettre_a_jour(
                images=None,
                action=action,
                confiance=confiance,
                vecteur=vecteur,
                latence=latence
            )
            time.sleep(0.5)
    except (KeyboardInterrupt, SystemExit):
        pygame.quit()
        print("Dashboard ferme.")
