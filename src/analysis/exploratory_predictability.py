"""EXPLORATORY (not pre-registered). How predictable is the family of the next sequence, using all matches?
Three analyses, all with cross-validation by match (6 groups) and the families refitted inside each fold (no leak):
  cv        gain of the protocol model (play pattern, minute, half, previous family) over the family shares -> exploratory_cv_<Team>.json
  ablation  the same model with some inputs removed: where does the gain come from?                      -> exploratory_ablation_<Team>.json
  context   for the same play pattern, does context help (previous family, minute, score, home/away)?    -> exploratory_context_<Team>.json
Usage: python exploratory_predictability.py cv|ablation|context <matches.json> "<Team>" [data_folder=.]
Settings as in the protocol (x = 45, k = 5/3, logistic C = 0.5). Note: GroupKFold does not keep the time order.
(Until 6 Nov 2026 these were three files: exploratory_cv_all_matches.py, exploratory_ablation.py, exploratory_context.py.)"""

import sys, os, json, warnings
import numpy as np, pandas as pd

warnings.filterwarnings("ignore")
if len(sys.argv) < 4 or sys.argv[1] not in ("cv", "ablation", "context"):
    sys.exit(__doc__)
WHAT = sys.argv[1]
sys.argv = [sys.argv[0]] + sys.argv[2:]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sequences_clustering as S
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold

COLS = ["x0", "w0", "x1", "w1", "net_x", "path_len", "directness", "n_pass", "long_share", "width_std", "dur"]
CUT = 45
K = {"costruzione": 5, "avanzata": 3}
FN = S.TEAM.replace(" ", "_")

df, n_matches = S.extract()
df["w0"] = (df.y0 - 40).abs()
df["w1"] = (df.y1 - 40).abs()


def in_phase(d, phase):
    if phase == "costruzione":
        return d.x0 < CUT
    return d.x0 >= CUT


def fit(train):
    # families of each phase, numbered by mean start x
    models = {}
    for phase, k in K.items():
        sub = train[in_phase(train, phase)]
        scaler = StandardScaler().fit(sub[COLS].values)
        km = KMeans(k, n_init=20, random_state=0).fit(scaler.transform(sub[COLS].values))
        lab = km.labels_
        order = sorted(range(k), key=lambda c: (sub.x0.values[lab == c].mean(), -(lab == c).sum()))
        rank = {}
        for i, c in enumerate(order):
            rank[c] = i + 1
        models[phase] = (scaler, km, rank)
    return models


def assign(d, models):
    d = d.copy()
    d["cl"] = ""
    for phase, (scaler, km, rank) in models.items():
        m = in_phase(d, phase)
        if m.sum():
            letter = "C" if phase == "costruzione" else "A"
            d.loc[m, "cl"] = [f"{letter}{rank[l]}" for l in km.predict(scaler.transform(d.loc[m, COLS].values))]
    d = d.sort_values(["gi", "pid"]).reset_index(drop=True)
    d["prev_cl"] = d.groupby("gi").cl.shift(1).fillna("start")
    return d


def blocks(d):
    # groups of model inputs
    return {
        "pp": pd.get_dummies(d.play_pattern, prefix="pp", dtype=float),
        "mt": pd.concat([d[["minuto"]].astype(float) / 90, (d.tempo == 2).astype(float).rename("t2")], axis=1),
        "prev": pd.get_dummies(d.prev_cl, prefix="prev", dtype=float),
        "st": pd.get_dummies(d.stato, prefix="st", dtype=float) if "stato" in d else None,
        "ha": d[["casa"]].astype(float) if "casa" in d else None,
    }


def protocol_inputs(d, cols=None):
    # the inputs of the protocol model, in the same column order as validate_replication.py
    X = pd.concat(
        [
            pd.get_dummies(d.play_pattern, dtype=float),
            d[["minuto"]].astype(float) / 90,
            (d.tempo == 2).astype(float).rename("t2"),
            pd.get_dummies(d.prev_cl, prefix="prev", dtype=float),
        ],
        axis=1,
    )
    if cols is None:
        return X
    return X.reindex(columns=cols, fill_value=0.0)


def proba(Xa, Xb, ya, classes, nb):
    # probability of each family for the test sequences (1e-6 for a family the model never saw)
    clf = LogisticRegression(max_iter=2000, C=0.5).fit(Xa.values, ya)
    p = np.full((nb, len(classes)), 1e-6)
    p[:, [list(classes).index(c) for c in clf.classes_]] = clf.predict_proba(Xb.values)
    p /= p.sum(1, keepdims=True)
    return p


def loss(names, ba, bb, ya, classes, yi, nb):
    Xa = pd.concat([ba[x] for x in names], axis=1)
    Xb = pd.concat([bb[x] for x in names], axis=1).reindex(columns=Xa.columns, fill_value=0.0)
    p = proba(Xa, Xb, ya, classes, nb)
    return -np.log(p[np.arange(nb), yi])


def boot_ci(d, g, rng, B):
    games = np.unique(g)
    means = []
    for _ in range(B):
        pick = rng.choice(games, len(games))
        means.append(np.mean(np.concatenate([d[g == x] for x in pick])))
    return np.percentile(means, [2.5, 97.5])


