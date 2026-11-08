"""The real test on the reserved matches (the last 30%): H1, H2 and H3.

The families are fitted on the first 70% of the matches and then frozen.
H2: do the family shares stay about the same on the new matches?
H1: can the family be predicted from how the sequence starts, the minute, the half and the previous family, better than by chance?
H3: does the family say something about the shot?
It runs only once, with --confirm, after the protocol is committed (docs/protocol_replication.md). Writes holdout_<Team>.json.

Usage: python validate_replication.py <matches.json> "<Team>" [data_folder=.] --confirm [--no-h3]
       python validate_replication.py <matches.json> "<Team>" [data_folder=.] --dry-run   (only exploration matches, to test the code)
--no-h3: only H1 and H2, as for the first two teams (Leverkusen, Leicester)."""

import sys, os, json, warnings
import numpy as np, pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, adjusted_rand_score
from sklearn.linear_model import LogisticRegression

warnings.filterwarnings("ignore")
flags = [a for a in sys.argv[1:] if a.startswith("--")]
args = [a for a in sys.argv[1:] if not a.startswith("--")]
if len(args) < 2:
    sys.exit(__doc__)
dry = "--dry-run" in flags
with_h3 = "--no-h3" not in flags
protocol = "docs/protocol_replication.md" if with_h3 else "docs/protocol_holdout.md"
if not dry and "--confirm" not in flags:
    sys.exit(f"Refusing to open the reserved matches without --confirm. First commit {protocol}, then rerun with --confirm.")

sys.argv = [sys.argv[0]] + args  # sequences_clustering reads match list, team and folder from here
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sequences_clustering as S

COLS = S.COLS


def logloss_shot(p, y):
    return -np.log(np.where(y == 1, p, 1 - p))


def logistic(X, y):
    return LogisticRegression(max_iter=2000, C=0.5).fit(X, y)


def verdict(ok):
    return "PASS" if ok else "NON confermato"


# fit the families on the first matches, freeze them, use them on the reserved ones
df, n_matches = S.extract()
train, test = S.split(df, n_matches, dry)
models = S.fit_families(train)
train = S.assign(train, models)
test = S.assign(test, models)

