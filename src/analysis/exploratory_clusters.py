"""EXPLORATORY (not pre-registered). Are the families real groups, and do they depend on the method? Exploration matches only.
  copula   real groups or slices of a continuum? K-Means silhouette and Jaccard stability on the real data against 100 null data
           sets with the same distribution of each variable and the same correlations (Gaussian copula) but no groups.
           p = (1 + nulls with silhouette >= observed) / 101                                  -> exploratory_cluster_test_<Team>.json
  methods  K-Means vs Gaussian mixture vs Ward (same k), and K-Means with other k and cut; Jaccard against a Gaussian null.
           The thesis method does not change: this only shows how much the results move.     -> exploratory_robustness_<Team>.json
Usage: python exploratory_clusters.py copula|methods <matches.json> "<Team>" [data_folder=.]
(Until 6 Nov 2026 these were two files: exploratory_cluster_test.py and exploratory_robustness.py.)"""

import sys, os, json, warnings
import numpy as np

warnings.filterwarnings("ignore")
if len(sys.argv) < 4 or sys.argv[1] not in ("copula", "methods"):
    sys.exit(__doc__)
WHAT = sys.argv[1]
sys.argv = [sys.argv[0]] + sys.argv[2:]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sequences_clustering as S
from scipy.stats import norm, rankdata
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, adjusted_rand_score

COLS = ["x0", "w0", "x1", "w1", "net_x", "path_len", "directness", "n_pass", "long_share", "width_std", "dur"]
CUT = 45
K = {"costruzione": 5, "avanzata": 3}
FN = S.TEAM.replace(" ", "_")

df, n_matches = S.extract()
k0 = int(round(n_matches * 0.7))
ex = df[df.gi < k0].reset_index(drop=True)
ex["w0"] = (ex.y0 - 40).abs()
ex["w1"] = (ex.y1 - 40).abs()


def phase_data(cut, phase):
    if phase == "costruzione":
        sub = ex[ex.x0 < cut]
    else:
        sub = ex[ex.x0 >= cut]
    return sub.reset_index(drop=True)


def best_jaccard(labels, new, c, k, safe):
    # how well group c is found again in the new labels (best Jaccard over the new groups)
    a = labels == c
    best = 0
    for j in range(k):
        union = (a | (new == j)).sum()
        if safe:
            union = max(union, 1)
        best = max(best, (a & (new == j)).sum() / union)
    return best


