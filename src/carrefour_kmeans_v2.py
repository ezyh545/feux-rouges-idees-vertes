"""
carrefour_kmeans_v2.py - K-Means 6 clusters + Decision + Visualisation
========================================================================
Ce fichier est le module de decision par clustering K-Means.
Il entraine un modele K-Means sur 600 echantillons synthetiques,
puis assigne chaque cluster a une action de feux via un matching
base sur les profils ideaux (algorithme hongrois simplifie).

UTILISATION :
  from carrefour_kmeans_v2 import GestionnaireCarrefour
  g = GestionnaireCarrefour()
  g.entrainer()
  action, confiance = g.decider([0, 1, 1, 0, 2, 0, 0, 1])

  # Standalone : python3 carrefour_kmeans_v2.py
"""

import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import logging

logger = logging.getLogger(__name__)

# === Les 6 actions valides ===
ACTIONS = ['NORD_SEUL', 'SUD_SEUL', 'EST_SEUL', 'OUEST_SEUL', 'NORD_SUD', 'EST_OUEST']

# === Profils ideaux pour chaque action ===
# Format : [pN, pS, pE, pW, vN, vS, vE, vW]
PROFILS_IDEAUX = {
    'NORD_SEUL':  [0, 1, 1, 1, 2, 0, 0, 0],
    'SUD_SEUL':   [1, 0, 1, 1, 0, 2, 0, 0],
    'EST_SEUL':   [1, 1, 0, 1, 0, 0, 2, 0],
    'OUEST_SEUL': [1, 1, 1, 0, 0, 0, 0, 2],
    'NORD_SUD':   [0, 0, 1, 1, 2, 2, 0, 0],
    'EST_OUEST':  [1, 1, 0, 0, 0, 0, 2, 2],
}