out = {
    "team": S.TEAM,
    "modo": "DRY-RUN (solo esplorazione)" if dry else "VALIDAZIONE RISERVATE",
    "partite_train": int(train.gi.nunique()),
    "partite_test": int(test.gi.nunique()),
    "n_seq_train": int(len(train)),
    "n_seq_test": int(len(test)),
}
rng = np.random.default_rng(2026)
for phase, k in S.K.items():
    a = S.phase_rows(train, phase)
    b = S.phase_rows(test, phase)
    scaler = models[phase][0]
    g = b.gi.values
    r = out[phase] = {"n_train": int(len(a)), "n_test": int(len(b))}

    # H2: the family shares do not move more than 10 points, and the frozen families still separate the data (silhouette >= 0.10)
    fam = sorted(a.cl.unique())
    share_a = a.cl.value_counts(normalize=True).reindex(fam).fillna(0)
    share_b = b.cl.value_counts(normalize=True).reindex(fam).fillna(0)
    r["quote_train"] = share_a.round(3).to_dict()
    r["quote_test"] = share_b.round(3).to_dict()
    r["max_scarto_quote"] = float((share_a - share_b).abs().max())
    sil = float(silhouette_score(scaler.transform(b[COLS].values), b.cl.values)) if b.cl.nunique() > 1 else None
    r["silhouette_congelata_test"] = sil
    refit = KMeans(k, n_init=20, random_state=0).fit_predict(StandardScaler().fit_transform(b[COLS].values))
    r["ari_riadattamento_descrittivo"] = float(adjusted_rand_score(b.cl.values, refit))  # descriptive only
    r["H2_pass"] = bool(r["max_scarto_quote"] <= 0.10 and sil is not None and sil >= 0.10)

    # H1: the model (play pattern, minute, half, previous family) against the family shares alone, by log-loss
    Xa = S.context(a)
    classes = list(np.unique(a.cl.values))
    clf = logistic(Xa.values, a.cl.values)
    p = np.full((len(b), len(classes)), 1e-6)  # tiny value for a family the model never saw
    p[:, [classes.index(c) for c in clf.classes_]] = clf.predict_proba(S.context(b, Xa.columns).values)
    p /= p.sum(1, keepdims=True)
    base = pd.Series(a.cl.values).value_counts(normalize=True).reindex(classes).fillna(1e-6).values
    base = base / base.sum()
    truth = np.array([classes.index(c) for c in b.cl.values])
    loss_model = -np.log(p[np.arange(len(b)), truth])
    loss_base = -np.log(base[truth])
    gain = loss_base - loss_model
    ci = S.boot_ci(gain, g, rng)
    r["logloss_modello"] = float(loss_model.mean())
    r["logloss_baseline"] = float(loss_base.mean())
    r["guadagno"] = float(gain.mean())
    r["guadagno_ci95"] = [float(ci[0]), float(ci[1])]
    r["accuratezza_modello"] = float((p.argmax(1) == truth).mean())
    r["accuratezza_baseline"] = float((base.argmax() == truth).mean())
    r["H1_pass"] = bool(ci[0] > 0)
    print(
        f"[{phase}] test: {len(b)} seq, {len(np.unique(g))} partite"
        f" | H1 guadagno {gain.mean():+.3f} IC95 [{ci[0]:+.3f}, {ci[1]:+.3f}] -> {verdict(ci[0] > 0)}"
        f" | H2 scarto quote max {r['max_scarto_quote']:.2f}, silhouette {sil:.2f} -> {verdict(r['H2_pass'])}"
    )
    if not with_h3:
        continue

    # H3: does knowing the family predict a shot better than the overall shot rate?
    ya = a.shot.astype(int).values
    yb = b.shot.astype(int).values
    p0 = float(np.clip(ya.mean(), 1e-6, 1 - 1e-6))
    Fa = pd.get_dummies(a.cl, dtype=float)
    Fb = pd.get_dummies(b.cl, dtype=float).reindex(columns=Fa.columns, fill_value=0.0)
    p_fam = np.clip(logistic(Fa.values, ya).predict_proba(Fb.values)[:, 1], 1e-6, 1 - 1e-6)
    gain_fam = logloss_shot(p0, yb) - logloss_shot(p_fam, yb)
    # descriptive: the same with the 11 raw features instead of the families
    raw = logistic(scaler.transform(a[COLS].values), ya)
    p_raw = np.clip(raw.predict_proba(scaler.transform(b[COLS].values))[:, 1], 1e-6, 1 - 1e-6)
    gain_raw = logloss_shot(p0, yb) - logloss_shot(p_raw, yb)
    ci3 = S.boot_ci(gain_fam, g, np.random.default_rng(2027))
    r["tiro_train"] = a.groupby("cl").shot.mean().round(3).to_dict()
    r["tiro_test"] = b.groupby("cl").shot.mean().round(3).to_dict()
    r["H3_guadagno"] = float(gain_fam.mean())
    r["H3_ci95"] = [float(ci3[0]), float(ci3[1])]
    r["H3_pass"] = bool(ci3[0] > 0)
    r["guadagno_modello_feature_descrittivo"] = float(gain_raw.mean())
    print(f"[{phase}] H3 tiro: guadagno famiglie {gain_fam.mean():+.4f} IC95 [{ci3[0]:+.4f}, {ci3[1]:+.4f}] -> {verdict(ci3[0] > 0)}")

fn = f"{S.BASE}/{'dryrun' if dry else 'holdout'}_{S.TEAM.replace(' ', '_')}.json"
json.dump(out, open(fn, "w"), indent=1, default=float)
print("salvato", fn)
