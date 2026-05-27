"""
feature_extractor_v2.py - Extracteur de features ROBUSTE avec fallback
========================================================================
AMELIORATIONS vs version originale :
  1. Try/except par camera : une camera en panne ne plante plus le pipeline
  2. Valeur par defaut configurable si capture echoue
  3. Logging de chaque echec pour diagnostic post-demo
  4. Retry automatique (1 tentative) avant fallback
  5. Statistiques de fiabilite par camera en temps reel

UTILISATION :
  Remplace feature_extractor.py dans ton projet.
  Compatible avec le reste du pipeline (meme format de sortie).
"""

import cv2
import time
import logging
import json
import os
from datetime import datetime

# --- Configuration logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('pipeline.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Fichier de mapping cameras persistant ---
CAMERA_MAP_FILE = "camera_mapping.json"

# --- Classes COCO detectees ---
CLASSES_VEHICULES = {'car', 'truck', 'bus', 'motorcycle'}
CLASSES_PIETONS = {'person'}

# --- Seuils ---
SEUIL_CONFIANCE = 0.40
SEUIL_MOYEN = 1      # >= 1 detection -> niveau 1
SEUIL_FORT = 3        # >= 3 detections -> niveau 2

# --- Valeurs par defaut si camera en panne (trafic moyen assume) ---
FALLBACK_PIETONS = 0  # pas de pieton par defaut (securitaire)
FALLBACK_VEHICULES = 1  # trafic moyen par defaut (evite de bloquer une voie)


