"""ESPLORATIVO (non pre-registrato). Prevedibilita' fuori campione su TUTTE le partite con validazione incrociata per partite (6 gruppi),
rifittando il clustering dentro ogni fold (nessuna fuga di informazione). Serve a stimare il guadagno con piu' dati (34-38 partite invece di 10-11).
Uso: python exploratory_cv_all_matches.py <matches.json> "<Squadra>" [cartella_dati=.]
Impostazioni identiche al protocollo (x=45, k=5/3, logistica C=0.5, stessi input). Attenzione: GroupKFold non rispetta l'ordine temporale."""

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


def feats(d, cols=None):
    X = pd.concat(
        [
            pd.get_dummies(d.play_pattern, dtype=float),
            d[["minuto"]].astype(float) / 90,
            (d.tempo == 2).astype(float).rename("t2"),
            pd.get_dummies(d.prev_cl, prefix="prev", dtype=float),
        ],
        axis=1,
    )
    return X if cols is None else X.reindex(columns=cols, fill_value=0.0)


res = {f: {"gi": [], "d": []} for f in K}
for tr, te in GroupKFold(6).split(df, groups=df.gi):
    m = fit(df.iloc[tr])
    a_all = assign(df.iloc[tr], m)
    b_all = assign(df.iloc[te], m)
    for f in K:
        a = a_all[mask(a_all, f)].reset_index(drop=True)
        b = b_all[mask(b_all, f)].reset_index(drop=True)
        Xa = feats(a)
        Xt = feats(b, Xa.columns)
        ya = a.cl.values
        yb = b.cl.values
        cl = np.unique(ya)
        clf = LogisticRegression(max_iter=2000, C=0.5).fit(Xa.values, ya)
        p = np.full((len(b), len(cl)), 1e-6)
        p[:, [list(cl).index(c) for c in clf.classes_]] = clf.predict_proba(Xt.values)
        p /= p.sum(1, keepdims=True)
        pr = pd.Series(ya).value_counts(normalize=True).reindex(cl).fillna(1e-6).values
        pr = pr / pr.sum()
        yi = np.array([list(cl).index(c) for c in yb])
        res[f]["d"] += list(-np.log(pr[yi]) + np.log(p[np.arange(len(b)), yi]))
        res[f]["gi"] += list(b.gi.values)
rng = np.random.default_rng(99)
out = {"team": S.TEAM, "n_partite": int(nm), "nota": "ESPLORATIVO, non pre-registrato"}
for f in K:
    d = np.array(res[f]["d"])
    g = np.array(res[f]["gi"])
    games = np.unique(g)
    ci = np.percentile(
        [np.mean(np.concatenate([d[g == x] for x in rng.choice(games, len(games))])) for _ in range(1000)], [2.5, 97.5]
    )
    pm = np.array([d[g == x].mean() for x in games])
    out[f] = dict(
        n=int(len(d)),
        guadagno=float(d.mean()),
        ci95=[float(ci[0]), float(ci[1])],
        quota_partite_positive=float((pm > 0).mean()),
        mediana_per_partita=float(np.median(pm)),
    )
    k0 = int(round(nm * 0.7))
    early = d[g < k0]
    late = d[g >= k0]
    out[f].update(guadagno_prime70=float(early.mean()), guadagno_ultime30=float(late.mean()))
    print(f"[{S.TEAM} {f}] (CV) prime 70% partite {early.mean():+.3f} | ultime 30% {late.mean():+.3f}")
    print(
        f"[{S.TEAM} {f}] n={len(d)} guadagno CV {d.mean():+.3f} IC95 [{ci[0]:+.3f}, {ci[1]:+.3f}] | partite con guadagno > 0: {(pm > 0).mean():.0%} | mediana per partita {np.median(pm):+.3f}"
    )
json.dump(out, open(f"{S.BASE}/exploratory_cv_{S.TEAM.replace(' ', '_')}.json", "w"), indent=1)
