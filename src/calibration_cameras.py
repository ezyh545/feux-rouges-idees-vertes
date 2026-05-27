"""
calibration_cameras.py - Script de recalibration rapide des cameras
====================================================================
PROBLEME RESOLU :
  Apres chaque reboot du RPi, Linux reassigne les indices /dev/video0-3
  dans un ordre aleatoire. Ce script identifie quelle camera physique
  correspond a quelle direction et persiste le mapping.

UTILISATION :
  1. Brancher les 4 cameras sur le hub USB
  2. Lancer : python3 calibration_cameras.py
  3. Le script ouvre chaque camera une par une
  4. Vous indiquez la direction (N/S/E/O) en regardant l'image
  5. Le mapping est sauvegarde dans camera_mapping.json
  6. Le pipeline charge automatiquement ce fichier au demarrage

ASTUCE FOIRE :
  Gardez ce script sur le bureau du RPi. Si reboot pendant la foire,
  la recalibration prend < 2 minutes.
"""

import cv2
import json
import sys
import time
import os

CAMERA_MAP_FILE = "camera_mapping.json"
MAX_CAMERAS = 10  # Cherche jusqu'a /dev/video9


def detecter_cameras_disponibles():
    """Detecte toutes les cameras USB connectees."""
    cameras = []
    print("\n=== Detection des cameras disponibles ===\n")

    for i in range(MAX_CAMERAS):
        cap = cv2.VideoCapture(i, cv2.CAP_V4L2)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                cameras.append(i)
                print(f"  Camera trouvee: /dev/video{i}")
            cap.release()

    print(f"\n  Total: {len(cameras)} camera(s) detectee(s)")
    return cameras