class FeatureExtractorV2:
    """
    Extracteur de features robuste avec gestion d'erreurs par camera.

    Produit le meme vecteur 8-entiers que la version originale :
    [pN, pS, pE, pW, vN, vS, vE, vW]
    """

    def __init__(self, model_path="yolov8n.pt", cameras=None):
        """
        Args:
            model_path: chemin vers le modele YOLOv8
            cameras: dict {direction: index} ou None pour charger depuis camera_mapping.json
        """
        # Chargement du modele YOLO
        try:
            from ultralytics import YOLO
            self.model = YOLO(model_path)
            logger.info(f"Modele YOLO charge: {model_path}")
        except Exception as e:
            logger.critical(f"IMPOSSIBLE de charger YOLO: {e}")
            raise

        # Chargement du mapping cameras
        if cameras:
            self.cameras = cameras
        else:
            self.cameras = self._charger_mapping()

        # Ordre des directions (doit correspondre au vecteur de features)
        self.directions = ['NORD', 'SUD', 'EST', 'OUEST']

        # Statistiques de fiabilite par camera
        self.stats = {d: {'succes': 0, 'echecs': 0} for d in self.directions}

        logger.info(f"Mapping cameras: {self.cameras}")

    def _charger_mapping(self):
        """Charge le mapping camera depuis le fichier JSON persistant."""
        if os.path.exists(CAMERA_MAP_FILE):
            with open(CAMERA_MAP_FILE, 'r') as f:
                mapping = json.load(f)
                logger.info(f"Mapping charge depuis {CAMERA_MAP_FILE}")
                return mapping
        else:
            # Mapping par defaut (a calibrer avec calibration_cameras.py)
            mapping = {'NORD': 0, 'SUD': 1, 'EST': 2, 'OUEST': 3}
            logger.warning(f"Pas de {CAMERA_MAP_FILE} trouve, mapping par defaut utilise")
            return mapping

    def _capturer_image(self, index_camera, direction, max_retries=2):
        """
        Capture une image depuis une camera USB avec retry.

        Returns:
            image (numpy array) ou None si echec total
        """
        for tentative in range(max_retries):
            cap = None
            try:
                cap = cv2.VideoCapture(index_camera, cv2.CAP_V4L2)
                if not cap.isOpened():
                    logger.warning(f"[{direction}] Camera {index_camera} non ouverte (tentative {tentative+1}/{max_retries})")
                    continue

                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

                # Delai d'initialisation
                time.sleep(0.5)

                # Flush du buffer (3 frames)
                for _ in range(3):
                    cap.read()

                # Capture reelle
                ret, frame = cap.read()
                if ret and frame is not None:
                    self.stats[direction]['succes'] += 1
                    return frame
                else:
                    logger.warning(f"[{direction}] Lecture echouee (tentative {tentative+1}/{max_retries})")

            except Exception as e:
                logger.error(f"[{direction}] Erreur capture camera {index_camera}: {e} (tentative {tentative+1}/{max_retries})")
            finally:
                if cap is not None:
                    cap.release()

            # Petit delai avant retry
            time.sleep(0.3)

        # Echec total apres toutes les tentatives
        self.stats[direction]['echecs'] += 1
        logger.error(f"[{direction}] ECHEC TOTAL camera {index_camera} apres {max_retries} tentatives -> FALLBACK")
        return None

    def _analyser_image(self, image, direction):
        """
        Analyse une image avec YOLO et retourne (nb_pietons, nb_vehicules).

        Returns:
            tuple (pietons_raw, vehicules_raw) = comptages bruts
        """
        try:
            results = self.model(image, conf=SEUIL_CONFIANCE, verbose=False)

            pietons = 0
            vehicules = 0

            for result in results:
                for box in result.boxes:
                    cls_id = int(box.cls[0])
                    cls_name = result.names[cls_id]

                    if cls_name in CLASSES_PIETONS:
                        pietons += 1
                    elif cls_name in CLASSES_VEHICULES:
                        vehicules += 1

            logger.debug(f"[{direction}] Detection: {pietons} pietons, {vehicules} vehicules")
            return pietons, vehicules

        except Exception as e:
            logger.error(f"[{direction}] Erreur YOLO: {e} -> fallback detection")
            return FALLBACK_PIETONS, FALLBACK_VEHICULES

    def _discretiser(self, pietons_raw, vehicules_raw):
        """
        Convertit les comptages bruts en niveaux discrets.

        Returns:
            tuple (p, v) ou p in {0,1} et v in {0,1,2}
        """
        p = 1 if pietons_raw >= 1 else 0

        if vehicules_raw >= SEUIL_FORT:
            v = 2
        elif vehicules_raw >= SEUIL_MOYEN:
            v = 1
        else:
            v = 0

        return p, v

    def extraire(self):
        """
        Pipeline complet : capture 4 cameras -> YOLO -> vecteur 8 entiers.

        AMELIORATION CRITIQUE : si une camera echoue, utilise des valeurs
        par defaut au lieu de planter.

        Returns:
            list [pN, pS, pE, pW, vN, vS, vE, vW]
            dict {direction: image} pour l'affichage (None si echec)
        """
        pietons = []
        vehicules = []
        images = {}

        for direction in self.directions:
            index = self.cameras.get(direction, -1)

            # === CAPTURE (avec fallback) ===
            image = self._capturer_image(index, direction)
            images[direction] = image

            if image is not None:
                # Camera OK -> analyse YOLO
                p_raw, v_raw = self._analyser_image(image, direction)
            else:
                # Camera KO -> valeurs par defaut
                p_raw = FALLBACK_PIETONS
                v_raw = FALLBACK_VEHICULES
                logger.warning(f"[{direction}] Utilisation valeurs fallback: p={p_raw}, v={v_raw}")

            # Discretisation
            p, v = self._discretiser(p_raw, v_raw)
            pietons.append(p)
            vehicules.append(v)

        # Assemblage du vecteur [pN, pS, pE, pW, vN, vS, vE, vW]
        vecteur = pietons + vehicules
        logger.info(f"Vecteur extrait: {vecteur}")

        return vecteur, images

    def get_stats(self):
        """Retourne les statistiques de fiabilite par camera."""
        stats_lisibles = {}
        for direction, s in self.stats.items():
            total = s['succes'] + s['echecs']
            taux = (s['succes'] / total * 100) if total > 0 else 0
            stats_lisibles[direction] = {
                'succes': s['succes'],
                'echecs': s['echecs'],
                'fiabilite': f"{taux:.1f}%"
            }
        return stats_lisibles

    def afficher_apercu(self, images):
        """Affiche une mosaique 2x2 des 4 cameras (compatible avec dashboard)."""
        import numpy as np

        # Image vide pour cameras en panne
        img_vide = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(img_vide, "CAMERA HORS LIGNE", (100, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        imgs = []
        for direction in self.directions:
            img = images.get(direction)
            if img is None:
                imgs.append(img_vide.copy())
            else:
                # Redimensionner si necessaire
                img_resized = cv2.resize(img, (640, 480))
                # Annoter la direction
                cv2.putText(img_resized, direction, (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                imgs.append(img_resized)

        # Mosaique 2x2
        row1 = np.hstack([imgs[0], imgs[1]])  # NORD | SUD
        row2 = np.hstack([imgs[2], imgs[3]])  # EST  | OUEST
        mosaique = np.vstack([row1, row2])

        return mosaique


# === TEST STANDALONE ===
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "stats":
        # Mode statistiques
        extractor = FeatureExtractorV2()
        print("\n=== Test de 5 cycles de capture ===\n")
        for i in range(5):
            print(f"--- Cycle {i+1} ---")
            vecteur, images = extractor.extraire()
            print(f"Vecteur: {vecteur}")
            time.sleep(2)

        print("\n=== Statistiques de fiabilite ===")
        for direction, stats in extractor.get_stats().items():
            print(f"  {direction}: {stats}")
    else:
        # Test simple
        extractor = FeatureExtractorV2()
        vecteur, images = extractor.extraire()
        print(f"Vecteur de features: {vecteur}")
        print(f"Stats: {extractor.get_stats()}")
