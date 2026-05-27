"""
gpio_controller_v2.py - Controleur GPIO avec phase TOUT-ROUGE securitaire
===========================================================================
AMELIORATIONS vs version originale :
  1. Phase TOUT-ROUGE obligatoire entre chaque transition (1.5s)
  2. Sequence complete : Vert -> Jaune (2s) -> Tout Rouge (1.5s) -> Nouveau Vert
  3. Mode clignotant d'urgence (tout jaune clignotant)
  4. Historique des transitions pour le dashboard
  5. Compteur de cycles pour metriques

UTILISATION :
  Remplace gpio_controller.py dans ton projet.
  Compatible avec le reste du pipeline.
"""

import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# === Configuration GPIO BCM ===
PINS = {
    'NORD':  {'rouge': 17, 'jaune': 27, 'vert': 22},
    'SUD':   {'rouge': 23, 'jaune': 24, 'vert': 25},
    'EST':   {'rouge': 5,  'jaune': 6,  'vert': 13},
    'OUEST': {'rouge': 19, 'jaune': 26, 'vert': 16},
}

# === Temporisations (en secondes) ===
DUREE_JAUNE = 2.0       # Phase jaune avant changement
DUREE_TOUT_ROUGE = 1.5  # Phase securite tout rouge (NOUVEAU)
DUREE_MIN_VERT = 5.0    # Duree minimum du vert
DUREE_CLIGNOTEMENT = 0.5  # Pour le mode urgence

# === Les 6 actions valides ===
ACTIONS = {
    'NORD_SEUL':  {'vert': ['NORD'],        'rouge': ['SUD', 'EST', 'OUEST']},
    'SUD_SEUL':   {'vert': ['SUD'],          'rouge': ['NORD', 'EST', 'OUEST']},
    'EST_SEUL':   {'vert': ['EST'],          'rouge': ['NORD', 'SUD', 'OUEST']},
    'OUEST_SEUL': {'vert': ['OUEST'],        'rouge': ['NORD', 'SUD', 'EST']},
    'NORD_SUD':   {'vert': ['NORD', 'SUD'],  'rouge': ['EST', 'OUEST']},
    'EST_OUEST':  {'vert': ['EST', 'OUEST'], 'rouge': ['NORD', 'SUD']},
}


class GPIOSimulateur:
    """Simulateur GPIO pour PC (pas de Raspberry Pi)."""

    def __init__(self):
        logger.info("Mode SIMULATEUR GPIO actif (pas sur RPi)")

    def setup(self, pin, mode):
        pass

    def output(self, pin, state):
        pass

    def cleanup(self):
        pass

    BCM = "BCM"
    OUT = "OUT"
    HIGH = True
    LOW = False


