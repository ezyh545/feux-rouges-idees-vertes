"""
pipeline_logger.py - Logger CSV + Chronometre de latence du pipeline
=====================================================================
OBJECTIF :
  1. Logger chaque decision dans un fichier CSV horodate
  2. Mesurer la latence de chaque etape du pipeline
  3. Generer un rapport de performance a la fin de la session

UTILISATION :
  from pipeline_logger import PipelineLogger
  logger = PipelineLogger()

  logger.start_timer("capture")
  # ... capture cameras ...
  logger.stop_timer("capture")

  logger.start_timer("yolo")
  # ... inference YOLO ...
  logger.stop_timer("yolo")

  logger.log_decision(vecteur, action, confiance)
  logger.rapport()

FICHIERS GENERES :
  - decisions_YYYYMMDD_HHMMSS.csv : log de toutes les decisions
  - latence_YYYYMMDD_HHMMSS.csv : latence par etape par cycle
"""

import csv
import time
import os
import statistics
from datetime import datetime


class PipelineLogger:
    """
    Logger complet pour le pipeline PLBD-12.
    Mesure la latence, enregistre les decisions, genere des rapports.
    """

    def __init__(self, dossier_logs="logs"):
        """
        Args:
            dossier_logs: dossier ou stocker les fichiers CSV
        """
        os.makedirs(dossier_logs, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.fichier_decisions = os.path.join(dossier_logs, f"decisions_{timestamp}.csv")
        self.fichier_latence = os.path.join(dossier_logs, f"latence_{timestamp}.csv")

        # Initialiser les fichiers CSV
        with open(self.fichier_decisions, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'cycle',
                'pN', 'pS', 'pE', 'pW', 'vN', 'vS', 'vE', 'vW',
                'action', 'confiance',
                'cameras_ok', 'latence_totale_ms'
            ])

        with open(self.fichier_latence, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'cycle',
                'capture_ms', 'yolo_ms', 'kmeans_ms', 'gpio_ms', 'dashboard_ms',
                'total_ms'
            ])

        # Etat interne
        self.cycle = 0
        self.timers = {}
        self.latences_cycle = {}
        self.historique_latences = []  # Pour le rapport final

        # Statistiques globales
        self.stats_latence = {
            'capture': [], 'yolo': [], 'kmeans': [],
            'gpio': [], 'dashboard': [], 'total': []
        }

        print(f"[Logger] Decisions: {self.fichier_decisions}")
        print(f"[Logger] Latences:  {self.fichier_latence}")

    def nouveau_cycle(self):
        """Demarre un nouveau cycle de mesure."""
        self.cycle += 1
        self.latences_cycle = {}
        self.timers = {}
        self.timers['__cycle_start'] = time.perf_counter()

    def start_timer(self, etape):
        """
        Demarre le chronometre pour une etape.

        Args:
            etape: 'capture', 'yolo', 'kmeans', 'gpio', 'dashboard'
        """
        self.timers[etape] = time.perf_counter()

    def stop_timer(self, etape):
        """
        Arrete le chronometre et enregistre la duree.

        Returns:
            float: duree en millisecondes
        """
        if etape in self.timers:
            duree_ms = (time.perf_counter() - self.timers[etape]) * 1000
            self.latences_cycle[etape] = duree_ms
            self.stats_latence.get(etape, []).append(duree_ms) if etape in self.stats_latence else None
            return duree_ms
        return 0

    def log_decision(self, vecteur, action, confiance, cameras_ok=4):
        """
        Enregistre une decision dans le CSV.

        Args:
            vecteur: list [pN,pS,pE,pW,vN,vS,vE,vW]
            action: str (ex: 'NORD_SUD')
            confiance: float (0-1)
            cameras_ok: int nombre de cameras fonctionnelles
        """
        # Calculer la latence totale du cycle
        if '__cycle_start' in self.timers:
            latence_totale = (time.perf_counter() - self.timers['__cycle_start']) * 1000
        else:
            latence_totale = sum(self.latences_cycle.values())

        self.latences_cycle['total'] = latence_totale
        self.stats_latence['total'].append(latence_totale)

        # Ecrire la decision
        with open(self.fichier_decisions, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().isoformat(),
                self.cycle,
                *vecteur,
                action,
                f"{confiance:.3f}",
                cameras_ok,
                f"{latence_totale:.1f}"
            ])

        # Ecrire la latence
        with open(self.fichier_latence, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().isoformat(),
                self.cycle,
                f"{self.latences_cycle.get('capture', 0):.1f}",
                f"{self.latences_cycle.get('yolo', 0):.1f}",
                f"{self.latences_cycle.get('kmeans', 0):.1f}",
                f"{self.latences_cycle.get('gpio', 0):.1f}",
                f"{self.latences_cycle.get('dashboard', 0):.1f}",
                f"{latence_totale:.1f}"
            ])

        self.historique_latences.append(self.latences_cycle.copy())

    def rapport(self):
        """
        Genere un rapport de performance en console.
        A appeler a la fin de la session (Ctrl+C).
        """
        print("\n" + "=" * 70)
        print("  RAPPORT DE PERFORMANCE DU PIPELINE")
        print("  Projet PLBD-12 - Session du", datetime.now().strftime("%d/%m/%Y %H:%M"))
        print("=" * 70)

        print(f"\n  Cycles completes: {self.cycle}")

        if self.cycle == 0:
            print("  Aucun cycle enregistre.")
            return

        print(f"\n  {'Etape':<15} {'Moy (ms)':>10} {'Min (ms)':>10} {'Max (ms)':>10} {'Ecart-type':>12}")
        print("  " + "-" * 59)

        for etape in ['capture', 'yolo', 'kmeans', 'gpio', 'dashboard', 'total']:
            vals = self.stats_latence.get(etape, [])
            if vals:
                moy = statistics.mean(vals)
                mini = min(vals)
                maxi = max(vals)
                ecart = statistics.stdev(vals) if len(vals) > 1 else 0
                print(f"  {etape:<15} {moy:>10.1f} {mini:>10.1f} {maxi:>10.1f} {ecart:>12.1f}")

        # Frequence du pipeline
        totaux = self.stats_latence.get('total', [])
        if totaux:
            moy_total = statistics.mean(totaux)
            freq = 1000 / moy_total if moy_total > 0 else 0
            print(f"\n  Latence moyenne totale: {moy_total:.0f} ms")
            print(f"  Frequence du pipeline:  {freq:.2f} Hz ({1/freq:.1f}s par cycle)" if freq > 0 else "")

        # Degradation dans le temps (throttling thermique?)
        if len(totaux) > 10:
            premiere_moitie = statistics.mean(totaux[:len(totaux)//2])
            seconde_moitie = statistics.mean(totaux[len(totaux)//2:])
            degradation = ((seconde_moitie - premiere_moitie) / premiere_moitie) * 100

            print(f"\n  Degradation temporelle:")
            print(f"    1ere moitie: {premiere_moitie:.0f} ms")
            print(f"    2eme moitie: {seconde_moitie:.0f} ms")
            print(f"    Degradation: {degradation:+.1f}%")

            if degradation > 20:
                print("    ATTENTION: Degradation significative detectee!")
                print("    Cause probable: throttling thermique du RPi 5")
                print("    Solution: verifier le ventilateur, reduire la charge")

        print(f"\n  Fichiers generes:")
        print(f"    {self.fichier_decisions}")
        print(f"    {self.fichier_latence}")
        print("=" * 70)

    def get_latence_courante(self):
        """Retourne les latences du cycle courant (pour le dashboard)."""
        return self.latences_cycle.copy()

    def get_stats_resume(self):
        """Retourne un resume des stats (pour affichage temps reel)."""
        totaux = self.stats_latence.get('total', [])
        if not totaux:
            return {'moy_ms': 0, 'cycles': 0}
        return {
            'moy_ms': statistics.mean(totaux),
            'min_ms': min(totaux),
            'max_ms': max(totaux),
            'cycles': self.cycle,
        }


# === TEST STANDALONE : simule 10 cycles ===
if __name__ == "__main__":
    import random

    logger = PipelineLogger(dossier_logs="logs_test")

    print("\n=== Simulation de 10 cycles du pipeline ===\n")

    actions = ['NORD_SEUL', 'SUD_SEUL', 'EST_SEUL', 'OUEST_SEUL', 'NORD_SUD', 'EST_OUEST']

    for i in range(10):
        logger.nouveau_cycle()

        # Simuler capture (500-800ms)
        logger.start_timer("capture")
        time.sleep(random.uniform(0.5, 0.8))
        logger.stop_timer("capture")

        # Simuler YOLO (800-1500ms)
        logger.start_timer("yolo")
        time.sleep(random.uniform(0.8, 1.5))
        logger.stop_timer("yolo")

        # Simuler K-Means (<10ms)
        logger.start_timer("kmeans")
        time.sleep(random.uniform(0.001, 0.01))
        logger.stop_timer("kmeans")

        # Simuler GPIO (<5ms)
        logger.start_timer("gpio")
        time.sleep(random.uniform(0.001, 0.005))
        logger.stop_timer("gpio")

        # Simuler Dashboard (20-40ms)
        logger.start_timer("dashboard")
        time.sleep(random.uniform(0.02, 0.04))
        logger.stop_timer("dashboard")

        # Log la decision
        vecteur = [random.randint(0, 1) for _ in range(4)] + [random.randint(0, 2) for _ in range(4)]
        action = random.choice(actions)
        confiance = random.uniform(0.5, 0.95)

        logger.log_decision(vecteur, action, confiance, cameras_ok=4)
        lat = logger.get_latence_courante()
        print(f"  Cycle {i+1}: {action:<12} conf={confiance:.2f} latence={lat.get('total', 0):.0f}ms")

    logger.rapport()
