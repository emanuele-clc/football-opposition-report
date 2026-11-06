"""How many matches does an opposition report need? (descriptive)
Draw n = 3, 5, 8, 10, 15 matches at random from the season (500 times) and see how far the numbers of those n matches are
from the numbers of the whole season: passes per sequence, long-pass share, share of sequences from our half, shot rate,
long-pass share from goal kicks, and the family shares (families fitted on the whole season; largest error among the shares).
Usage: python sample_size.py <matches.json> "<Team>" [data_folder=.]   -> samplesize_<Team>.json"""

import sys, os, json, warnings
import numpy as np

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sequences_clustering as S
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

COLS = ["x0", "w0", "x1", "w1", "net_x", "path_len", "directness", "n_pass", "long_share", "width_std", "dur"]
CUT = 45
K = {"build-up": 5, "advanced": 3}
DRAWS = 500

df, n_matches = S.extract()
df["w0"] = (df.y0 - 40).abs()
df["w1"] = (df.y1 - 40).abs()
rng = np.random.default_rng(41)

# families on the whole season: B0..B4 (build-up), A0..A2 (advanced)
df["fam"] = ""
for phase, k in K.items():
    if phase == "build-up":
        m = df.x0 < CUT
    else:
        m = df.x0 >= CUT
    X = StandardScaler().fit(df.loc[m, COLS].values).transform(df.loc[m, COLS].values)
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
    r = {}
    for k, v in errors.items():
        r[f"{k}_p90"] = float(np.nanpercentile(v, 90))
    for k, v in errors.items():
        r[f"{k}_median"] = float(np.nanmedian(v))
    for phase, v in share_errors.items():
        r[f"shares_{phase}_p90"] = float(np.percentile(v, 90))
    out["n"][str(n)] = r
    print(
        f"[{S.TEAM}] n={n:2d} | error P90: passes {r['passes_p90']:.2f}, long {r['long_p90']:.3f}, shot {r['shot_p90']:.3f} | "
        f"family shares max error P90: build-up {r['shares_build-up_p90']:.3f}, advanced {r['shares_advanced_p90']:.3f}"
    )
json.dump(out, open(f"{S.BASE}/samplesize_{S.TEAM.replace(' ', '_')}.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
