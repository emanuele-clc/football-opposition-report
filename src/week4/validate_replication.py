"""Settimana 4 - REPLICA su squadre nuove: validazione sulle partite RISERVATE (ultimo 30%), protocollo in docs/protocol_replication.md.
Come validate_holdout.py (H1, H2 invariate) piu' H3: le famiglie differiscono nella probabilita' di tiro fuori campione.
Uso:   python validate_holdout.py <matches.json> "<Squadra>" [cartella_dati=.] --confirm
       python validate_holdout.py <matches.json> "<Squadra>" [cartella_dati=.] --dry-run   (prova del codice: usa SOLO i dati di esplorazione)
Il modello (scaler, centri K-Means, ordine dei gruppi) viene congelato sulle partite di esplorazione e MAI riaddestrato sulle riservate.
Senza --confirm lo script non apre le partite riservate. Va lanciato UNA volta sola, dopo aver committato il protocollo di replica."""

import sys, os, json, warnings
import numpy as np, pandas as pd

warnings.filterwarnings("ignore")
flags = {a for a in sys.argv[1:] if a.startswith("--")}
pos = [a for a in sys.argv[1:] if not a.startswith("--")]
if len(pos) < 2:
    sys.exit(__doc__)
DRY = "--dry-run" in flags
if not DRY and "--confirm" not in flags:
    sys.exit(
        "Rifiuto di aprire le partite riservate senza --confirm. Prima committa docs/protocol_replication.md, poi rilancia con --confirm."
    )
sys.argv = [sys.argv[0]] + pos
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "week2"))
import sequences_clustering as S
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, adjusted_rand_score
from sklearn.linear_model import LogisticRegression

COLS = ["x0", "w0", "x1", "w1", "net_x", "path_len", "directness", "n_pass", "long_share", "width_std", "dur"]
CUT = 45
K = {"costruzione": 5, "avanzata": 3}
# soglie fissate nel protocollo
SHARE_MAX_DRIFT = 0.10
SIL_MIN = 0.10
ALPHA_CI = (2.5, 97.5)
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
mask = lambda d, fase: (d.x0 < CUT) if fase == "costruzione" else (d.x0 >= CUT)
models = {}
for fase, k in K.items():
    sub = tr[mask(tr, fase)]
    sc = StandardScaler().fit(sub[COLS].values)
    km = KMeans(k, n_init=20, random_state=0).fit(sc.transform(sub[COLS].values))
    order = sorted(range(k), key=lambda c: (sub.x0.values[km.labels_ == c].mean(), -(km.labels_ == c).sum()))
    models[fase] = (sc, km, {c: i + 1 for i, c in enumerate(order)})


def assign(d):
    d["cl"] = ""
    for fase, (sc, km, rank) in models.items():
        m = mask(d, fase)
        if m.sum():
            d.loc[m, "cl"] = [
                f"{'C' if fase == 'costruzione' else 'A'}{rank[l]}"
                for l in km.predict(sc.transform(d.loc[m, COLS].values))
            ]
    d = d.sort_values(["gi", "pid"]).reset_index(drop=True)
    d["prev_cl"] = d.groupby("gi").cl.shift(1).fillna("start")
    return d


tr = assign(tr)
te = assign(te)


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