class ControleurFeuxV2:
    """
    Controleur de feux tricolores avec transitions securisees.

    Sequence de transition :
    1. Vert actuel -> Jaune (2s)
    2. Jaune -> TOUT ROUGE (1.5s) [SECURITE]
    3. Tout Rouge -> Nouveau Vert
    """

    def __init__(self):
        # Initialisation GPIO
        try:
            import RPi.GPIO as GPIO
            self.gpio = GPIO
            self.gpio.setmode(GPIO.BCM)
            self.gpio.setwarnings(False)
            self.sur_rpi = True
            logger.info("GPIO RPi initialise (BCM)")
        except (ImportError, RuntimeError):
            self.gpio = GPIOSimulateur()
            self.sur_rpi = False
            logger.info("GPIO simulateur initialise")

        # Setup de tous les pins
        for direction, pins in PINS.items():
            for couleur, pin in pins.items():
                if self.sur_rpi:
                    self.gpio.setup(pin, self.gpio.OUT)
                    self.gpio.output(pin, self.gpio.LOW)

        # Etat actuel
        self.action_courante = None
        self.dernier_changement = 0
        self.nb_cycles = 0
        self.historique = []  # Liste des (timestamp, action, duree_cycle)

        # Demarrer en tout rouge
        self._tout_rouge()
        logger.info("Feux initialises: TOUT ROUGE")

    def _allumer(self, direction, couleur):
        """Allume une LED specifique."""
        pin = PINS[direction][couleur]
        if self.sur_rpi:
            self.gpio.output(pin, self.gpio.HIGH)

    def _eteindre(self, direction, couleur):
        """Eteint une LED specifique."""
        pin = PINS[direction][couleur]
        if self.sur_rpi:
            self.gpio.output(pin, self.gpio.LOW)

    def _eteindre_tout(self):
        """Eteint toutes les LEDs."""
        for direction in PINS:
            for couleur in ['rouge', 'jaune', 'vert']:
                self._eteindre(direction, couleur)

    def _tout_rouge(self):
        """Met toutes les directions au rouge (phase de securite)."""
        self._eteindre_tout()
        for direction in PINS:
            self._allumer(direction, 'rouge')
        logger.debug("Phase: TOUT ROUGE")

    def _tout_jaune(self):
        """Met toutes les directions au jaune (phase de transition)."""
        self._eteindre_tout()
        for direction in PINS:
            self._allumer(direction, 'jaune')
        logger.debug("Phase: TOUT JAUNE")

    def _appliquer_action(self, action_name):
        """Applique directement une configuration de feux (sans transition)."""
        config = ACTIONS[action_name]
        self._eteindre_tout()

        for direction in config['vert']:
            self._allumer(direction, 'vert')
        for direction in config['rouge']:
            self._allumer(direction, 'rouge')

        logger.debug(f"Phase: {action_name} appliquee")

    def changer(self, nouvelle_action):
        """
        Change les feux avec la sequence de securite complete.

        Sequence :
        1. Si meme action -> ne rien faire
        2. Jaune (2s) sur les voies actuellement au vert
        3. TOUT ROUGE (1.5s) - securite inter-phase
        4. Nouveau vert

        Args:
            nouvelle_action: str parmi les cles de ACTIONS
        """
        maintenant = time.time()

        # Verifier que l'action est valide
        if nouvelle_action not in ACTIONS:
            logger.error(f"Action invalide: {nouvelle_action}")
            return False

        # Meme action -> pas de changement
        if nouvelle_action == self.action_courante:
            logger.debug(f"Action identique ({nouvelle_action}), pas de transition")
            return True

        # Respecter la duree minimum de vert
        if self.action_courante and (maintenant - self.dernier_changement) < DUREE_MIN_VERT:
            temps_restant = DUREE_MIN_VERT - (maintenant - self.dernier_changement)
            logger.debug(f"Duree min vert non atteinte, attente {temps_restant:.1f}s")
            return False

        logger.info(f"Transition: {self.action_courante} -> {nouvelle_action}")

        # === ETAPE 1 : Phase Jaune ===
        if self.action_courante:
            # Jaune seulement sur les voies qui etaient au vert
            config_actuelle = ACTIONS[self.action_courante]
            self._eteindre_tout()
            for direction in config_actuelle['vert']:
                self._allumer(direction, 'jaune')
            for direction in config_actuelle['rouge']:
                self._allumer(direction, 'rouge')

            logger.info(f"  Phase JAUNE ({DUREE_JAUNE}s)")
            time.sleep(DUREE_JAUNE)

        # === ETAPE 2 : Phase TOUT ROUGE (securite) ===
        self._tout_rouge()
        logger.info(f"  Phase TOUT ROUGE securite ({DUREE_TOUT_ROUGE}s)")
        time.sleep(DUREE_TOUT_ROUGE)

        # === ETAPE 3 : Nouveau Vert ===
        self._appliquer_action(nouvelle_action)
        logger.info(f"  Phase VERT: {nouvelle_action}")

        # Mettre a jour l'etat
        duree_cycle = maintenant - self.dernier_changement if self.action_courante else 0
        self.historique.append({
            'timestamp': datetime.now().isoformat(),
            'action': nouvelle_action,
            'duree_cycle_s': round(duree_cycle, 1)
        })

        self.action_courante = nouvelle_action
        self.dernier_changement = time.time()
        self.nb_cycles += 1

        return True

    def mode_urgence(self, duree=10):
        """
        Mode urgence : tout jaune clignotant.
        Utile si le systeme detecte une anomalie.

        Args:
            duree: duree du mode urgence en secondes
        """
        logger.warning(f"MODE URGENCE ACTIVE ({duree}s)")
        debut = time.time()

        while time.time() - debut < duree:
            self._tout_jaune()
            time.sleep(DUREE_CLIGNOTEMENT)
            self._eteindre_tout()
            time.sleep(DUREE_CLIGNOTEMENT)

        # Revenir en tout rouge apres l'urgence
        self._tout_rouge()
        self.action_courante = None
        logger.info("Mode urgence termine -> TOUT ROUGE")

    def get_etat(self):
        """Retourne l'etat actuel pour le dashboard."""
        return {
            'action': self.action_courante,
            'nb_cycles': self.nb_cycles,
            'derniere_transition': self.dernier_changement,
            'sur_rpi': self.sur_rpi,
            'historique_recent': self.historique[-6:] if self.historique else []
        }

    def cleanup(self):
        """Nettoyage propre des GPIO."""
        self._eteindre_tout()
        if self.sur_rpi:
            self.gpio.cleanup()
        logger.info(f"GPIO nettoye. Total cycles: {self.nb_cycles}")


# === TEST STANDALONE ===
if __name__ == "__main__":
    print("=== Test ControleurFeuxV2 ===\n")
    ctrl = ControleurFeuxV2()

    try:
        sequences_test = ['NORD_SEUL', 'NORD_SUD', 'EST_OUEST', 'SUD_SEUL']

        for action in sequences_test:
            print(f"\n-> Changement vers {action}")
            ctrl.changer(action)
            print(f"   Etat: {ctrl.get_etat()['action']}")
            time.sleep(3)

        print("\n-> Test mode urgence (5s)")
        ctrl.mode_urgence(duree=5)

    except KeyboardInterrupt:
        print("\nInterrompu.")
    finally:
        ctrl.cleanup()
        print(f"\nTotal cycles: {ctrl.nb_cycles}")
        print("Historique:")
        for h in ctrl.historique:
            print(f"  {h['timestamp']}: {h['action']} (cycle: {h['duree_cycle_s']}s)")
