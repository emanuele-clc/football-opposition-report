"""Quante partite servono perche' un report sull'avversario sia affidabile? (descrittivo)
Per n = 3, 5, 8, 10, 15 partite estratte a caso (500 estrazioni) dalla stagione della squadra, si misura di quanto le tendenze calcolate su quelle partite
si discostano da quelle della stagione intera: stile (passaggi per sequenza, quota di lanci lunghi, quota di sequenze dalla propria meta' campo, quota con tiro,
quota di lanci lunghi dai rinvii) e quote delle famiglie (partizione K-Means congelata sulla stagione intera: errore massimo tra le quote delle famiglie).
Uso: python sample_size.py <matches.json> "<Squadra>" [cartella_dati=.]"""
import sys, os, json, warnings
import numpy as np
warnings.filterwarnings("ignore"); sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "week2"))
import sequences_clustering as S
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
COLS = ["x0", "w0", "x1", "w1", "net_x", "path_len", "directness", "n_pass", "long_share", "width_std", "dur"]; CUT = 45; K = {"build-up": 5, "advanced": 3}; NS = [3, 5, 8, 10, 15]; R = 500
df, nm = S.extract(); df["w0"] = (df.y0 - 40).abs(); df["w1"] = (df.y1 - 40).abs(); rng = np.random.default_rng(41)
df["fam"] = ""
for ph, k in K.items():
    m = (df.x0 < CUT) if ph == "build-up" else (df.x0 >= CUT); sc = StandardScaler().fit(df.loc[m, COLS].values); df.loc[m, "fam"] = [f"{ph[0].upper()}{l}" for l in KMeans(k, n_init=20, random_state=0).fit_predict(sc.transform(df.loc[m, COLS].values))]
def metrics(d):
    gk = d[d.play_pattern == "From Goal Kick"].long_share
    return dict(passes=d.n_pass.mean(), long=d.long_share.mean(), buildup_share=(d.x0 < CUT).mean(), shot=d.shot.mean(), goalkick_long=gk.mean() if len(gk) else np.nan)
def shares(d, ph):
    s = d[d.fam.str.startswith(ph[0].upper())]; fams = sorted(df[df.fam.str.startswith(ph[0].upper())].fam.unique()); return np.array([(s.fam == f).sum() / max(len(s), 1) for f in fams])
full = metrics(df); fsh = {ph: shares(df, ph) for ph in K}; games = df.gi.unique(); out = {"team": S.TEAM, "matches": int(len(games)), "full": {k: float(v) for k, v in full.items()}, "n": {}}
for n in NS:
    if n >= len(games): continue
    err = {k: [] for k in full}; serr = {ph: [] for ph in K}
    for _ in range(R):
        d = df[df.gi.isin(rng.choice(games, n, replace=False))]; mm = metrics(d)
        for k in full: err[k].append(abs(mm[k] - full[k]))
        for ph in K: serr[ph].append(np.max(np.abs(shares(d, ph) - fsh[ph])))
    out["n"][str(n)] = dict(**{f"{k}_p90": float(np.nanpercentile(v, 90)) for k, v in err.items()}, **{f"{k}_median": float(np.nanmedian(v)) for k, v in err.items()}, **{f"shares_{ph}_p90": float(np.percentile(v, 90)) for ph, v in serr.items()})
    print(f"[{S.TEAM}] n={n:2d} | error P90: passes {out['n'][str(n)]['passes_p90']:.2f}, long {out['n'][str(n)]['long_p90']:.3f}, shot {out['n'][str(n)]['shot_p90']:.3f} | family shares max error P90: build-up {out['n'][str(n)]['shares_build-up_p90']:.3f}, advanced {out['n'][str(n)]['shares_advanced_p90']:.3f}")
json.dump(out, open(f"{S.BASE}/samplesize_{S.TEAM.replace(' ', '_')}.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
