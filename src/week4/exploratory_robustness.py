"""ESPLORATIVO (non pre-registrato). Quanto dipendono le famiglie dalle scelte di metodo? Nessuna partita riservata viene usata; il metodo della tesi
(K-Means, k = 5 e 3, taglio x = 45) NON cambia: qui si misura solo quanto i risultati si muovono se le scelte fossero state altre.
1) Metodi: K-Means vs modello a misture gaussiane (GMM, covarianza piena) vs clustering gerarchico (Ward), stesso k.
   Accordo con K-Means (indice di Rand aggiustato, ARI), silhouette, stabilita' Jaccard con bootstrap sulle partite.
2) Sensibilita': costruzione con k = 4, 5, 6 (taglio 45) e taglio x = 40, 50 (k = 5); avanzata con k = 2, 3, 4.
   Stabilita' Jaccard, silhouette e margine sul nullo gaussiano (stessa media e covarianza, nessun gruppo), come in E1.
Uso: python exploratory_robustness.py <matches.json> "<Squadra>" [cartella_dati=.]   ->  exploratory_robustness_<Squadra>.json"""
import sys, os, json, warnings
import numpy as np
warnings.filterwarnings("ignore"); sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "week2"))
import sequences_clustering as S
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, adjusted_rand_score
COLS = ["x0", "w0", "x1", "w1", "net_x", "path_len", "directness", "n_pass", "long_share", "width_std", "dur"]; CUT = 45; K = {"costruzione": 5, "avanzata": 3}; BJ = 40
df, nm = S.extract(); k0 = int(round(nm * 0.7)); ex = df[df.gi < k0].reset_index(drop=True); ex["w0"] = (ex.y0 - 40).abs(); ex["w1"] = (ex.y1 - 40).abs()
rng = np.random.default_rng(57)

def fit(method, X, k, seed=0):
    """Labels on X and a function that assigns new points (nearest centre for Ward)."""
    if method == "kmeans":
        m = KMeans(k, n_init=10 if seed == 0 else 3, random_state=seed).fit(X); return m.labels_, m.predict
    if method == "gmm":
        m = GaussianMixture(k, covariance_type="full", n_init=3, random_state=seed).fit(X); return m.predict(X), m.predict
    lab = AgglomerativeClustering(k, linkage="ward").fit_predict(X); C = np.array([X[lab == c].mean(0) for c in range(k)])
    return lab, lambda Z: np.argmin(((Z[:, None, :] - C[None]) ** 2).sum(-1), 1)

def jaccard(method, X, g, k):
    lab, _ = fit(method, X, k); games = np.unique(g); by = {x: np.where(g == x)[0] for x in games}; sc = np.zeros(k)
    for _ in range(BJ):
        idx = np.concatenate([by[x] for x in rng.choice(games, len(games))]); _, pred = fit(method, X[idx], k, int(rng.integers(1, 1e9))); lb = pred(X)
        for c in range(k): a = lab == c; sc[c] += max((a & (lb == j)).sum() / max((a | (lb == j)).sum(), 1) for j in range(k))
    return float((sc / BJ).mean())

def phase(cut, which):
    sub = (ex[ex.x0 < cut] if which == "costruzione" else ex[ex.x0 >= cut]).reset_index(drop=True)
    return StandardScaler().fit_transform(sub[COLS].values), sub.gi.values

out = {"team": S.TEAM, "nota": "ESPLORATIVO, non pre-registrato; solo partite di esplorazione; il metodo della tesi non cambia", "BJ": BJ, "metodi": {}, "sensibilita": {}}
for fase, k in K.items():
    X, g = phase(CUT, fase); ref, _ = fit("kmeans", X, k); res = {}
    for m in ("kmeans", "gmm", "ward"):
        lab, _ = fit(m, X, k)
        res[m] = dict(ari_vs_kmeans=float(adjusted_rand_score(ref, lab)), silhouette=float(silhouette_score(X, lab)), jaccard=jaccard(m, X, g, k))
        print(f"[{S.TEAM} {fase} {m}] ARI vs K-Means {res[m]['ari_vs_kmeans']:.2f} | silhouette {res[m]['silhouette']:.3f} | Jaccard {res[m]['jaccard']:.2f}")
    out["metodi"][fase] = dict(n=int(len(X)), k=k, **res)

grid = [("costruzione", 45, 4), ("costruzione", 45, 5), ("costruzione", 45, 6), ("costruzione", 40, 5), ("costruzione", 50, 5), ("avanzata", 45, 2), ("avanzata", 45, 3), ("avanzata", 45, 4)]
for fase, cut, k in grid:
    X, g = phase(cut, fase); lab, _ = fit("kmeans", X, k); j = jaccard("kmeans", X, g, k)
    Xn = rng.multivariate_normal(X.mean(0), np.cov(X.T), size=len(X)); jn = jaccard("kmeans", Xn, g, k)
    key = f"{fase}_x{cut}_k{k}"; out["sensibilita"][key] = dict(fase=fase, cut=cut, k=k, n=int(len(X)), jaccard=j, jaccard_null_gauss=jn, margin=j - jn, silhouette=float(silhouette_score(X, lab)))
    print(f"[{S.TEAM} {key}] n {len(X)} | Jaccard {j:.2f} vs nullo {jn:.2f} (margine {j - jn:+.2f}) | silhouette {out['sensibilita'][key]['silhouette']:.3f}")
json.dump(out, open(f"{S.BASE}/exploratory_robustness_{S.TEAM.replace(' ', '_')}.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
