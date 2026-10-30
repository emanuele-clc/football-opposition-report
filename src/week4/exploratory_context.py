"""EXPLORATORY (not pre-registered). Does match context add information on the family, FOR THE SAME PLAY PATTERN?
Baseline = model with play pattern only. Added: previous family, minute+half, score state (behind/level/ahead at the start of the minute), home/away.
CV by match on all matches (clustering refitted in each fold). Gain = log-loss(baseline) - log-loss(extended model); positive = context helps.
Usage: python exploratory_context.py <matches.json> "<Team>" [data_folder=.]"""

import sys, os, json, warnings
import numpy as np, pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "week2"))
import sequences_clustering as S
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold

COLS = ["x0", "w0", "x1", "w1", "net_x", "path_len", "directness", "n_pass", "long_share", "width_std", "dur"]
CUT = 45
K = {"costruzione": 5, "avanzata": 3}
df, nm = S.extract()
df["w0"] = (df.y0 - 40).abs()
df["w1"] = (df.y1 - 40).abs()
# context: score at the start of the minute and home/away
ms = {g["match_id"]: g for g in json.load(open(S.MF))}
diff = {}
home = {}
for mid in df.match.unique():
    g = ms[mid]
    home[mid] = int(g["home_team"]["home_team_name"] == S.TEAM)
    gf, ga = [], []
    for e in json.load(open(f"{S.BASE}/ev/{mid}.json")):
        t = e["type"]["name"]
        key = (e["period"], e["minute"])
        if t == "Shot" and e["shot"]["outcome"]["name"] == "Goal":
            (gf if e["team"]["name"] == S.TEAM else ga).append(key)
        elif t == "Own Goal For":
            (gf if e["team"]["name"] == S.TEAM else ga).append(key)
    diff[mid] = (gf, ga)


def dif(r):
    gf, ga = diff[r.match]
    k = (r.tempo, r.minuto)
    return sum(x < k for x in gf) - sum(x < k for x in ga)


df["diff"] = df.apply(dif, axis=1)
df["stato"] = np.where(df["diff"] < 0, "sotto", np.where(df["diff"] > 0, "sopra", "pari"))
df["casa"] = df.match.map(home)
mask = lambda d, f: (d.x0 < CUT) if f == "costruzione" else (d.x0 >= CUT)


def fit(tr):
    m = {}
    for f, k in K.items():
        sub = tr[mask(tr, f)]
        sc = StandardScaler().fit(sub[COLS].values)
        km = KMeans(k, n_init=20, random_state=0).fit(sc.transform(sub[COLS].values))
        o = sorted(range(k), key=lambda c: (sub.x0.values[km.labels_ == c].mean(), -(km.labels_ == c).sum()))
        m[f] = (sc, km, {c: i + 1 for i, c in enumerate(o)})
    return m


def assign(d, m):
    d = d.copy()
    d["cl"] = ""
    for f, (sc, km, rank) in m.items():
        mk = mask(d, f)
        if mk.sum():
            d.loc[mk, "cl"] = [
                f"{'C' if f == 'costruzione' else 'A'}{rank[l]}"
                for l in km.predict(sc.transform(d.loc[mk, COLS].values))
            ]
    d = d.sort_values(["gi", "pid"]).reset_index(drop=True)
    d["prev_cl"] = d.groupby("gi").cl.shift(1).fillna("start")
    return d


def blocks(d):
    return {
        "pp": pd.get_dummies(d.play_pattern, prefix="pp", dtype=float),
        "prev": pd.get_dummies(d.prev_cl, prefix="prev", dtype=float),
        "mt": pd.concat([d[["minuto"]].astype(float) / 90, (d.tempo == 2).astype(float).rename("t2")], axis=1),
        "st": pd.get_dummies(d.stato, prefix="st", dtype=float),
        "ha": d[["casa"]].astype(float),
    }


SETS = {
    "+ famiglia precedente": ["pp", "prev"],
    "+ minuto e tempo": ["pp", "mt"],
    "+ stato punteggio": ["pp", "st"],
    "+ casa/trasferta": ["pp", "ha"],
    "+ tutto il contesto": ["pp", "prev", "mt", "st", "ha"],
}


def nll(bl, ba, bb, ya, cl, yi, nb):
    Xa = pd.concat([ba[x] for x in bl], axis=1)
    Xt = pd.concat([bb[x] for x in bl], axis=1).reindex(columns=Xa.columns, fill_value=0.0)
    clf = LogisticRegression(max_iter=2000, C=0.5).fit(Xa.values, ya)
    p = np.full((nb, len(cl)), 1e-6)
    p[:, [list(cl).index(c) for c in clf.classes_]] = clf.predict_proba(Xt.values)
    p /= p.sum(1, keepdims=True)
    return -np.log(p[np.arange(nb), yi])


res = {f: {n: {"gi": [], "d": []} for n in SETS} for f in K}
for tr, te in GroupKFold(6).split(df, groups=df.gi):
    m = fit(df.iloc[tr])
    A = assign(df.iloc[tr], m)
    Bm = assign(df.iloc[te], m)
    for f in K:
        a = A[mask(A, f)].reset_index(drop=True)
        b = Bm[mask(Bm, f)].reset_index(drop=True)
        ya = a.cl.values
        cl = np.unique(ya)
        ba = blocks(a)
        bb = blocks(b)
        yi = np.array([list(cl).index(c) for c in b.cl.values])
        l0 = nll(["pp"], ba, bb, ya, cl, yi, len(b))
        for n, bl in SETS.items():
            res[f][n]["d"] += list(l0 - nll(bl, ba, bb, ya, cl, yi, len(b)))
            res[f][n]["gi"] += list(b.gi.values)
rng = np.random.default_rng(5)
out = {"team": S.TEAM, "nota": "ESPLORATIVO, non pre-registrato", "baseline": "solo play pattern"}
for f in K:
    out[f] = {}
    for n in SETS:
        d = np.array(res[f][n]["d"])
        g = np.array(res[f][n]["gi"])
        games = np.unique(g)
        ci = np.percentile(
            [np.mean(np.concatenate([d[g == x] for x in rng.choice(games, len(games))])) for _ in range(500)],
            [2.5, 97.5],
        )
        out[f][n] = dict(guadagno=float(d.mean()), ci95=[float(ci[0]), float(ci[1])])
        print(f"[{S.TEAM} {f}] {n:24s} {d.mean():+.4f} [{ci[0]:+.4f}, {ci[1]:+.4f}]")
json.dump(out, open(f"{S.BASE}/exploratory_context_{S.TEAM.replace(' ', '_')}.json", "w"), indent=1)
