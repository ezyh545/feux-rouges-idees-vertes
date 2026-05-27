# Guide Pratique : Construction du Diorama + Optimisation YOLO

## 1. Construction du Diorama

### Materiel recommande (budget ~100 MAD)
- Plaque de carton rigide 60x60cm (base)
- Carton gris pour les routes (peint en gris fonce)
- Peinture blanche pour le marquage routier
- Papier vert pour les zones de vegetation
- Colle forte + cutter

### Schema de la maquette

```
        [Cam NORD]
           |
    -------+-------
    |  N   |      |
    |  ^   |      |
----+--+---+------+----
    |      |  ->E |
    |      |      |
----+------+--+---+----
    |      |  v   |
    |      |  S   |
    -------+-------
           |
        [Cam SUD]

[Cam OUEST] <-     -> [Cam EST]
```

### Regles critiques
1. Chaque voie doit faire au moins 10cm de large (pour que les voitures en papier soient visibles)
2. Les cameras doivent etre a 25-30cm de hauteur, orientees en plongee legere (30 degres)
3. Le fond de la route doit etre SOMBRE (gris/noir) pour maximiser le contraste avec les voitures
4. Pas de surface brillante : utiliser du papier mat ou du carton peint

### Placement des LEDs
- Plantez les LEDs directement dans le carton a chaque entree du carrefour
- Un petit rectangle de carton blanc derriere chaque LED amplifie la visibilite
- Fils sous la maquette, breadboard cachee en dessous

## 2. Optimisation des Voitures en Papier

### Pourquoi ca marche
YOLOv8 a ete entraine sur des PHOTOS de voitures (dataset COCO). 
Une photo imprimee d'une voiture est donc exactement le type d'input qu'il attend.

### Regles pour maximiser la detection

| Critere | Bon | Mauvais |
|---------|-----|---------|
| Taille minimum | 6cm x 4cm minimum | < 4cm (trop petit) |
| Angle | Vue 3/4 avant ou laterale | Vue de dessus (top-down) |
| Fond | Transparent ou decoupe propre | Fond blanc rectangulaire |
| Papier | Mat (80g standard) | Glace/brillant (reflets) |
| Contraste | Voiture sombre sur route claire, ou voiture coloree sur route sombre | Voiture grise sur route grise |
| Resolution impression | 300 DPI minimum | Impression basse qualite |

### Modeles recommandes
Cherchez sur Google Images avec ces termes :
- "car side view transparent background PNG"
- "sedan 3/4 view cutout"
- "bus side view PNG transparent"
- "motorcycle side view cutout"
- "pedestrian walking side view PNG"

### Astuce critique : le seuil de confiance
Si YOLO ne detecte pas vos papiers :
1. D'abord, agrandissez les images (8cm x 5cm minimum)
2. Ensuite, baissez le seuil : `SEUIL_CONFIANCE = 0.30` (au lieu de 0.40)
3. En dernier recours : `SEUIL_CONFIANCE = 0.25`
4. ATTENTION : trop bas = faux positifs (detecte des voitures dans le decor)

### Test rapide
```bash
# Tester la detection sur une seule image
python3 test_yolo_live.py
# Appuyer sur + ou - pour ajuster le seuil en direct
# Appuyer sur S pour sauvegarder une capture avec les detections
```

## 3. Eclairage pour la Foire

### Probleme
Les foires ont un eclairage au neon/LED puissant et variable qui cause :
- Reflets sur le papier
- Ombres des visiteurs
- Lumiere directe dans les webcams

### Solutions
1. **Eclairage integre** : Fixez une petite lampe LED USB (type lampe de bureau flexible) au-dessus de la maquette, pointant vers le bas. Cela cree un eclairage controle et constant.
2. **Pare-soleil cameras** : Entourez chaque webcam d'un petit tube en carton noir (3cm) pour bloquer la lumiere laterale.
3. **Tester avant** : Arrivez 1h avant l'ouverture pour ajuster l'eclairage et recalibrer si necessaire.

## 4. Checklist Pre-Demo

- [ ] Toutes les voitures en papier sont detectees (tester chaque une)
- [ ] Les 4 cameras voient leur voie respective (calibration_cameras.py)
- [ ] Les 12 LEDs fonctionnent (test_gpio.py sur chaque direction)
- [ ] Le dashboard s'affiche correctement en fullscreen
- [ ] Le ventilateur du RPi tourne
- [ ] La carte SD a ete backupee
- [ ] Le cable d'alimentation du RPi est securise (scotch)
- [ ] Le hub USB est alimente et stable
- [ ] 3 scenarios de demo sont repetes et chronometres
- [ ] test_interactive.py est pret comme plan B
