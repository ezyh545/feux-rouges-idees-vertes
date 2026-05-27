"""
main_v2.py - Pipeline principal AMELIORE integrant toutes les corrections
==========================================================================
AMELIORATIONS integrees :
  1. Fallback robuste par camera (feature_extractor_v2)
  2. Phase tout-rouge securitaire (gpio_controller_v2)
  3. Logging CSV + mesure de latence (pipeline_logger)
  4. Gestion propre des erreurs a chaque etape
  5. Mode degrade automatique
  6. Monitoring temperature RPi
  7. Signal handler pour arret propre avec rapport

UTILISATION :
  python3 main_v2.py                    # Mode normal
  python3 main_v2.py --no-dashboard     # Sans affichage pygame
  python3 main_v2.py --intervalle 10    # Cycle de 10 secondes
  python3 main_v2.py --debug            # Mode debug verbose

FICHIERS REQUIS (dans le meme dossier) :
  - feature_extractor_v2.py
  - carrefour_kmeans_v2.py  (version originale compatible)
  - gpio_controller_v2.py
  - dashboard.py            (version originale compatible)
  - pipeline_logger.py
  - camera_mapping.json     (genere par calibration_cameras.py)
"""

import signal
import sys
import time
import argparse
import logging
import os
from datetime import datetime

# === Configuration par defaut ===
INTERVALLE_S = 5.0          # Intervalle entre chaque cycle
YOLO_MODEL = "yolov8n.pt"   # Modele YOLO
AFFICHER_DEBUG = True        # Afficher les infos de debug
FULLSCREEN = False           # Dashboard plein ecran

# === Setup logging ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('pipeline.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("main")


def lire_temperature():
    """Lit la temperature du CPU du Raspberry Pi."""
    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temp_milli = int(f.read().strip())
            return temp_milli / 1000.0
    except (FileNotFoundError, ValueError):
        return None  # Pas sur RPi


def verifier_sante_systeme():
    """Verifie l'etat de sante du systeme."""
    alertes = []

    # Temperature
    temp = lire_temperature()
    if temp is not None:
        if temp > 80:
            alertes.append(f"CRITIQUE: Temperature CPU {temp:.1f} C (throttling probable!)")
        elif temp > 70:
            alertes.append(f"ATTENTION: Temperature CPU {temp:.1f} C (elevee)")

    # Memoire
    try:
        import psutil
        mem = psutil.virtual_memory()
        if mem.percent > 90:
            alertes.append(f"CRITIQUE: RAM {mem.percent:.0f}% utilisee")
        elif mem.percent > 80:
            alertes.append(f"ATTENTION: RAM {mem.percent:.0f}% utilisee")
    except ImportError:
        pass  # psutil pas installe, pas grave

    return alertes


