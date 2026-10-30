"""EXPLORATORY (not pre-registered). Are the families real groups or slices of a continuum? Monte Carlo test stricter than the Gaussian comparison:
the null data keep the distribution of each variable (skew, tails, bounded values) and the correlation between variables (Gaussian copula), but have no groups.
Statistics: K-Means silhouette and Jaccard stability (bootstrap over matches), observed on the exploration matches and compared with B null data sets.
p = (1 + number of nulls with silhouette >= observed) / (B + 1). No reserved match is used.
Usage: python exploratory_cluster_test.py <matches.json> "<Team>" [data_folder=.]"""

import sys, os, json, warnings
import numpy as np

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "week2"))
import sequences_clustering as S
from scipy.stats import norm, rankdata
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score

COLS = ["x0", "w0", "x1", "w1", "net_x", "path_len", "directness", "n_pass", "long_share", "width_std", "dur"]
CUT = 45
K = {"costruzione": 5, "avanzata": 3}
B = 100
BJ = 60
df, nm = S.extract()
k0 = int(round(nm * 0.7))
ex = df[df.gi < k0].reset_index(drop=True)
ex["w0"] = (ex.y0 - 40).abs()
ex["w1"] = (ex.y1 - 40).abs()
rng = np.random.default_rng(31)


def copula(X):
    n, d = X.shape
    Z = norm.ppf((rankdata(X, axis=0) - 0.5) / n)
    C = np.corrcoef(Z.T)
    Zs = rng.multivariate_normal(np.zeros(d), C, size=n)
    U = norm.cdf(Zs)
    return np.column_stack([np.quantile(X[:, j], U[:, j]) for j in range(d)])


def jaccard(X, g, k, B_):
    lab = KMeans(k, n_init=10, random_state=0).fit(X).labels_
    games = np.unique(g)
    by = {x: np.where(g == x)[0] for x in games}
    sc = np.zeros(k)
    for _ in range(B_):
        idx = np.concatenate([by[x] for x in rng.choice(games, len(games))])
        lb = KMeans(k, n_init=3, random_state=int(rng.integers(1e9))).fit(X[idx]).predict(X)
        for c in range(k):
            a = lab == c
            sc[c] += max((a & (lb == j)).sum() / (a | (lb == j)).sum() for j in range(k))
    return float((sc / B_).mean())


out = {
    "team": S.TEAM,
    "nota": "ESPLORATIVO, non pre-registrato; nulla = copula gaussiana (stesse marginali e correlazioni, nessun gruppo)",
    "B": B,
}
for fase, k in K.items():
    sub = (ex[ex.x0 < CUT] if fase == "costruzione" else ex[ex.x0 >= CUT]).reset_index(drop=True)
    Xr = sub[COLS].values
    g = sub.gi.values
    X = StandardScaler().fit_transform(Xr)
    s_obs = float(silhouette_score(X, KMeans(k, n_init=10, random_state=0).fit(X).labels_))
    j_obs = jaccard(X, g, k, BJ)
    sn = []
    for _ in range(B):
        Xn = StandardScaler().fit_transform(copula(Xr))
        sn.append(silhouette_score(Xn, KMeans(k, n_init=3, random_state=0).fit(Xn).labels_))
    Xj = StandardScaler().fit_transform(copula(Xr))
    j_null = jaccard(Xj, g, k, BJ)
    p = (1 + sum(s >= s_obs for s in sn)) / (B + 1)
    out[fase] = dict(
        n=int(len(sub)),
        silhouette_osservata=s_obs,
        silhouette_nulla_media=float(np.mean(sn)),
        silhouette_nulla_p95=float(np.percentile(sn, 95)),
        p_silhouette=float(p),
        jaccard_osservato=j_obs,
        jaccard_nullo=j_null,
    )
    print(
        f"[{S.TEAM} {fase}] silhouette {s_obs:.3f} | nulla media {np.mean(sn):.3f}, p95 {np.percentile(sn, 95):.3f} | p = {p:.3f} | Jaccard osservato {j_obs:.2f} vs nullo {j_null:.2f}"
    )
json.dump(
    out,
    open(f"{S.BASE}/exploratory_cluster_test_{S.TEAM.replace(' ', '_')}.json", "w", encoding="utf-8"),
    indent=1,
    ensure_ascii=False,
)
