"""
test_single_lane.py - Pipeline complet sur 1 voie
Usage: python3 test_single_lane.py [index_camera] [direction]
Les 3 autres voies sont traitees comme vides.
"""
import sys
import time
sys.path.insert(0, '../src')

from feature_extractor_v2 import FeatureExtractorV2
from carrefour_kmeans_v2 import GestionnaireCarrefour
from gpio_controller_v2 import ControleurFeuxV2

index = int(sys.argv[1]) if len(sys.argv) > 1 else 0
direction = sys.argv[2].upper() if len(sys.argv) > 2 else "NORD"

print(f"=== Test pipeline 1 voie : {direction} (camera {index}) ===\n")

# Init avec 1 seule camera
cameras = {'NORD': -1, 'SUD': -1, 'EST': -1, 'OUEST': -1}
cameras[direction] = index

extracteur = FeatureExtractorV2(cameras=cameras)
gestionnaire = GestionnaireCarrefour()
gestionnaire.entrainer()
controleur = ControleurFeuxV2()

try:
    while True:
        vecteur, images = extracteur.extraire()
        action, confiance = gestionnaire.decider(vecteur)
        controleur.changer(action)
        print(f"Vecteur={vecteur} -> {action} (conf={confiance:.2f})")
        time.sleep(5)
except KeyboardInterrupt:
    print("\nArret.")
finally:
    controleur.cleanup()