class PipelineComplet:
    """
    Pipeline principal integrant toutes les ameliorations.
    """

    def __init__(self, args):
        self.args = args
        self.running = True
        self.nb_erreurs_consecutives = 0
        self.MAX_ERREURS = 5  # Passe en mode urgence apres 5 erreurs

        logger.info("=" * 60)
        logger.info("  DEMARRAGE PIPELINE PLBD-12 v2")
        logger.info("  Feux Rouges, Idees Vertes")
        logger.info("=" * 60)

        # === 1. Logger ===
        from pipeline_logger import PipelineLogger
        self.pl = PipelineLogger()
        logger.info("Logger initialise")

        # === 2. Feature Extractor (avec fallback) ===
        try:
            from feature_extractor_v2 import FeatureExtractorV2
            self.extracteur = FeatureExtractorV2(model_path=args.model)
            logger.info("Feature Extractor v2 initialise")
        except Exception as e:
            logger.critical(f"Impossible d'initialiser le Feature Extractor: {e}")
            sys.exit(1)

        # === 3. K-Means ===
        try:
            from carrefour_kmeans_v2 import GestionnaireCarrefour
            self.gestionnaire = GestionnaireCarrefour()
            self.gestionnaire.entrainer()
            logger.info("K-Means entraine (6 clusters, 600 echantillons)")
        except Exception as e:
            logger.critical(f"Impossible d'initialiser le K-Means: {e}")
            sys.exit(1)

        # === 4. GPIO (avec phase tout-rouge) ===
        try:
            from gpio_controller_v2 import ControleurFeuxV2
            self.controleur = ControleurFeuxV2()
            logger.info("GPIO Controller v2 initialise")
        except Exception as e:
            logger.critical(f"Impossible d'initialiser le GPIO: {e}")
            sys.exit(1)

        # === 5. Dashboard (optionnel) ===
        self.dashboard = None
        if not args.no_dashboard:
            try:
                from dashboard import Dashboard
                self.dashboard = Dashboard(fullscreen=args.fullscreen)
                logger.info("Dashboard initialise")
            except Exception as e:
                logger.warning(f"Dashboard non disponible: {e}")
                logger.warning("Le pipeline continue sans affichage")

        logger.info(f"Intervalle: {args.intervalle}s | Debug: {args.debug}")
        logger.info("Pipeline pret. Ctrl+C pour arreter.\n")

    def cycle(self):
        """Execute un cycle complet du pipeline."""
        self.pl.nouveau_cycle()

        # --- ETAPE 1 : Capture + YOLO ---
        self.pl.start_timer("capture")
        self.pl.start_timer("yolo")  # Capture et YOLO sont combines dans l'extracteur
        try:
            vecteur, images = self.extracteur.extraire()
            cameras_ok = sum(1 for img in images.values() if img is not None)
        except Exception as e:
            logger.error(f"Erreur extraction: {e}")
            vecteur = [0, 0, 0, 0, 1, 1, 1, 1]  # Fallback : trafic moyen partout
            images = {}
            cameras_ok = 0
        self.pl.stop_timer("capture")
        self.pl.stop_timer("yolo")

        # --- ETAPE 2 : Decision K-Means ---
        self.pl.start_timer("kmeans")
        try:
            action, confiance = self.gestionnaire.decider(vecteur)
        except Exception as e:
            logger.error(f"Erreur K-Means: {e}")
            action = "NORD_SUD"  # Fallback par defaut
            confiance = 0.0
        self.pl.stop_timer("kmeans")

        # --- ETAPE 3 : GPIO ---
        self.pl.start_timer("gpio")
        try:
            self.controleur.changer(action)
        except Exception as e:
            logger.error(f"Erreur GPIO: {e}")
        self.pl.stop_timer("gpio")

        # --- ETAPE 4 : Dashboard ---
        self.pl.start_timer("dashboard")
        if self.dashboard:
            try:
                self.dashboard.mettre_a_jour(
                    images=images,
                    action=action,
                    confiance=confiance,
                    vecteur=vecteur,
                    latence=self.pl.get_latence_courante()
                )
            except Exception as e:
                logger.warning(f"Erreur dashboard: {e}")
        self.pl.stop_timer("dashboard")

        # --- LOG ---
        self.pl.log_decision(vecteur, action, confiance, cameras_ok)

        # --- Affichage debug ---
        if self.args.debug:
            temp = lire_temperature()
            temp_str = f"{temp:.1f} C" if temp else "N/A"
            lat = self.pl.get_latence_courante()
            logger.info(
                f"Cycle {self.pl.cycle}: "
                f"vecteur={vecteur} "
                f"action={action} "
                f"conf={confiance:.2f} "
                f"cams={cameras_ok}/4 "
                f"latence={lat.get('total', 0):.0f}ms "
                f"temp={temp_str}"
            )

        # --- Gestion erreurs consecutives ---
        if cameras_ok == 0:
            self.nb_erreurs_consecutives += 1
            if self.nb_erreurs_consecutives >= self.MAX_ERREURS:
                logger.critical("Trop d'erreurs consecutives! Mode urgence.")
                self.controleur.mode_urgence(duree=10)
                self.nb_erreurs_consecutives = 0
        else:
            self.nb_erreurs_consecutives = 0

        # --- Verification sante ---
        if self.pl.cycle % 10 == 0:  # Toutes les 10 cycles
            alertes = verifier_sante_systeme()
            for alerte in alertes:
                logger.warning(alerte)

    def run(self):
        """Boucle principale du pipeline."""
        try:
            while self.running:
                debut_cycle = time.time()

                self.cycle()

                # Attendre le reste de l'intervalle
                duree_cycle = time.time() - debut_cycle
                attente = max(0, self.args.intervalle - duree_cycle)
                if attente > 0:
                    time.sleep(attente)

        except KeyboardInterrupt:
            logger.info("\nArret demande par l'utilisateur (Ctrl+C)")
        finally:
            self.shutdown()

    def shutdown(self):
        """Arret propre du pipeline."""
        logger.info("\n=== ARRET DU PIPELINE ===")

        # Rapport de performance
        self.pl.rapport()

        # Stats cameras
        logger.info("\nStatistiques cameras:")
        for direction, stats in self.extracteur.get_stats().items():
            logger.info(f"  {direction}: {stats}")

        # Etat GPIO
        etat = self.controleur.get_etat()
        logger.info(f"\nCycles GPIO: {etat['nb_cycles']}")

        # Cleanup
        self.controleur.cleanup()
        if self.dashboard:
            try:
                import pygame
                pygame.quit()
            except:
                pass

        logger.info("Pipeline arrete proprement.")


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline PLBD-12 v2 - Gestion Intelligente de Carrefour"
    )
    parser.add_argument('--intervalle', type=float, default=INTERVALLE_S,
                        help=f"Intervalle entre cycles en secondes (defaut: {INTERVALLE_S})")
    parser.add_argument('--model', type=str, default=YOLO_MODEL,
                        help=f"Chemin vers le modele YOLO (defaut: {YOLO_MODEL})")
    parser.add_argument('--no-dashboard', action='store_true',
                        help="Desactiver l'affichage pygame")
    parser.add_argument('--fullscreen', action='store_true',
                        help="Dashboard en plein ecran")
    parser.add_argument('--debug', action='store_true',
                        help="Mode debug verbose")

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Signal handler pour arret propre
    pipeline = PipelineComplet(args)

    def signal_handler(sig, frame):
        pipeline.running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    pipeline.run()


if __name__ == "__main__":
    main()
