"""Week 2 - open-play sequences of a team, their features, and the choice of k.
Not run on its own: imported as S, then S.extract().
Data: StatsBomb Open Data (cite StatsBomb). StatsBomb already turns every event so the team attacks left to right; small y = left.
The other scripts import this file and use extract(). The choice of k (done once, on the exploration matches) is in archive/choose_k.py."""

import json, sys
import numpy as np, pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score

# the other scripts change these three before calling extract()
MF = sys.argv[1]
TEAM = sys.argv[2]
if len(sys.argv) > 3:
    BASE = sys.argv[3]
else:
    BASE = "."

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
    col = int(np.searchsorted(XB, x, side="right") - 1)
    row = int(np.searchsorted(YB, y, side="right") - 1)
    col = min(col, 3)
    row = min(row, 2)
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

    P = np.array(points)[:, :2]
    x0, y0 = P[0, 0], P[0, 1]
    x1, y1 = P[-1, 0], P[-1, 1]
    steps = np.diff(P, axis=0)
    length = float(np.sum(np.linalg.norm(steps, axis=1)))

    start = events[0]["minute"] * 60 + events[0]["second"]
    end = events[-1]["minute"] * 60 + events[-1]["second"]

    long_passes = [p["pass"].get("length", 0) >= 30 for p in passes]
    shot = 0
    for e in events:
        if e["type"]["name"] == "Shot":
            shot = 1

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
        if g["home_team"]["home_team_name"] == TEAM:
            opponent = g["away_team"]["away_team_name"]
        else:
            opponent = g["home_team"]["home_team_name"]

        # group our passes, carries, shots and dribbles by possession number
        possessions = {}
        events = json.load(open(f"{BASE}/ev/{g['match_id']}.json"))
        for e in events:
            if e.get("possession_team", {}).get("name") != TEAM:
                continue
            if e["team"]["name"] != TEAM:
                continue
            if e["type"]["name"] not in ("Pass", "Carry", "Shot", "Dribble"):
                continue
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
    for b in range(B):
        idx = rng.integers(0, n, n)
        km = KMeans(k, n_init=5, random_state=int(rng.integers(1e9))).fit(X[idx])
        new = km.predict(X)
        aris.append(adjusted_rand_score(labels, new))
        for c in range(k):
            a = labels == c
            best = 0
            for j in range(k):
                jac = (a & (new == j)).sum() / (a | (new == j)).sum()
                best = max(best, jac)
            score[c] += best
    return score / B, float(np.mean(aris)), list(np.percentile(aris, [2.5, 97.5]))
