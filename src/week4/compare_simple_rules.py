"""Do the families explain shots better than a simple rule? (protocol: docs/protocol_simple_rule.md)
For each phase: K-Means families (frozen on exploration) against a trivial partition with the same number of cells: equal-frequency bins of the end position x1
(main comparison), plus bins of net_x and n_pass (descriptive). Same model for all (logistic on the cells, C = 0.5), evaluated on the reserved matches.
Usage: python compare_simple_rules.py <matches.json> "<Team>" [data_folder=.] --confirm      (reserved matches; once only)
     python compare_simple_rules.py <matches.json> "<Team>" [data_folder=.] --dry-run      (code check: exploration data only)"""

import sys, os, json, warnings
import numpy as np, pandas as pd

warnings.filterwarnings("ignore")
flags = {a for a in sys.argv[1:] if a.startswith("--")}
pos = [a for a in sys.argv[1:] if not a.startswith("--")]
if len(pos) < 2:
    sys.exit(__doc__)
DRY = "--dry-run" in flags
if not DRY and "--confirm" not in flags:
    sys.exit("Needs --confirm (after committing docs/protocol_simple_rule.md) or --dry-run.")
sys.argv = [sys.argv[0]] + pos
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "week2"))
import sequences_clustering as S
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

COLS = ["x0", "w0", "x1", "w1", "net_x", "path_len", "directness", "n_pass", "long_share", "width_std", "dur"]
CUT = 45
K = {"costruzione": 5, "avanzata": 3}
B = 1000
df, nm = S.extract()
k0 = int(round(nm * 0.7))
if DRY:
    k1 = int(round(k0 * 0.7))
    tr = df[df.gi < k1].copy()
    te = df[(df.gi >= k1) & (df.gi < k0)].copy()
else:
    tr = df[df.gi < k0].copy()
    te = df[df.gi >= k0].copy()
for d in (tr, te):
    d["w0"] = (d.y0 - 40).abs()
    d["w1"] = (d.y1 - 40).abs()
mask = lambda d, f: (d.x0 < CUT) if f == "costruzione" else (d.x0 >= CUT)


def nll(cells_a, cells_b, ya, yb):
    Fa = pd.get_dummies(cells_a, dtype=float)
    Fb = pd.get_dummies(cells_b, dtype=float).reindex(columns=Fa.columns, fill_value=0.0)
    p = np.clip(
        LogisticRegression(max_iter=2000, C=0.5).fit(Fa.values, ya).predict_proba(Fb.values)[:, 1], 1e-6, 1 - 1e-6
    )
    return -np.log(np.where(yb == 1, p, 1 - p))


def bins(a, b, col, k):
    edges = np.unique(np.quantile(a[col].values, np.linspace(0, 1, k + 1)[1:-1]))
    return np.digitize(a[col].values, edges), np.digitize(b[col].values, edges)


rng = np.random.default_rng(2028)
out = {
    "team": S.TEAM,
    "modo": "DRY-RUN (solo esplorazione)" if DRY else "PARTITE RISERVATE",
    "partite_test": int(te.gi.nunique()),
}
for fase, k in K.items():
    a = tr[mask(tr, fase)].reset_index(drop=True)
    b = te[mask(te, fase)].reset_index(drop=True)
    ya = a.shot.astype(int).values
    yb = b.shot.astype(int).values
    sc = StandardScaler().fit(a[COLS].values)
    km = KMeans(k, n_init=20, random_state=0).fit(sc.transform(a[COLS].values))
    fa = km.labels_
    fb = km.predict(sc.transform(b[COLS].values))
    p0 = float(np.clip(ya.mean(), 1e-6, 1 - 1e-6))
    l0 = -np.log(np.where(yb == 1, p0, 1 - p0))
    lf = nll(fa, fb, ya, yb)
    res = {"n_test": int(len(b)), "tiro_test": float(yb.mean()), "guadagno_famiglie": float((l0 - lf).mean())}
    g = b.gi.values
    games = np.unique(g)
    by = {x: np.where(g == x)[0] for x in games}
    for nmr, col in [("x1", "x1"), ("net_x", "net_x"), ("n_pass", "n_pass")]:
        ra, rb = bins(a, b, col, k)
        lr = nll(ra, rb, ya, yb)
        d = lr - lf
        res[f"guadagno_{nmr}"] = float((l0 - lr).mean())
        res[f"celle_{nmr}"] = int(len(np.unique(ra)))
        res[f"diff_{nmr}"] = float(d.mean())
        if nmr == "x1":
            ci = np.percentile(
                [np.mean(np.concatenate([d[by[x]] for x in rng.choice(games, len(games))])) for _ in range(B)],
                [2.5, 97.5],
            )
            res["diff_x1_ci95"] = [float(ci[0]), float(ci[1])]
            res["verdetto"] = (
                "famiglie meglio" if ci[0] > 0 else ("regola semplice meglio" if ci[1] < 0 else "nessuna differenza")
            )
    out[fase] = res
    print(
        f"[{S.TEAM} {fase}] guadagno sui tiri: famiglie {res['guadagno_famiglie']:+.4f} | x1 in {res['celle_x1']} fasce {res['guadagno_x1']:+.4f} | net_x {res['guadagno_net_x']:+.4f} | n_pass {res['guadagno_n_pass']:+.4f} || differenza (x1 - famiglie) {res['diff_x1']:+.4f} IC95 [{res['diff_x1_ci95'][0]:+.4f}, {res['diff_x1_ci95'][1]:+.4f}] -> {res['verdetto']}"
    )
fn = f"{S.BASE}/{'dryrun_' if DRY else ''}simplerule_{S.TEAM.replace(' ', '_')}.json"
json.dump(out, open(fn, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("salvato", fn)
