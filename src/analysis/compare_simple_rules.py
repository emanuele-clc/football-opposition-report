"""Do the families predict shots better than a very simple rule?

The simple rule just splits the sequences by where they end (x1) into the same number of groups.
Both get the same logistic model, and I compare them on the reserved matches. Protocol: docs/protocol_simple_rule.md.

Usage: python compare_simple_rules.py <matches.json> "<Team>" [data_folder=.] --confirm   (reserved matches, once only)
       python compare_simple_rules.py <matches.json> "<Team>" [data_folder=.] --dry-run   (exploration matches only)"""

import sys, os, json, warnings
import numpy as np, pandas as pd

warnings.filterwarnings("ignore")
flags = [a for a in sys.argv[1:] if a.startswith("--")]
args = [a for a in sys.argv[1:] if not a.startswith("--")]
if len(args) < 2:
    sys.exit(__doc__)
dry = "--dry-run" in flags
if not dry and "--confirm" not in flags:
    sys.exit("Needs --confirm (after committing docs/protocol_simple_rule.md) or --dry-run.")
sys.argv = [sys.argv[0]] + args
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sequences_clustering as S
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

COLS = S.COLS
df, n_matches = S.extract()
train, test = S.split(df, n_matches, dry)


def loss_per_sequence(cells_a, cells_b, ya, yb):
    # logistic model on the cells (one dummy per cell), log loss of each test sequence
    Fa = pd.get_dummies(cells_a, dtype=float)
    Fb = pd.get_dummies(cells_b, dtype=float).reindex(columns=Fa.columns, fill_value=0.0)
    model = LogisticRegression(max_iter=2000, C=0.5).fit(Fa.values, ya)
    p = np.clip(model.predict_proba(Fb.values)[:, 1], 1e-6, 1 - 1e-6)
    return -np.log(np.where(yb == 1, p, 1 - p))


def bins(a, b, col, k):
    # k equal-frequency bins, edges taken from the training data
    edges = np.unique(np.quantile(a[col].values, np.linspace(0, 1, k + 1)[1:-1]))
    return np.digitize(a[col].values, edges), np.digitize(b[col].values, edges)


rng = np.random.default_rng(2028)
out = {
    "team": S.TEAM,
    "modo": "DRY-RUN (solo esplorazione)" if dry else "PARTITE RISERVATE",
    "partite_test": int(test.gi.nunique()),
}
for phase, k in S.K.items():
    a = S.phase_rows(train, phase)
    b = S.phase_rows(test, phase)
    ya = a.shot.astype(int).values
    yb = b.shot.astype(int).values

    scaler = StandardScaler().fit(a[COLS].values)
    km = KMeans(k, n_init=20, random_state=0).fit(scaler.transform(a[COLS].values))
    fam_a = km.labels_
    fam_b = km.predict(scaler.transform(b[COLS].values))

    p0 = float(np.clip(ya.mean(), 1e-6, 1 - 1e-6))
    loss_0 = -np.log(np.where(yb == 1, p0, 1 - p0))  # same shot rate for everyone
    loss_fam = loss_per_sequence(fam_a, fam_b, ya, yb)
    res = {"n_test": int(len(b)), "tiro_test": float(yb.mean()), "guadagno_famiglie": float((loss_0 - loss_fam).mean())}

    for col in ("x1", "net_x", "n_pass"):
        cells_a, cells_b = bins(a, b, col, k)
        loss_rule = loss_per_sequence(cells_a, cells_b, ya, yb)
        d = loss_rule - loss_fam  # > 0: the families are better
        res[f"guadagno_{col}"] = float((loss_0 - loss_rule).mean())
        res[f"celle_{col}"] = int(len(np.unique(cells_a)))
        res[f"diff_{col}"] = float(d.mean())
        if col != "x1":
            continue
        ci = S.boot_ci(d, b.gi.values, rng)  # 95% interval resampling matches, only for the main comparison
        res["diff_x1_ci95"] = [float(ci[0]), float(ci[1])]
        if ci[0] > 0:
            res["verdetto"] = "famiglie meglio"
        elif ci[1] < 0:
            res["verdetto"] = "regola semplice meglio"
        else:
            res["verdetto"] = "nessuna differenza"
    out[phase] = res
    print(f"[{S.TEAM} {phase}] famiglie {res['guadagno_famiglie']:+.4f} | x1 {res['guadagno_x1']:+.4f} | x1 - famiglie {res['diff_x1']:+.4f} -> {res['verdetto']}")

fn = f"{S.BASE}/{'dryrun_' if dry else ''}simplerule_{S.TEAM.replace(' ', '_')}.json"
json.dump(out, open(fn, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("salvato", fn)
