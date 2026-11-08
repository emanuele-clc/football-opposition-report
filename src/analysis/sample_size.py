"""How many matches do you need for a report?

I take 3, 5, 8, 10 or 15 random matches (500 times) and look how far their numbers are from the whole season:
passes per sequence, long passes, sequences from own half, shot rate, long goal kicks and family shares.

Usage: python sample_size.py <matches.json> "<Team>" [data_folder=.]   -> samplesize_<Team>.json"""

import sys, os, json, warnings
import numpy as np

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sequences_clustering as S
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

COLS, CUT = S.COLS, S.CUT
K = {"build-up": 5, "advanced": 3}
DRAWS = 500

df, n_matches = S.extract()
S.add_width(df)
rng = np.random.default_rng(41)

# families on the whole season: B0..B4 (build-up), A0..A2 (advanced)
df["fam"] = ""
for phase, k in K.items():
    m = df.x0 < CUT if phase == "build-up" else df.x0 >= CUT
    X = StandardScaler().fit_transform(df.loc[m, COLS].values)
    labels = KMeans(k, n_init=20, random_state=0).fit_predict(X)
    df.loc[m, "fam"] = [f"{phase[0].upper()}{l}" for l in labels]


def numbers(d):
    goal_kicks = d[d.play_pattern == "From Goal Kick"].long_share
    return {
        "passes": d.n_pass.mean(),
        "long": d.long_share.mean(),
        "buildup_share": (d.x0 < CUT).mean(),
        "shot": d.shot.mean(),
        "goalkick_long": goal_kicks.mean() if len(goal_kicks) else np.nan,
    }


def shares(d, phase):
    letter = phase[0].upper()
    families = sorted(df[df.fam.str.startswith(letter)].fam.unique())
    s = d[d.fam.str.startswith(letter)]
    return np.array([(s.fam == f).sum() / max(len(s), 1) for f in families])


season = numbers(df)
season_shares = {phase: shares(df, phase) for phase in K}
games = df.gi.unique()
out = {"team": S.TEAM, "matches": int(len(games)), "full": {k: float(v) for k, v in season.items()}, "n": {}}
for n in [3, 5, 8, 10, 15]:
    if n >= len(games):
        continue
    errors = {k: [] for k in season}
    share_errors = {phase: [] for phase in K}
    for _ in range(DRAWS):
        d = df[df.gi.isin(rng.choice(games, n, replace=False))]
        now = numbers(d)
        for k in season:
            errors[k].append(abs(now[k] - season[k]))
        for phase in K:
            share_errors[phase].append(np.max(np.abs(shares(d, phase) - season_shares[phase])))
    r = {f"{k}_p90": float(np.nanpercentile(v, 90)) for k, v in errors.items()}
    r.update({f"{k}_median": float(np.nanmedian(v)) for k, v in errors.items()})
    r.update({f"shares_{phase}_p90": float(np.percentile(v, 90)) for phase, v in share_errors.items()})
    out["n"][str(n)] = r
    print(f"[{S.TEAM}] n={n:2d} | passes {r['passes_p90']:.2f}, long {r['long_p90']:.3f}, shot {r['shot_p90']:.3f} (error P90)")
json.dump(out, open(f"{S.BASE}/samplesize_{S.TEAM.replace(' ', '_')}.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
