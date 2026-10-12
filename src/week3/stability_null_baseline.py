"""Baseline nulla per la stabilita' L2: stesso match-bootstrap, ma su dati senza struttura di gruppo.
Uso: python stability_null_baseline.py <matches.json> "<Squadra>" [cartella_dati=.]
Null 1 (shuffle): ogni feature viene permutata indipendentemente (stesse distribuzioni marginali, correlazioni distrutte).
Null 2 (gauss): dati gaussiani con la stessa media e covarianza (stessa correlazione, ma un solo blob, nessun cluster reale).
Se il Jaccard osservato e' ben sopra i due null, la stabilita' non e' un artefatto di K-Means."""
import sys, os, json, warnings
import numpy as np
warnings.filterwarnings("ignore"); sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "week2"))
import sequences_clustering as S
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
COLS = ["x0", "w0", "x1", "w1", "net_x", "path_len", "directness", "n_pass", "long_share", "width_std", "dur"]
df, nm = S.extract(); k0 = int(round(nm * 0.7)); ex = df[df.gi < k0].reset_index(drop=True)
ex["w0"] = (ex.y0 - 40).abs(); ex["w1"] = (ex.y1 - 40).abs()
rng = np.random.default_rng(11)

def jaccard_boot(X, games_arr, k, B=100):
    lab = KMeans(k, n_init=10, random_state=0).fit(X).labels_
    games = np.unique(games_arr); by = {g: np.where(games_arr == g)[0] for g in games}; sc = np.zeros(k)
    for _ in range(B):
        gs = rng.choice(games, len(games)); idx = np.concatenate([by[g] for g in gs])
        lb = KMeans(k, n_init=3, random_state=int(rng.integers(1e9))).fit(X[idx]).predict(X)
        for c in range(k):
            a = lab == c; sc[c] += max((a & (lb == j)).sum() / (a | (lb == j)).sum() for j in range(k))
    return float((sc / B).mean()), float((sc / B).min()), float(silhouette_score(X, lab))

out = {}
for fase, k, sub in [("costruzione", 5, ex[ex.x0 < 45]), ("avanzata", 3, ex[ex.x0 >= 45])]:
    sub = sub.reset_index(drop=True); g = sub.gi.values; X = StandardScaler().fit_transform(sub[COLS].values)
    r = {"osservato": jaccard_boot(X, g, k)}
    sh = np.column_stack([rng.permutation(X[:, j]) for j in range(X.shape[1])]); r["null_shuffle"] = jaccard_boot(sh, g, k)
    ga = rng.multivariate_normal(X.mean(0), np.cov(X.T), size=len(X)); r["null_gauss"] = jaccard_boot(ga, g, k)
    out[fase] = {n: dict(jaccard_mean=v[0], jaccard_min=v[1], silhouette=v[2]) for n, v in r.items()}
    print(f"[{fase} k={k}] " + " | ".join(f"{n}: J {v[0]:.2f} (min {v[1]:.2f}) sil {v[2]:.2f}" for n, v in r.items()))
json.dump(out, open(f"{S.BASE}/null_baseline_{S.TEAM.replace(' ','_')}.json", "w"), indent=1)
