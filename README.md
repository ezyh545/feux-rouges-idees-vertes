# Feux Rouges, Idees Vertes

**Systeme de Gestion Intelligente de Carrefour par Vision par Ordinateur et IA**

Projet PLBD-12 | Ecole Centrale Casablanca | 2025-2026

---

## Le Probleme

Les feux de circulation classiques fonctionnent sur des cycles fixes, aveugles au trafic reel. Resultat : des voies vides au vert pendant que des files s'accumulent ailleurs. A Casablanca, un conducteur perd en moyenne 45 minutes par jour dans les embouteillages.

## Notre Solution

Un systeme embarque sur Raspberry Pi 5 qui observe le trafic en temps reel via 4 cameras USB et prend des decisions intelligentes grace a YOLOv8 (detection) et K-Means (decision).
```
4 Cameras USB -> YOLOv8-nano (detection vehicules/pietons)
              -> Vecteur 8 features [pN,pS,pE,pW,vN,vS,vE,vW]
              -> K-Means 6 clusters (decision)
              -> GPIO 12 LEDs (feux tricolores)
              -> Dashboard pygame (visualisation temps reel)
```

## Architecture Technique

| Composant | Technologie |
|-----------|------------|
| Hardware | Raspberry Pi 5 (4 Go RAM) |
| Detection | YOLOv8-nano (PyTorch CPU-only) |
| Decision | K-Means (scikit-learn, 6 clusters) |
| Cameras | 4 webcams USB via hub alimente |
| Affichage | pygame 1280x720 sur HDMI |
| LEDs | 12 LEDs GPIO (3 couleurs x 4 directions) |
| OS | Raspberry Pi OS Desktop 64-bit (Bookworm, X11) |

## Structure du Projet

```
feux-rouges-idees-vertes/
|-- src/                        # Code source principal
|   |-- main_v2.py              # Pipeline principal (point d'entree)
|   |-- feature_extractor_v2.py # Capture cameras + YOLO (avec fallback)
|   |-- carrefour_kmeans_v2.py  # K-Means 6 clusters + decision
|   |-- gpio_controller_v2.py   # Controle LEDs + phase tout-rouge
|   |-- dashboard.py            # Affichage pygame temps reel
|   |-- pipeline_logger.py      # Logging CSV + mesure latence
|   |-- calibration_cameras.py  # Recalibration rapide des cameras
|   +-- simulation_comparative.py # Comparaison cycle fixe vs intelligent
|
|-- tests/                      # Scripts de test individuels
|   |-- test_camera.py          # Test capture webcam
|   |-- test_gpio.py            # Test LEDs sequentiel
|   |-- test_video.py           # Test flux video brut
|   |-- test_yolo_live.py       # Test detection YOLO en direct
|   |-- test_single_lane.py     # Test pipeline 1 voie
|   +-- test_interactive.py     # GUI interactive de test
|
|-- scripts/                    # Scripts utilitaires
|   +-- backup_sd.sh            # Backup carte SD
|
|-- docs/                       # Documentation
|   |-- GUIDE_MAQUETTE_YOLO.md  # Guide construction diorama + YOLO papier
|   +-- AUDIT_PLBD12_Complet.docx # Audit technique complet
|
|-- logs/                       # Logs generes (ignore par git)
|-- camera_mapping.json         # Mapping cameras (genere par calibration)
|-- requirements.txt            # Dependances Python
+-- .gitignore
```

## Installation sur Raspberry Pi 5

### 1. Prerequis systeme
```bash
# Passer en X11 (obligatoire pour OpenCV/pygame)
sudo raspi-config  # Advanced Options -> Wayland -> X11

# Packages systeme
sudo apt update && sudo apt install -y python3-opencv libsdl2-dev libsdl2-mixer-dev
```

### 2. Dependances Python
```bash
# PyTorch CPU-only (CRITIQUE : evite de remplir la SD avec CUDA)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu --break-system-packages

# Ultralytics sans dependances lourdes
pip install ultralytics --no-deps --break-system-packages

# Autres dependances
pip install -r requirements.txt --break-system-packages

# GPIO pour RPi 5 (remplace RPi.GPIO)
pip install rpi-lgpio --break-system-packages
```

### 3. Calibration des cameras
```bash
# Brancher les 4 cameras au hub USB
cd src/
python3 calibration_cameras.py        # Mode normal
python3 calibration_cameras.py rapide # Mode rapide (mosaique)
python3 calibration_cameras.py verify # Verification
```

### 4. Lancement
```bash
cd src/
python3 main_v2.py                    # Mode normal
python3 main_v2.py --debug            # Mode debug
python3 main_v2.py --no-dashboard     # Sans affichage
python3 main_v2.py --intervalle 10    # Cycle de 10s
```

## Tests Individuels

```bash
cd tests/
python3 test_camera.py          # Tester 1 webcam
python3 test_gpio.py            # Tester les LEDs
python3 test_yolo_live.py       # Detection YOLO en direct (+/- pour seuil)
python3 test_single_lane.py     # Pipeline complet sur 1 voie
python3 test_interactive.py     # GUI interactive (plan B pour la demo)
```

## Simulation Comparative

```bash
cd src/
python3 simulation_comparative.py
# -> Compare cycle fixe vs systeme intelligent
# -> Genere resultats_simulation.csv
```

## Backup Carte SD

```bash
sudo bash scripts/backup_sd.sh
# -> Cree une image compressee sur cle USB
```

## Assignation GPIO (BCM)

| Direction | Rouge | Jaune | Vert |
|-----------|-------|-------|------|
| NORD      | 17    | 27    | 22   |
| SUD       | 23    | 24    | 25   |
| EST       | 5     | 6     | 13   |
| OUEST     | 19    | 26    | 16   |

## Les 6 Combinaisons de Feux

| Action | Feux Verts | Feux Rouges | Cas typique |
|--------|-----------|-------------|-------------|
| NORD_SEUL | NORD | SUD, EST, OUEST | Fort flux Nord |
| SUD_SEUL | SUD | NORD, EST, OUEST | Fort flux Sud |
| EST_SEUL | EST | NORD, SUD, OUEST | Fort flux Est |
| OUEST_SEUL | OUEST | NORD, SUD, EST | Fort flux Ouest |
| NORD_SUD | NORD + SUD | EST, OUEST | Axe N-S charge |
| EST_OUEST | EST + OUEST | NORD, SUD | Axe E-O charge |

## Budget

| Composant | Quantite | Prix (MAD) |
|-----------|----------|------------|
| Raspberry Pi 5 (4 Go) | 1 | ~1 000 |
| Webcam HD USB | 4 | ~280 |
| LEDs + resistances | 12+20 | ~30 |
| Breadboard + fils | 1 kit | ~50 |
| Ventilateur RPi 5 | 1 | ~90 |
| Cable HDMI | 1 | ~40 |
| Hub USB alimente | 1 | ~80 |
| Materiaux maquette | - | ~100 |
| **TOTAL** | | **~1 670 MAD** |

## Equipe

Projet PLBD-12 - Ecole Centrale Casablanca

## Licence

Projet academique - Ecole Centrale Casablanca 2025-2026
