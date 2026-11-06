"""Are the families more stable than K-Means on data with no groups at all?
Usage: python stability_null_baseline.py <matches.json> "<Team>" [data_folder=.]
Same bootstrap over matches on three data sets (exploration matches only):
- observed: the real features
- null_shuffle: every feature shuffled on its own (same values, correlations destroyed)
- null_gauss: Gaussian data with the same mean and covariance (one blob, no groups)
If the real Jaccard is clearly above both, the stability is not just something K-Means always produces."""

import sys, os, json, warnings
import numpy as np

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "week2"))
import sequences_clustering as S
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score

COLS = ["x0", "w0", "x1", "w1", "net_x", "path_len", "directness", "n_pass", "long_share", "width_std", "dur"]

df, n_matches = S.extract()
k0 = int(round(n_matches * 0.7))
ex = df[df.gi < k0].reset_index(drop=True)
ex["w0"] = (ex.y0 - 40).abs()
ex["w1"] = (ex.y1 - 40).abs()
rng = np.random.default_rng(11)


def stability(X, match_of_row, k, B=100):
    # mean and min Jaccard over B bootstrap samples of matches, and the silhouette
    labels = KMeans(k, n_init=10, random_state=0).fit(X).labels_
    games = np.unique(match_of_row)
    rows_of = {}
    for g in games:
        rows_of[g] = np.where(match_of_row == g)[0]
    score = np.zeros(k)
    for _ in range(B):
        pick = rng.choice(games, len(games))
        idx = np.concatenate([rows_of[g] for g in pick])
        new = KMeans(k, n_init=3, random_state=int(rng.integers(1e9))).fit(X[idx]).predict(X)
        for c in range(k):
            a = labels == c
            best = 0
            for j in range(k):
                best = max(best, (a & (new == j)).sum() / (a | (new == j)).sum())
            score[c] += best
    score = score / B
    return float(score.mean()), float(score.min()), float(silhouette_score(X, labels))


out = {}
for phase, k in [("costruzione", 5), ("avanzata", 3)]:
    if phase == "costruzione":
        sub = ex[ex.x0 < 45].reset_index(drop=True)
    else:
        sub = ex[ex.x0 >= 45].reset_index(drop=True)
    g = sub.gi.values
    X = StandardScaler().fit_transform(sub[COLS].values)

    res = {}
    res["osservato"] = stability(X, g, k)
    shuffled = np.column_stack([rng.permutation(X[:, j]) for j in range(X.shape[1])])
    res["null_shuffle"] = stability(shuffled, g, k)
    gauss = rng.multivariate_normal(X.mean(0), np.cov(X.T), size=len(X))
    res["null_gauss"] = stability(gauss, g, k)

    out[phase] = {}
    line = f"[{phase} k={k}]"
    for name, (jmean, jmin, sil) in res.items():
        out[phase][name] = {"jaccard_mean": jmean, "jaccard_min": jmin, "silhouette": sil}
        line += f" {name}: J {jmean:.2f} (min {jmin:.2f}) sil {sil:.2f} |"
    print(line)

json.dump(out, open(f"{S.BASE}/null_baseline_{S.TEAM.replace(' ', '_')}.json", "w"), indent=1)
