"""Cuts the matches of a team into open-play sequences and describes each one with 11 numbers.

A sequence is a possession in open play with at least 3 passes (no corners, free kicks or kick-offs).
For each one I keep where it starts and ends, how far it goes forward, how long the ball path is, how direct it is,
number of passes, share of long passes, width and duration. Also minute, half, how it started and if it ended in a shot.
This file is not run on its own: the other scripts import it and call extract().
jaccard_stability() is used to check if the families come out the same when the data is resampled.
The choice of k was made once with archive/choose_k.py (removed on 8 Nov 2026; see git commit 7d6a28f)."""

import json, sys
import numpy as np, pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score
from sklearn.preprocessing import StandardScaler

# match list, team and data folder, from the command line
# (the other scripts can change these three before calling extract())
MF = sys.argv[1]
TEAM = sys.argv[2]
BASE = sys.argv[3] if len(sys.argv) > 3 else "."

# the settings of the protocol: 11 features, phase cut at x = 45, 5 build-up families and 3 advanced ones
COLS = ["x0", "w0", "x1", "w1", "net_x", "path_len", "directness", "n_pass", "long_share", "width_std", "dur"]
CUT = 45
K = {"costruzione": 5, "avanzata": 3}

# play patterns we keep (no corners, free kicks, kick-offs)
OPEN_PLAY = {"Regular Play", "From Counter", "From Goal Kick", "From Keeper", "From Throw In"}

# 12 zones: 4 bands along the pitch (A = our box ... D = last third) x 3 across (s = left, C = centre, d = right)
XB = [0, 30, 60, 90, 120]
YB = [0, 80 / 3, 160 / 3, 80.01]
ZN = []
for c in "ABCD":
    for r in "sCd":
        ZN.append(c + r)


def zone(x, y):
    # number of the zone (0-11) where the point (x, y) falls
    col = min(int(np.searchsorted(XB, x, side="right") - 1), 3)
    row = min(int(np.searchsorted(YB, y, side="right") - 1), 2)
    return col * 3 + row


def path_points(events):
    # start of the sequence, then where every pass and carry ends
    points = [events[0]["location"]]
    for e in events:
        if e["type"]["name"] == "Pass":
            points.append(e["pass"]["end_location"])
        elif e["type"]["name"] == "Carry":
            points.append(e["carry"]["end_location"])
    # drop a point if it is the same as the one before
    clean = [points[0]]
    for p in points[1:]:
        if p != clean[-1]:
            clean.append(p)
    return clean


def sequence_row(events, pid, game, gi, opponent):
    # one possession -> one row, or None if it is not open play with 3+ passes
    pattern = events[0]["play_pattern"]["name"]
    if pattern not in OPEN_PLAY:
        return None
    passes = [e for e in events if e["type"]["name"] == "Pass"]
    if len(passes) < 3:
        return None
    points = path_points(events)
    if len(points) < 4:
        return None

    P = np.array(points)[:, :2]  # the ball path, one (x, y) per row
    x0, y0 = P[0, 0], P[0, 1]
    x1, y1 = P[-1, 0], P[-1, 1]
    steps = np.diff(P, axis=0)
    length = float(np.sum(np.linalg.norm(steps, axis=1)))  # metres the ball travels

    start = events[0]["minute"] * 60 + events[0]["second"]
    end = events[-1]["minute"] * 60 + events[-1]["second"]

    long_passes = [p["pass"].get("length", 0) >= 30 for p in passes]
    shot = int(any(e["type"]["name"] == "Shot" for e in events))

    row = {}
    row["match"] = game["match_id"]
    row["gi"] = gi  # match number in date order
    row["data"] = game["match_date"]
    row["avv"] = opponent
    row["minuto"] = events[0]["minute"]
    row["sec"] = events[0]["second"]
    row["tempo"] = events[0]["period"]
    row["pid"] = pid
    row["play_pattern"] = pattern
    row["n_pass"] = len(passes)
    row["n_pts"] = len(P)
    row["x0"] = x0
    row["y0"] = y0
    row["x1"] = x1
    row["y1"] = y1
    row["net_x"] = x1 - x0
    row["path_len"] = length
    row["directness"] = float(np.clip((x1 - x0) / max(length, 1), -1, 1))
    row["long_share"] = float(np.mean(long_passes))
    row["width_std"] = float(P[:, 1].std())
    row["mean_x"] = float(P[:, 0].mean())
    row["dur"] = max(end - start, 0)
    row["shot"] = shot
    row["zone0"] = zone(*P[0])
    row["zone1"] = zone(*P[-1])
    row["zones"] = [zone(*p) for p in P]
    row["path"] = P.tolist()
    return row