if WHAT == "context":
    # score at the start of the minute (behind / level / ahead) and home/away
    games = {g["match_id"]: g for g in json.load(open(S.MF))}
    goals = {}
    home = {}
    for mid in df.match.unique():
        home[mid] = int(games[mid]["home_team"]["home_team_name"] == S.TEAM)
        scored, conceded = [], []
        for e in json.load(open(f"{S.BASE}/ev/{mid}.json")):
            t = e["type"]["name"]
            goal = (t == "Shot" and e["shot"]["outcome"]["name"] == "Goal") or t == "Own Goal For"
            if goal:
                when = (e["period"], e["minute"])
                if e["team"]["name"] == S.TEAM:
                    scored.append(when)
                else:
                    conceded.append(when)
        goals[mid] = (scored, conceded)

    def score_diff(r):
        scored, conceded = goals[r.match]
        now = (r.tempo, r.minuto)
        return sum(x < now for x in scored) - sum(x < now for x in conceded)

    df["diff"] = df.apply(score_diff, axis=1)
    df["stato"] = np.where(df["diff"] < 0, "sotto", np.where(df["diff"] > 0, "sopra", "pari"))
    df["casa"] = df.match.map(home)

# the input sets of each analysis
if WHAT == "cv":
    SETS = {"cv": None}
elif WHAT == "ablation":
    SETS = {
        "completo": ["pp", "mt", "prev"],
        "solo play pattern": ["pp"],
        "solo minuto+tempo": ["mt"],
        "solo famiglia precedente": ["prev"],
        "senza play pattern": ["mt", "prev"],
        "senza famiglia precedente": ["pp", "mt"],
    }
else:
    SETS = {
        "+ famiglia precedente": ["pp", "prev"],
        "+ minuto e tempo": ["pp", "mt"],
        "+ stato punteggio": ["pp", "st"],
        "+ casa/trasferta": ["pp", "ha"],
        "+ tutto il contesto": ["pp", "prev", "mt", "st", "ha"],
    }

# cross-validation: d = gain of each test sequence, gi = its match
res = {}
for phase in K:
    res[phase] = {}
    for name in SETS:
        res[phase][name] = {"gi": [], "d": []}
for tr, te in GroupKFold(6).split(df, groups=df.gi):
    models = fit(df.iloc[tr])
    A = assign(df.iloc[tr], models)
    Bm = assign(df.iloc[te], models)
    for phase in K:
        a = A[in_phase(A, phase)].reset_index(drop=True)
        b = Bm[in_phase(Bm, phase)].reset_index(drop=True)
        ya = a.cl.values
        classes = np.unique(ya)
        yi = np.array([list(classes).index(c) for c in b.cl.values])
        # baseline: the family shares of the training matches
        base = pd.Series(ya).value_counts(normalize=True).reindex(classes).fillna(1e-6).values
        base = base / base.sum()
        if WHAT == "cv":
            Xa = protocol_inputs(a)
            p = proba(Xa, protocol_inputs(b, Xa.columns), ya, classes, len(b))
            gains = {"cv": -np.log(base[yi]) + np.log(p[np.arange(len(b)), yi])}
        else:
            ba = blocks(a)
            bb = blocks(b)
            gains = {}
            if WHAT == "ablation":
                for name, names in SETS.items():
                    gains[name] = -np.log(base[yi]) - loss(names, ba, bb, ya, classes, yi, len(b))
            else:  # context: the baseline is the model with play pattern only
                l0 = loss(["pp"], ba, bb, ya, classes, yi, len(b))
                for name, names in SETS.items():
                    gains[name] = l0 - loss(names, ba, bb, ya, classes, yi, len(b))
        for name in SETS:
            res[phase][name]["d"] += list(gains[name])
            res[phase][name]["gi"] += list(b.gi.values)

# summary with a 95% interval resampling matches
if WHAT == "cv":
    rng = np.random.default_rng(99)
    out = {"team": S.TEAM, "n_partite": int(n_matches), "nota": "ESPLORATIVO, non pre-registrato"}
    for phase in K:
        d = np.array(res[phase]["cv"]["d"])
        g = np.array(res[phase]["cv"]["gi"])
        ci = boot_ci(d, g, rng, 1000)
        per_match = np.array([d[g == x].mean() for x in np.unique(g)])
        k0 = int(round(n_matches * 0.7))
        early = d[g < k0]
        late = d[g >= k0]
        out[phase] = {
            "n": int(len(d)),
            "guadagno": float(d.mean()),
            "ci95": [float(ci[0]), float(ci[1])],
            "quota_partite_positive": float((per_match > 0).mean()),
            "mediana_per_partita": float(np.median(per_match)),
            "guadagno_prime70": float(early.mean()),
            "guadagno_ultime30": float(late.mean()),
        }
        print(f"[{S.TEAM} {phase}] (CV) prime 70% partite {early.mean():+.3f} | ultime 30% {late.mean():+.3f}")
        print(
            f"[{S.TEAM} {phase}] n={len(d)} guadagno CV {d.mean():+.3f} IC95 [{ci[0]:+.3f}, {ci[1]:+.3f}] | partite con guadagno > 0: {(per_match > 0).mean():.0%} | mediana per partita {np.median(per_match):+.3f}"
        )
    json.dump(out, open(f"{S.BASE}/exploratory_cv_{FN}.json", "w"), indent=1)
else:
    if WHAT == "ablation":
        rng = np.random.default_rng(7)
        out = {"team": S.TEAM, "nota": "ESPLORATIVO, non pre-registrato"}
    else:
        rng = np.random.default_rng(5)
        out = {"team": S.TEAM, "nota": "ESPLORATIVO, non pre-registrato", "baseline": "solo play pattern"}
    for phase in K:
        out[phase] = {}
        for name in SETS:
            d = np.array(res[phase][name]["d"])
            g = np.array(res[phase][name]["gi"])
            ci = boot_ci(d, g, rng, 500)
            out[phase][name] = {"guadagno": float(d.mean()), "ci95": [float(ci[0]), float(ci[1])]}
            print(f"[{S.TEAM} {phase}] {name:28s} {d.mean():+.4f} [{ci[0]:+.4f}, {ci[1]:+.4f}]")
    json.dump(out, open(f"{S.BASE}/exploratory_{WHAT}_{FN}.json", "w"), indent=1)