class GestionnaireCarrefour:
    """
    Gestionnaire de carrefour par K-Means.

    Pipeline :
    1. Genere 600 echantillons synthetiques (100 par action)
    2. Entraine K-Means avec 6 clusters
    3. Associe chaque cluster a une action via matching
    4. Predit l'action pour un nouveau vecteur de features
    """

    def __init__(self, n_clusters=6, random_state=42):
        self.n_clusters = n_clusters
        self.random_state = random_state
        self.kmeans = None
        self.scaler = StandardScaler()
        self.cluster_to_action = {}
        self.est_entraine = False

    def _generer_donnees_synthetiques(self, n_par_action=100):
        """Genere des donnees synthetiques equilibrees pour l'entrainement."""
        np.random.seed(self.random_state)
        X = []
        y_true = []

        for idx, (action, profil) in enumerate(PROFILS_IDEAUX.items()):
            for _ in range(n_par_action):
                sample = []
                for i, val in enumerate(profil):
                    if i < 4:  # Pietons (0 ou 1)
                        # Biaiser vers la valeur du profil
                        prob = 0.8 if val == 1 else 0.2
                        sample.append(np.random.choice([0, 1], p=[1-prob, prob]))
                    else:  # Vehicules (0, 1, 2)
                        if val == 2:
                            sample.append(np.random.choice([0, 1, 2], p=[0.05, 0.15, 0.80]))
                        elif val == 0:
                            sample.append(np.random.choice([0, 1, 2], p=[0.70, 0.25, 0.05]))
                        else:
                            sample.append(np.random.choice([0, 1, 2], p=[0.20, 0.60, 0.20]))
                X.append(sample)
                y_true.append(action)

        return np.array(X, dtype=float), y_true

    def _matcher_clusters(self, X_scaled):
        """
        Associe chaque cluster a une action via un algorithme hongrois simplifie.
        Compare les centroides aux profils ideaux normalises.
        """
        # Normaliser les profils ideaux avec le meme scaler
        profils = np.array([PROFILS_IDEAUX[a] for a in ACTIONS], dtype=float)
        profils_scaled = self.scaler.transform(profils)

        centroides = self.kmeans.cluster_centers_
        n = len(ACTIONS)

        # Matrice de distances
        distances = np.zeros((n, n))
        for i in range(n):  # cluster
            for j in range(n):  # action
                distances[i][j] = np.linalg.norm(centroides[i] - profils_scaled[j])

        # Matching glouton (argmin iteratif, sans doublon)
        clusters_assignes = set()
        actions_assignees = set()
        self.cluster_to_action = {}

        for _ in range(n):
            min_dist = float('inf')
            best_cluster = -1
            best_action_idx = -1

            for i in range(n):
                if i in clusters_assignes:
                    continue
                for j in range(n):
                    if j in actions_assignees:
                        continue
                    if distances[i][j] < min_dist:
                        min_dist = distances[i][j]
                        best_cluster = i
                        best_action_idx = j

            self.cluster_to_action[best_cluster] = ACTIONS[best_action_idx]
            clusters_assignes.add(best_cluster)
            actions_assignees.add(best_action_idx)

        logger.info(f"Matching clusters -> actions: {self.cluster_to_action}")

    def entrainer(self):
        """Entraine le modele K-Means et effectue le matching."""
        logger.info("Entrainement K-Means...")

        # Generer les donnees
        X, y_true = self._generer_donnees_synthetiques()
        logger.info(f"Donnees generees: {X.shape[0]} echantillons, {X.shape[1]} features")

        # Normaliser
        X_scaled = self.scaler.fit_transform(X)

        # Entrainer K-Means
        self.kmeans = KMeans(
            n_clusters=self.n_clusters,
            random_state=self.random_state,
            n_init=20,
            max_iter=500
        )
        self.kmeans.fit(X_scaled)
        logger.info(f"K-Means entraine: inertie={self.kmeans.inertia_:.2f}")

        # Matcher clusters aux actions
        self._matcher_clusters(X_scaled)

        # Evaluer la concordance
        predictions = self.kmeans.predict(X_scaled)
        concordance = sum(
            1 for pred, true in zip(predictions, y_true)
            if self.cluster_to_action.get(pred) == true
        ) / len(y_true)
        logger.info(f"Concordance: {concordance:.1%}")

        self.est_entraine = True
        return concordance

    def decider(self, vecteur):
        """
        Prend une decision pour un vecteur de features donne.

        Args:
            vecteur: list [pN, pS, pE, pW, vN, vS, vE, vW]

        Returns:
            tuple (action: str, confiance: float)
        """
        if not self.est_entraine:
            raise RuntimeError("Le modele n'est pas entraine. Appelez entrainer() d'abord.")

        X = np.array([vecteur], dtype=float)
        X_scaled = self.scaler.transform(X)

        cluster = self.kmeans.predict(X_scaled)[0]
        action = self.cluster_to_action.get(cluster, 'NORD_SUD')  # fallback

        # Confiance = inverse de la distance au centroide
        centroide = self.kmeans.cluster_centers_[cluster]
        distance = np.linalg.norm(X_scaled[0] - centroide)
        confiance = 1.0 / (1.0 + distance)

        return action, confiance

    def evaluer_modele(self):
        """Evaluation complete avec matrice de confusion."""
        if not self.est_entraine:
            self.entrainer()

        X, y_true = self._generer_donnees_synthetiques()
        X_scaled = self.scaler.transform(X)
        predictions = self.kmeans.predict(X_scaled)

        # Matrice de confusion
        print("\n=== Matrice de Concordance ===\n")
        print(f"{'':>15}", end="")
        for a in ACTIONS:
            print(f"{a[:8]:>10}", end="")
        print()

        for true_action in ACTIONS:
            print(f"{true_action[:15]:>15}", end="")
            for pred_cluster in range(self.n_clusters):
                pred_action = self.cluster_to_action.get(pred_cluster, "?")
                count = sum(
                    1 for p, t in zip(predictions, y_true)
                    if self.cluster_to_action.get(p) == pred_action and t == true_action
                )
                print(f"{count:>10}", end="")
            print()

        concordance = sum(
            1 for p, t in zip(predictions, y_true)
            if self.cluster_to_action.get(p) == t
        ) / len(y_true)
        print(f"\nConcordance globale: {concordance:.1%}")
        return concordance


# === TEST STANDALONE ===
if __name__ == "__main__":
    print("=== Test GestionnaireCarrefour ===\n")
    g = GestionnaireCarrefour()
    concordance = g.entrainer()

    # Tester quelques vecteurs
    tests = [
        ([0, 1, 1, 1, 2, 0, 0, 0], "NORD_SEUL attendu"),
        ([1, 0, 1, 1, 0, 2, 0, 0], "SUD_SEUL attendu"),
        ([0, 0, 1, 1, 2, 2, 0, 0], "NORD_SUD attendu"),
        ([1, 1, 0, 0, 0, 0, 2, 2], "EST_OUEST attendu"),
        ([0, 0, 0, 0, 1, 1, 1, 1], "Trafic equilibre"),
    ]

    print("\n=== Decisions ===\n")
    for vecteur, description in tests:
        action, confiance = g.decider(vecteur)
        print(f"  {vecteur} -> {action} (conf={confiance:.2f}) [{description}]")

    print()
    g.evaluer_modele()