def extract():
    # all open-play sequences of TEAM, plus the number of matches
    matches = []
    for g in json.load(open(MF, encoding="utf-8")):
        if TEAM in (g["home_team"]["home_team_name"], g["away_team"]["away_team_name"]):
            matches.append(g)
    matches.sort(key=lambda g: g["match_date"])

    rows = []
    for gi, g in enumerate(matches):
        home = g["home_team"]["home_team_name"]
        away = g["away_team"]["away_team_name"]
        opponent = away if home == TEAM else home

        # our passes, carries, shots and dribbles while we have the ball, grouped by possession number
        possessions = {}
        events = json.load(open(f"{BASE}/ev/{g['match_id']}.json"))
        for e in events:
            ours = e.get("possession_team", {}).get("name") == TEAM and e["team"]["name"] == TEAM
            if ours and e["type"]["name"] in ("Pass", "Carry", "Shot", "Dribble"):
                possessions.setdefault(e["possession"], []).append(e)

        for pid, evs in possessions.items():
            row = sequence_row(evs, pid, g, gi, opponent)
            if row:
                rows.append(row)
    return pd.DataFrame(rows), len(matches)


def jaccard_stability(X, labels, k, B=200, seed=0):
    # refit K-Means on B bootstrap samples; for each group, how well it is found again (Jaccard)
    rng = np.random.default_rng(seed)
    n = len(labels)
    score = np.zeros(k)
    aris = []
    for _ in range(B):
        idx = rng.integers(0, n, n)  # resample the sequences with replacement
        km = KMeans(k, n_init=5, random_state=int(rng.integers(1e9))).fit(X[idx])
        new = km.predict(X)
        aris.append(adjusted_rand_score(labels, new))
        for c in range(k):
            old_group = labels == c
            # Jaccard = in both / in at least one; keep the best match among the new groups
            best = 0
            for j in range(k):
                new_group = new == j
                jac = (old_group & new_group).sum() / (old_group | new_group).sum()
                best = max(best, jac)
            score[c] += best
    return score / B, float(np.mean(aris)), list(np.percentile(aris, [2.5, 97.5]))


# ---------------------------------------------------------------- shared by the analysis scripts
def add_width(d):
    # distance from the centre line, so left and right count the same
    d["w0"] = (d.y0 - 40).abs()
    d["w1"] = (d.y1 - 40).abs()
    return d


def split(df, n_matches, dry=False):
    # first 70% of the matches to fit, last 30% to test; dry run: split the first 70% again, never touch the rest
    k0 = int(round(n_matches * 0.7))
    if dry:
        k1 = int(round(k0 * 0.7))
        return add_width(df[df.gi < k1].copy()), add_width(df[(df.gi >= k1) & (df.gi < k0)].copy())
    return add_width(df[df.gi < k0].copy()), add_width(df[df.gi >= k0].copy())


def in_phase(d, phase, cut=CUT):
    return d.x0 < cut if phase == "costruzione" else d.x0 >= cut


def phase_rows(d, phase, cut=CUT):
    return d[in_phase(d, phase, cut)].reset_index(drop=True)


def fit_families(train):
    # scaler + K-Means per phase; family 1 = the one that starts deepest (ties: the bigger one)
    models = {}
    for phase, k in K.items():
        sub = train[in_phase(train, phase)]
        scaler = StandardScaler().fit(sub[COLS].values)
        km = KMeans(k, n_init=20, random_state=0).fit(scaler.transform(sub[COLS].values))
        order = sorted(range(k), key=lambda c: (sub.x0.values[km.labels_ == c].mean(), -(km.labels_ == c).sum()))
        models[phase] = (scaler, km, {c: i + 1 for i, c in enumerate(order)})
    return models


def assign(d, models):
    # family of every sequence (C1.. build-up, A1.. advanced) and the family of the sequence before it
    d = d.copy()
    d["cl"] = ""
    for phase, (scaler, km, number) in models.items():
        rows = in_phase(d, phase)
        if rows.sum():
            letter = "C" if phase == "costruzione" else "A"
            d.loc[rows, "cl"] = [f"{letter}{number[l]}" for l in km.predict(scaler.transform(d.loc[rows, COLS].values))]
    d = d.sort_values(["gi", "pid"]).reset_index(drop=True)
    d["prev_cl"] = d.groupby("gi").cl.shift(1).fillna("start")
    return d


def context(d, cols=None):
    # the inputs of the protocol model: play pattern, minute, half, previous family
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


def boot_ci(values, g, rng, B=1000):
    # 95% interval of the mean, resampling whole matches (g = match of each value)
    games = np.unique(g)
    means = [np.mean(np.concatenate([values[g == x] for x in rng.choice(games, len(games))])) for _ in range(B)]
    return np.percentile(means, [2.5, 97.5])
