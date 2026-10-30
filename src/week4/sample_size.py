"""How many matches does an opposition report need to be reliable? (descriptive)
For n = 3, 5, 8, 10, 15 matches drawn at random (500 draws) from the team's season, measures how far the tendencies computed on those matches
are from those of the whole season: style (passes per sequence, long-pass share, share of sequences from the own half, share with a shot,
long-pass share from goal kicks) and family shares (K-Means partition frozen on the whole season: largest error among the family shares).
Usage: python sample_size.py <matches.json> "<Team>" [data_folder=.]"""

import sys, os, json, warnings
import numpy as np

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "week2"))
import sequences_clustering as S
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

COLS = ["x0", "w0", "x1", "w1", "net_x", "path_len", "directness", "n_pass", "long_share", "width_std", "dur"]
CUT = 45
K = {"build-up": 5, "advanced": 3}
NS = [3, 5, 8, 10, 15]
R = 500
df, nm = S.extract()
df["w0"] = (df.y0 - 40).abs()
df["w1"] = (df.y1 - 40).abs()
rng = np.random.default_rng(41)
df["fam"] = ""
for ph, k in K.items():
    m = (df.x0 < CUT) if ph == "build-up" else (df.x0 >= CUT)
    sc = StandardScaler().fit(df.loc[m, COLS].values)
    df.loc[m, "fam"] = [
        f"{ph[0].upper()}{l}"
        for l in KMeans(k, n_init=20, random_state=0).fit_predict(sc.transform(df.loc[m, COLS].values))
    ]


def metrics(d):
    gk = d[d.play_pattern == "From Goal Kick"].long_share
    return dict(
        passes=d.n_pass.mean(),
        long=d.long_share.mean(),
        buildup_share=(d.x0 < CUT).mean(),
        shot=d.shot.mean(),
        goalkick_long=gk.mean() if len(gk) else np.nan,
    )


def shares(d, ph):
    s = d[d.fam.str.startswith(ph[0].upper())]
    fams = sorted(df[df.fam.str.startswith(ph[0].upper())].fam.unique())
    return np.array([(s.fam == f).sum() / max(len(s), 1) for f in fams])


full = metrics(df)
fsh = {ph: shares(df, ph) for ph in K}
games = df.gi.unique()
out = {"team": S.TEAM, "matches": int(len(games)), "full": {k: float(v) for k, v in full.items()}, "n": {}}
for n in NS:
    if n >= len(games):
        continue
    err = {k: [] for k in full}
    serr = {ph: [] for ph in K}
    for _ in range(R):
        d = df[df.gi.isin(rng.choice(games, n, replace=False))]
        mm = metrics(d)
        for k in full:
            err[k].append(abs(mm[k] - full[k]))
        for ph in K:
            serr[ph].append(np.max(np.abs(shares(d, ph) - fsh[ph])))
    out["n"][str(n)] = dict(
        **{f"{k}_p90": float(np.nanpercentile(v, 90)) for k, v in err.items()},
        **{f"{k}_median": float(np.nanmedian(v)) for k, v in err.items()},
        **{f"shares_{ph}_p90": float(np.percentile(v, 90)) for ph, v in serr.items()},
    )
    print(
        f"[{S.TEAM}] n={n:2d} | error P90: passes {out['n'][str(n)]['passes_p90']:.2f}, long {out['n'][str(n)]['long_p90']:.3f}, shot {out['n'][str(n)]['shot_p90']:.3f} | family shares max error P90: build-up {out['n'][str(n)]['shares_build-up_p90']:.3f}, advanced {out['n'][str(n)]['shares_advanced_p90']:.3f}"
    )
json.dump(
    out,
    open(f"{S.BASE}/samplesize_{S.TEAM.replace(' ', '_')}.json", "w", encoding="utf-8"),
    indent=1,
    ensure_ascii=False,
)
