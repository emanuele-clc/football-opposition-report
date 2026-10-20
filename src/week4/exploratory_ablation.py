"""ESPLORATIVO (non pre-registrato). Da dove viene il guadagno di prevedibilita'? Ablazione degli input del modello, CV per partite su tutte le partite
(clustering rifatto in ogni fold). Blocchi: play pattern (come parte la sequenza), minuto+tempo, famiglia della sequenza precedente.
Uso: python exploratory_ablation.py <matches.json> "<Squadra>" [cartella_dati=.]"""

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
        "mt": pd.concat([d[["minuto"]].astype(float) / 90, (d.tempo == 2).astype(float).rename("t2")], axis=1),
        "prev": pd.get_dummies(d.prev_cl, prefix="prev", dtype=float),
    }


SETS = {
    "completo": ["pp", "mt", "prev"],
    "solo play pattern": ["pp"],
    "solo minuto+tempo": ["mt"],
    "solo famiglia precedente": ["prev"],
    "senza play pattern": ["mt", "prev"],
    "senza famiglia precedente": ["pp", "mt"],
}
res = {f: {n: {"gi": [], "d": []} for n in SETS} for f in K}
for tr, te in GroupKFold(6).split(df, groups=df.gi):
    m = fit(df.iloc[tr])
    A = assign(df.iloc[tr], m)
    Bm = assign(df.iloc[te], m)
    for f in K:
        a = A[mask(A, f)].reset_index(drop=True)
        b = Bm[mask(Bm, f)].reset_index(drop=True)
        ya = a.cl.values
        yb = b.cl.values
        cl = np.unique(ya)
        ba = blocks(a)
        bb = blocks(b)
        pr = pd.Series(ya).value_counts(normalize=True).reindex(cl).fillna(1e-6).values
        pr = pr / pr.sum()
        yi = np.array([list(cl).index(c) for c in yb])
        for n, bl in SETS.items():
            Xa = pd.concat([ba[x] for x in bl], axis=1)
            Xt = pd.concat([bb[x] for x in bl], axis=1).reindex(columns=Xa.columns, fill_value=0.0)
            clf = LogisticRegression(max_iter=2000, C=0.5).fit(Xa.values, ya)
            p = np.full((len(b), len(cl)), 1e-6)
            p[:, [list(cl).index(c) for c in clf.classes_]] = clf.predict_proba(Xt.values)
            p /= p.sum(1, keepdims=True)
            res[f][n]["d"] += list(-np.log(pr[yi]) + np.log(p[np.arange(len(b)), yi]))
            res[f][n]["gi"] += list(b.gi.values)
rng = np.random.default_rng(7)
out = {"team": S.TEAM, "nota": "ESPLORATIVO, non pre-registrato"}
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
        print(f"[{S.TEAM} {f}] {n:28s} {d.mean():+.3f} [{ci[0]:+.3f}, {ci[1]:+.3f}]")
json.dump(out, open(f"{S.BASE}/exploratory_ablation_{S.TEAM.replace(' ', '_')}.json", "w"), indent=1)
