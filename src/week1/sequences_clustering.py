"""Settimana 2 - modulo L2: sequenze di possesso, zone, clustering e stabilita' (bootstrap).
Uso: python sequences_clustering.py <matches.json> "<Squadra>" [cartella_dati=.]
Dati: StatsBomb Open Data (licenza non commerciale, citare StatsBomb). Orientamento: StatsBomb normalizza gia' la direzione di attacco
(sinistra verso destra per la squadra che compie l'evento); y piccolo = fascia sinistra (verificato con le posizioni dei terzini).
Regola di metodo: il clustering e la scelta di k usano solo le prime 70% partite (esplorazione). Le ultime partite NON vengono toccate."""
import json, sys, math, collections
import numpy as np, pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score, adjusted_rand_score
from sklearn.preprocessing import StandardScaler

MF, TEAM = sys.argv[1], sys.argv[2]; BASE = sys.argv[3] if len(sys.argv) > 3 else "."
OPEN_PLAY = {"Regular Play", "From Counter", "From Goal Kick", "From Keeper", "From Throw In"}   # niente corner, punizioni, calcio d'inizio
XB = [0, 30, 60, 90, 120]; YB = [0, 80 / 3, 160 / 3, 80.01]
def zone(x, y): return min(int(np.searchsorted(XB, x, side="right") - 1), 3) * 3 + min(int(np.searchsorted(YB, y, side="right") - 1), 2)
ZN = [f"{c}{r}" for c in "ABCD" for r in "sCd"]     # A..D = lunghezza (A: propria area, D: ultimo terzo), s/C/d = sinistra/centro/destra

def extract():
    ms = sorted([g for g in json.load(open(MF, encoding="utf-8")) if TEAM in (g["home_team"]["home_team_name"], g["away_team"]["away_team_name"])], key=lambda g: g["match_date"])
    rows = []
    for gi, g in enumerate(ms):
        ev = json.load(open(f"{BASE}/ev/{g['match_id']}.json", encoding="utf-8")); poss = collections.OrderedDict()
        for e in ev:
            if e.get("possession_team", {}).get("name") == TEAM and e["team"]["name"] == TEAM and e["type"]["name"] in ("Pass", "Carry", "Shot", "Dribble"):
                poss.setdefault(e["possession"], []).append(e)
        for pid, es in poss.items():
            pp = es[0]["play_pattern"]["name"]
            if pp not in OPEN_PLAY: continue
            passes = [e for e in es if e["type"]["name"] == "Pass"]
            if len(passes) < 3: continue
            pts = [es[0]["location"]]
            for e in es:
                t = e["type"]["name"]
                if t == "Pass": pts.append(e["pass"]["end_location"])
                elif t == "Carry": pts.append(e["carry"]["end_location"])
            pts = [p for k, p in enumerate(pts) if k == 0 or p != pts[k-1]]
            if len(pts) < 4: continue
            P = np.array(pts)[:, :2]; L = float(np.sum(np.linalg.norm(np.diff(P, axis=0), axis=1)))
            shot = any(e["type"]["name"] == "Shot" for e in es)
            t0 = es[0]["minute"] * 60 + es[0]["second"]; t1 = es[-1]["minute"] * 60 + es[-1]["second"]
            lp = np.mean([p["pass"].get("length", 0) >= 30 for p in passes])
            rows.append(dict(match=g["match_id"], gi=gi, pid=pid, play_pattern=pp, n_pass=len(passes), n_pts=len(P),
                             x0=P[0, 0], y0=P[0, 1], x1=P[-1, 0], y1=P[-1, 1], net_x=P[-1, 0] - P[0, 0], path_len=L,
                             directness=float(np.clip((P[-1, 0] - P[0, 0]) / max(L, 1), -1, 1)), long_share=float(lp),
                             width_std=float(P[:, 1].std()), mean_x=float(P[:, 0].mean()), dur=max(t1 - t0, 0), shot=int(shot),
                             zone0=zone(*P[0]), zone1=zone(*P[-1]), zones=[zone(*p) for p in P], path=P.tolist()))
    return pd.DataFrame(rows), len(ms)

def features(df):
    n = len(df); F = {}
    for z in range(12): F[f"start_{ZN[z]}"] = (df.zone0 == z).astype(float).values; F[f"end_{ZN[z]}"] = (df.zone1 == z).astype(float).values
    for z in range(12): F[f"occ_{ZN[z]}"] = np.array([np.mean([q == z for q in zs]) for zs in df.zones])
    for c in ("n_pass", "net_x", "path_len", "directness", "long_share", "width_std", "mean_x", "dur"): F[c] = df[c].values.astype(float)
    for pp in sorted(OPEN_PLAY): F[f"pp_{pp}"] = (df.play_pattern == pp).astype(float).values
    return pd.DataFrame(F)

def jaccard_stability(Xp, labels, k, B=200, seed=0):
    rng = np.random.default_rng(seed); n = len(labels); sc = np.zeros(k); aris = []
    for b in range(B):
        idx = rng.integers(0, n, n)
        km = KMeans(k, n_init=5, random_state=int(rng.integers(1e9))).fit(Xp[idx]); lb = km.predict(Xp)
        aris.append(adjusted_rand_score(labels, lb))
        for c in range(k):
            a = labels == c; sc[c] += max((a & (lb == j)).sum() / (a | (lb == j)).sum() for j in range(k))
    return sc / B, float(np.mean(aris)), list(np.percentile(aris, [2.5, 97.5]))

if __name__ == "__main__":
    df, nm = extract(); k0 = int(round(nm * 0.7))
    print(f"{TEAM}: {nm} partite, {len(df)} sequenze di gioco aperto (>=3 passaggi, >=4 punti); esplorazione = prime {k0} partite")
    ex = df[df.gi < k0].reset_index(drop=True); print("sequenze di esplorazione:", len(ex), "| riservate alla validazione:", int((df.gi >= k0).sum()))
    X = StandardScaler().fit_transform(features(ex)); pca = PCA(0.90, random_state=0).fit(X); Xp = pca.transform(X); print("componenti PCA (90% varianza):", Xp.shape[1])
    sel = []
    for k in range(3, 9):
        km = KMeans(k, n_init=10, random_state=0).fit(Xp); lab = km.labels_
        sj, ari, ari_ci = jaccard_stability(Xp, lab, k, B=100)
        sel.append(dict(k=k, silhouette=float(silhouette_score(Xp, lab)), ari=ari, jaccard_min=float(sj.min()), jaccard_mean=float(sj.mean()), sizes=sorted(np.bincount(lab).tolist(), reverse=True)))
        print(f"k={k}: silhouette {sel[-1]['silhouette']:.3f} | ARI bootstrap {ari:.2f} | Jaccard min {sj.min():.2f} medio {sj.mean():.2f} | dimensioni {sel[-1]['sizes']}")
    json.dump(sel, open(f"{BASE}/k_selection_{TEAM.replace(' ','_')}.json", "w"), indent=1)