rng = np.random.default_rng(2026)
out = {
    "team": S.TEAM,
    "modo": "DRY-RUN (solo esplorazione)" if DRY else "VALIDAZIONE RISERVATE",
    "partite_train": int(tr.gi.nunique()),
    "partite_test": int(te.gi.nunique()),
    "n_seq_train": int(len(tr)),
    "n_seq_test": int(len(te)),
}
for fase, k in K.items():
    a = tr[mask(tr, fase)].reset_index(drop=True)
    b = te[mask(te, fase)].reset_index(drop=True)
    sc, km, rank = models[fase]
    r = {"n_train": int(len(a)), "n_test": int(len(b))}
    # H2: riproducibilita' dei gruppi (quote e silhouette dell'assegnazione congelata)
    fam = sorted(a.cl.unique())
    sa = a.cl.value_counts(normalize=True).reindex(fam).fillna(0)
    sb = b.cl.value_counts(normalize=True).reindex(fam).fillna(0)
    r["quote_train"] = sa.round(3).to_dict()
    r["quote_test"] = sb.round(3).to_dict()
    r["max_scarto_quote"] = float((sa - sb).abs().max())
    Xb = sc.transform(b[COLS].values)
    r["silhouette_congelata_test"] = float(silhouette_score(Xb, b.cl.values)) if b.cl.nunique() > 1 else None
    refit = KMeans(k, n_init=20, random_state=0).fit_predict(StandardScaler().fit_transform(b[COLS].values))
    r["ari_riadattamento_descrittivo"] = float(adjusted_rand_score(b.cl.values, refit))
    r["H2_pass"] = bool(
        r["max_scarto_quote"] <= SHARE_MAX_DRIFT
        and r["silhouette_congelata_test"] is not None
        and r["silhouette_congelata_test"] >= SIL_MIN
    )
    # H1: prevedibilita' fuori campione (modello addestrato su esplorazione, valutato su riservate)
    Xa = feats(a)
    Xt = feats(b, Xa.columns)
    ya = a.cl.values
    yb = b.cl.values
    classes = np.unique(ya)
    clf = LogisticRegression(max_iter=2000, C=0.5).fit(Xa.values, ya)
    p = np.full((len(b), len(classes)), 1e-6)
    p[:, [list(classes).index(c) for c in clf.classes_]] = clf.predict_proba(Xt.values)
    p /= p.sum(1, keepdims=True)
    pr = pd.Series(ya).value_counts(normalize=True).reindex(classes).fillna(1e-6).values
    pr = pr / pr.sum()
    yi = np.array([list(classes).index(c) for c in yb])
    lm = -np.log(p[np.arange(len(b)), yi])
    lb = -np.log(pr[yi])
    d = lb - lm
    g = b.gi.values
    games = np.unique(g)
    ci = np.percentile(
        [np.mean(np.concatenate([d[g == x] for x in rng.choice(games, len(games))])) for _ in range(B)], ALPHA_CI
    )
    r.update(
        logloss_modello=float(lm.mean()),
        logloss_baseline=float(lb.mean()),
        guadagno=float(d.mean()),
        guadagno_ci95=[float(ci[0]), float(ci[1])],
        accuratezza_modello=float((p.argmax(1) == yi).mean()),
        accuratezza_baseline=float((pr.argmax() == yi).mean()),
        H1_pass=bool(ci[0] > 0),
    )
    out[fase] = r
    print(
        f"[{fase}] test: {len(b)} seq, {len(games)} partite | H1 guadagno {d.mean():+.3f} IC95 [{ci[0]:+.3f}, {ci[1]:+.3f}] -> {'PASS' if ci[0] > 0 else 'NON confermato'} | "
        f"H2 scarto quote max {r['max_scarto_quote']:.2f}, silhouette {r['silhouette_congelata_test']:.2f} -> {'PASS' if r['H2_pass'] else 'NON confermato'} | ARI riadattamento {r['ari_riadattamento_descrittivo']:.2f}"
    )
    # H3: le famiglie differiscono nella probabilita' di tiro (fuori campione). Modello addestrato su esplorazione, valutato su riservate.
    sa_ = a.shot.astype(int).values
    sb_ = b.shot.astype(int).values
    Fa = pd.get_dummies(a.cl, dtype=float)
    Fb = pd.get_dummies(b.cl, dtype=float).reindex(columns=Fa.columns, fill_value=0.0)
    p0 = float(np.clip(sa_.mean(), 1e-6, 1 - 1e-6))
    ls = lambda p, y: -np.log(np.where(y == 1, p, 1 - p))
    pf = np.clip(
        LogisticRegression(max_iter=2000, C=0.5).fit(Fa.values, sa_).predict_proba(Fb.values)[:, 1], 1e-6, 1 - 1e-6
    )
    dh = ls(p0, sb_) - ls(pf, sb_)
    prr = np.clip(
        LogisticRegression(max_iter=2000, C=0.5)
        .fit(sc.transform(a[COLS].values), sa_)
        .predict_proba(sc.transform(b[COLS].values))[:, 1],
        1e-6,
        1 - 1e-6,
    )
    dr = ls(p0, sb_) - ls(prr, sb_)
    rng3 = np.random.default_rng(2027)
    cih = np.percentile(
        [np.mean(np.concatenate([dh[g == x] for x in rng3.choice(games, len(games))])) for _ in range(B)], ALPHA_CI
    )
    r.update(
        tiro_train=a.groupby("cl").shot.mean().round(3).to_dict(),
        tiro_test=b.groupby("cl").shot.mean().round(3).to_dict(),
        H3_guadagno=float(dh.mean()),
        H3_ci95=[float(cih[0]), float(cih[1])],
        H3_pass=bool(cih[0] > 0),
        guadagno_modello_feature_descrittivo=float(dr.mean()),
    )
    print(
        f"[{fase}] H3 tiro: guadagno famiglie {dh.mean():+.4f} IC95 [{cih[0]:+.4f}, {cih[1]:+.4f}] -> {'PASS' if cih[0] > 0 else 'NON confermato'} | (descrittivo) modello sulle feature grezze {dr.mean():+.4f} | tiro per famiglia test {r['tiro_test']}"
    )
fn = f"{S.BASE}/{'dryrun' if DRY else 'holdout'}_{S.TEAM.replace(' ', '_')}.json"
json.dump(out, open(fn, "w"), indent=1, default=float)
print("salvato", fn)
