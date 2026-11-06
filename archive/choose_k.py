"""ARCHIVE (done once, 10 Oct 2026): choice of the number of families k on the exploration matches.
Tries k = 3..8 on a wide feature table (zones, path, play pattern) reduced with PCA, and prints silhouette and bootstrap stability.
Usage: python archive/choose_k.py <matches.json> "<Team>" [data_folder=.]   -> k_selection_<Team>.json (results/k_selection_Bayer_Leverkusen.json)
Moved here from src/analysis/sequences_clustering.py on 6 Nov 2026 (same code)."""

import os, sys, json
import numpy as np, pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "analysis"))
import sequences_clustering as S


def features(df):
    # wide feature table used only for the choice of k below
    F = {}
    for z in range(12):
        F[f"start_{S.ZN[z]}"] = (df.zone0 == z).astype(float).values
        F[f"end_{S.ZN[z]}"] = (df.zone1 == z).astype(float).values
    for z in range(12):
        F[f"occ_{S.ZN[z]}"] = np.array([np.mean([q == z for q in zs]) for zs in df.zones])
    for c in ("n_pass", "net_x", "path_len", "directness", "long_share", "width_std", "mean_x", "dur"):
        F[c] = df[c].values.astype(float)
    for pattern in sorted(S.OPEN_PLAY):
        F[f"pp_{pattern}"] = (df.play_pattern == pattern).astype(float).values
    return pd.DataFrame(F)


df, n_matches = S.extract()
k0 = int(round(n_matches * 0.7))
print(f"{S.TEAM}: {n_matches} partite, {len(df)} sequenze di gioco aperto (>=3 passaggi, >=4 punti); esplorazione = prime {k0} partite")
ex = df[df.gi < k0].reset_index(drop=True)
print("exploration sequences:", len(ex), "| riservate alla validazione:", int((df.gi >= k0).sum()))

X = StandardScaler().fit_transform(features(ex))
pca = PCA(0.90, random_state=0).fit(X)
X = pca.transform(X)
print("componenti PCA (90% varianza):", X.shape[1])

results = []
for k in range(3, 9):
    labels = KMeans(k, n_init=10, random_state=0).fit(X).labels_
    jac, ari, ari_ci = S.jaccard_stability(X, labels, k, B=100)
    sizes = sorted(np.bincount(labels).tolist(), reverse=True)
    sil = float(silhouette_score(X, labels))
    results.append(
        {
            "k": k,
            "silhouette": sil,
            "ari": ari,
            "jaccard_min": float(jac.min()),
            "jaccard_mean": float(jac.mean()),
            "sizes": sizes,
        }
    )
    print(f"k={k}: silhouette {sil:.3f} | ARI bootstrap {ari:.2f} | Jaccard min {jac.min():.2f} medio {jac.mean():.2f} | dimensioni {sizes}")
json.dump(results, open(f"{S.BASE}/k_selection_{S.TEAM.replace(' ', '_')}.json", "w"), indent=1)