def calibrer_camera(index):
    """
    Ouvre une camera et demande a l'utilisateur d'identifier la direction.

    Returns:
        str: direction ('NORD', 'SUD', 'EST', 'OUEST') ou None si skip
    """
    cap = cv2.VideoCapture(index, cv2.CAP_V4L2)
    if not cap.isOpened():
        print(f"  Erreur: impossible d'ouvrir la camera {index}")
        return None

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    print(f"\n--- Camera /dev/video{index} ---")
    print("  La fenetre de la camera va s'ouvrir.")
    print("  Regardez l'image et identifiez la direction.")
    print("  Tapez : N (Nord), S (Sud), E (Est), O (Ouest), X (ignorer)")
    print("  Appuyez sur Q pour fermer la fenetre.\n")

    window_name = f"Camera {index} - Quelle direction ?"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 640, 480)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Ajouter l'index sur l'image
        cv2.putText(frame, f"Camera index: {index}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, "Appuyez Q pour fermer", (10, 460),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 200), 2)

        cv2.imshow(window_name, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == ord('Q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    # Demander la direction
    while True:
        choix = input(f"  Direction pour camera {index} (N/S/E/O/X pour ignorer) : ").upper().strip()
        mapping_choix = {
            'N': 'NORD', 'S': 'SUD', 'E': 'EST', 'O': 'OUEST', 'X': None
        }
        if choix in mapping_choix:
            return mapping_choix[choix]
        print("  Choix invalide. Tapez N, S, E, O ou X.")


def mode_rapide(cameras):
    """
    Mode rapide : affiche toutes les cameras en mosaique et demande
    le mapping d'un coup. Plus rapide pour les recalibrations repetees.
    """
    import numpy as np

    print("\n=== MODE RAPIDE : Mosaique de toutes les cameras ===")
    print("  Toutes les cameras s'affichent en meme temps.")
    print("  Notez quel index correspond a quelle direction.\n")

    frames = {}
    for idx in cameras:
        cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            time.sleep(0.3)
            for _ in range(3):
                cap.read()
            ret, frame = cap.read()
            if ret:
                cv2.putText(frame, f"INDEX: {idx}", (10, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)
                frames[idx] = cv2.resize(frame, (320, 240))
            cap.release()

    # Creer la mosaique
    if len(frames) >= 4:
        keys = sorted(frames.keys())[:4]
        row1 = np.hstack([frames[keys[0]], frames[keys[1]]])
        row2 = np.hstack([frames[keys[2]], frames[keys[3]]])
        mosaique = np.vstack([row1, row2])
    elif len(frames) > 0:
        imgs = [frames[k] for k in sorted(frames.keys())]
        mosaique = np.hstack(imgs)
    else:
        print("Aucune camera detectee!")
        return None

    cv2.namedWindow("Mosaique Cameras", cv2.WINDOW_NORMAL)
    cv2.imshow("Mosaique Cameras", mosaique)
    print("  Fenetre ouverte. Appuyez sur une touche pour fermer.")
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    # Demander le mapping
    mapping = {}
    for direction in ['NORD', 'SUD', 'EST', 'OUEST']:
        while True:
            try:
                idx = int(input(f"  Index de la camera {direction} : "))
                if idx in cameras:
                    mapping[direction] = idx
                    break
                else:
                    print(f"  Index {idx} non disponible. Cameras : {cameras}")
            except ValueError:
                print("  Entrez un nombre entier.")

    return mapping


def sauvegarder_mapping(mapping):
    """Sauvegarde le mapping dans un fichier JSON."""
    with open(CAMERA_MAP_FILE, 'w') as f:
        json.dump(mapping, f, indent=2)
    print(f"\n  Mapping sauvegarde dans {CAMERA_MAP_FILE}")
    print(f"  Contenu: {json.dumps(mapping, indent=2)}")


def verifier_mapping():
    """Verifie le mapping existant en ouvrant chaque camera."""
    if not os.path.exists(CAMERA_MAP_FILE):
        print("Aucun mapping trouve. Lancez d'abord la calibration.")
        return

    with open(CAMERA_MAP_FILE, 'r') as f:
        mapping = json.load(f)

    print(f"\n=== Verification du mapping existant ===")
    print(f"  Fichier: {CAMERA_MAP_FILE}")
    print(f"  Mapping: {mapping}\n")

    for direction, index in mapping.items():
        cap = cv2.VideoCapture(index, cv2.CAP_V4L2)
        if cap.isOpened():
            ret, _ = cap.read()
            status = "OK" if ret else "ECHEC LECTURE"
            cap.release()
        else:
            status = "NON CONNECTEE"
        print(f"  {direction} (index {index}): {status}")


def main():
    print("=" * 60)
    print("  CALIBRATION DES CAMERAS - PLBD-12")
    print("  Feux Rouges, Idees Vertes")
    print("=" * 60)

    if len(sys.argv) > 1:
        if sys.argv[1] == "verify":
            verifier_mapping()
            return
        elif sys.argv[1] == "rapide":
            cameras = detecter_cameras_disponibles()
            if len(cameras) < 4:
                print(f"\n  ATTENTION: seulement {len(cameras)} cameras detectees (4 requises)")
            mapping = mode_rapide(cameras)
            if mapping:
                sauvegarder_mapping(mapping)
            return

    # Mode normal : camera par camera
    cameras = detecter_cameras_disponibles()

    if not cameras:
        print("\n  ERREUR: Aucune camera detectee!")
        print("  Verifiez les connexions USB et le hub.")
        sys.exit(1)

    if len(cameras) < 4:
        print(f"\n  ATTENTION: seulement {len(cameras)} cameras detectees (4 requises)")
        print("  Le pipeline fonctionnera en mode degrade pour les cameras manquantes.")

    print("\n=== Calibration camera par camera ===")
    print("  Pour chaque camera, une fenetre s'ouvrira.")
    print("  Identifiez la direction et fermez la fenetre.\n")

    mapping = {}
    directions_restantes = {'NORD', 'SUD', 'EST', 'OUEST'}

    for index in cameras:
        if not directions_restantes:
            break

        direction = calibrer_camera(index)
        if direction and direction in directions_restantes:
            mapping[direction] = index
            directions_restantes.remove(direction)
            print(f"  -> Camera {index} assignee a {direction}")
        elif direction:
            print(f"  -> {direction} deja assignee, camera {index} ignoree")

    # Verifier les directions manquantes
    if directions_restantes:
        print(f"\n  ATTENTION: Directions sans camera: {directions_restantes}")
        print("  Ces voies utiliseront le fallback (trafic moyen par defaut)")

    sauvegarder_mapping(mapping)

    print("\n=== Calibration terminee ===")
    print("  Le pipeline chargera ce mapping au prochain demarrage.")
    print("  Pour verifier: python3 calibration_cameras.py verify")
    print("  Mode rapide:   python3 calibration_cameras.py rapide")


if __name__ == "__main__":
    main()