# ---------------------------------------------------------------- copula
def copula_test():
    rng = np.random.default_rng(31)
    B = 100  # null data sets for the silhouette
    BJ = 60  # bootstrap samples for the Jaccard

    def copula(X):
        # same marginals and rank correlations as X, no groups
        n, d = X.shape
        Z = norm.ppf((rankdata(X, axis=0) - 0.5) / n)
        C = np.corrcoef(Z.T)
        U = norm.cdf(rng.multivariate_normal(np.zeros(d), C, size=n))
        return np.column_stack([np.quantile(X[:, j], U[:, j]) for j in range(d)])

    def jaccard(X, g, k):
        labels = KMeans(k, n_init=10, random_state=0).fit(X).labels_
        games = np.unique(g)
        rows_of = {x: np.where(g == x)[0] for x in games}
        score = np.zeros(k)
        for _ in range(BJ):
            idx = np.concatenate([rows_of[x] for x in rng.choice(games, len(games))])
            new = KMeans(k, n_init=3, random_state=int(rng.integers(1e9))).fit(X[idx]).predict(X)
            for c in range(k):
                score[c] += best_jaccard(labels, new, c, k, safe=False)
        return float((score / BJ).mean())

    out = {
        "team": S.TEAM,
        "nota": "ESPLORATIVO, non pre-registrato; nulla = copula gaussiana (stesse marginali e correlazioni, nessun gruppo)",
        "B": B,
    }
    for phase, k in K.items():
        sub = phase_data(CUT, phase)
        raw = sub[COLS].values
        g = sub.gi.values
        X = StandardScaler().fit_transform(raw)
        s_obs = float(silhouette_score(X, KMeans(k, n_init=10, random_state=0).fit(X).labels_))
        j_obs = jaccard(X, g, k)
        s_null = []
        for _ in range(B):
            Xn = StandardScaler().fit_transform(copula(raw))
            s_null.append(silhouette_score(Xn, KMeans(k, n_init=3, random_state=0).fit(Xn).labels_))
        j_null = jaccard(StandardScaler().fit_transform(copula(raw)), g, k)
        p = (1 + sum(s >= s_obs for s in s_null)) / (B + 1)
        out[phase] = {
            "n": int(len(sub)),
            "silhouette_osservata": s_obs,
            "silhouette_nulla_media": float(np.mean(s_null)),
            "silhouette_nulla_p95": float(np.percentile(s_null, 95)),
            "p_silhouette": float(p),
            "jaccard_osservato": j_obs,
            "jaccard_nullo": j_null,
        }
        print(
            f"[{S.TEAM} {phase}] silhouette {s_obs:.3f} | nulla media {np.mean(s_null):.3f}, p95 {np.percentile(s_null, 95):.3f} | p = {p:.3f} | Jaccard osservato {j_obs:.2f} vs nullo {j_null:.2f}"
        )
    json.dump(out, open(f"{S.BASE}/exploratory_cluster_test_{FN}.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)


# ---------------------------------------------------------------- methods
def methods_test():
    rng = np.random.default_rng(57)
    BJ = 40

    def fit(method, X, k, seed=0):
        # labels on X, and a function that labels new points (Ward has none: nearest group mean)
        if method == "kmeans":
            m = KMeans(k, n_init=10 if seed == 0 else 3, random_state=seed).fit(X)
            return m.labels_, m.predict
        if method == "gmm":
            m = GaussianMixture(k, covariance_type="full", n_init=3, random_state=seed).fit(X)
            return m.predict(X), m.predict
        labels = AgglomerativeClustering(k, linkage="ward").fit_predict(X)
        centres = np.array([X[labels == c].mean(0) for c in range(k)])

        def nearest_centre(Z):
            return np.argmin(((Z[:, None, :] - centres[None]) ** 2).sum(-1), 1)

        return labels, nearest_centre

    def jaccard(method, X, g, k):
        labels, _ = fit(method, X, k)
        games = np.unique(g)
        rows_of = {x: np.where(g == x)[0] for x in games}
        score = np.zeros(k)
        for _ in range(BJ):
            idx = np.concatenate([rows_of[x] for x in rng.choice(games, len(games))])
            _, predict = fit(method, X[idx], k, int(rng.integers(1, 1e9)))
            new = predict(X)
            for c in range(k):
                score[c] += best_jaccard(labels, new, c, k, safe=True)
        return float((score / BJ).mean())

    def scaled(cut, phase):
        sub = phase_data(cut, phase)
        return StandardScaler().fit_transform(sub[COLS].values), sub.gi.values

    out = {
        "team": S.TEAM,
        "nota": "ESPLORATIVO, non pre-registrato; solo partite di esplorazione; il metodo della tesi non cambia",
        "BJ": BJ,
        "metodi": {},
        "sensibilita": {},
    }
    # 1) three algorithms, same k
    for phase, k in K.items():
        X, g = scaled(CUT, phase)
        ref, _ = fit("kmeans", X, k)
        res = {}
        for m in ("kmeans", "gmm", "ward"):
            labels, _ = fit(m, X, k)
            res[m] = {
                "ari_vs_kmeans": float(adjusted_rand_score(ref, labels)),
                "silhouette": float(silhouette_score(X, labels)),
                "jaccard": jaccard(m, X, g, k),
            }
            print(f"[{S.TEAM} {phase} {m}] ARI vs K-Means {res[m]['ari_vs_kmeans']:.2f} | silhouette {res[m]['silhouette']:.3f} | Jaccard {res[m]['jaccard']:.2f}")
        out["metodi"][phase] = dict(n=int(len(X)), k=k, **res)

    # 2) K-Means with other k and cut, against a Gaussian null
    grid = [
        ("costruzione", 45, 4),
        ("costruzione", 45, 5),
        ("costruzione", 45, 6),
        ("costruzione", 40, 5),
        ("costruzione", 50, 5),
        ("avanzata", 45, 2),
        ("avanzata", 45, 3),
        ("avanzata", 45, 4),
    ]
    for phase, cut, k in grid:
        X, g = scaled(cut, phase)
        labels, _ = fit("kmeans", X, k)
        j = jaccard("kmeans", X, g, k)
        Xn = rng.multivariate_normal(X.mean(0), np.cov(X.T), size=len(X))
        jn = jaccard("kmeans", Xn, g, k)
        key = f"{phase}_x{cut}_k{k}"
        sil = float(silhouette_score(X, labels))
        out["sensibilita"][key] = {
            "fase": phase,
            "cut": cut,
            "k": k,
            "n": int(len(X)),
            "jaccard": j,
            "jaccard_null_gauss": jn,
            "margin": j - jn,
            "silhouette": sil,
        }
        print(f"[{S.TEAM} {key}] n {len(X)} | Jaccard {j:.2f} vs nullo {jn:.2f} (margine {j - jn:+.2f}) | silhouette {sil:.3f}")
    json.dump(out, open(f"{S.BASE}/exploratory_robustness_{FN}.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)


if WHAT == "copula":
    copula_test()
else:
    methods_test()
