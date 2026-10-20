"""Expected Threat (xT) grid, as in Karun Singh (2018, "Introducing Expected Threat"): the pitch is split into zones, and the value of a zone is the
probability that a possession holding the ball there ends in a goal within the next actions, estimated with a Markov chain over ball moves. Descriptive model.
Usage:  python xt_model.py <data_dir> [out=src/report/xt_grid.json]
Fits the grid once on all matches of the 10 thesis teams (both teams' events) found in <data_dir>/matches and <data_dir>/ev, so every team sheet uses the
same grid (same ruler). The grid is written to xt_grid.json next to this script and read by xthreat.py.
Definitions (fixed before the first fit, not tuned afterwards):
- grid: 16 x 12 zones on the StatsBomb pitch 120 x 80 (Singh's size), each team attacking left to right (StatsBomb locations are already on the acting team's direction).
- moves: open-play passes (StatsBomb pass type not Corner, Free Kick, Goal Kick, Kick Off, Throw-in) and all carries, with a start and end location.
  A pass is completed when StatsBomb gives no pass outcome; carries are always completed.
- shots: open-play shots only (shot type 'Open Play'); goal = shot outcome 'Goal'. Penalties, direct free kicks and corners are left out.
- per zone z: s = shots / (shots + moves), m = moves / (shots + moves), g = goals / shots (0 when no shots), T[z, z'] = completed moves from z ending in z' / moves from z
  (failed moves lead nowhere, as in Singh). xT = s * g + m * T @ xT, solved by iteration from 0 until the largest change is below 1e-7 (at most 200 rounds).
- value of a completed move = xT(end zone) - xT(start zone); can be negative (a back pass)."""

import sys, os, json
import numpy as np

NX, NY = 16, 12
SET_PASS = {"Corner", "Free Kick", "Goal Kick", "Kick Off", "Throw-in"}
TEAMS = [
    ("9_281", "Bayer Leverkusen"),
    ("2_27", "Leicester City"),
    ("11_27", "Barcelona"),
    ("2_27", "Arsenal"),
    ("11_27", "Atlético Madrid"),
    ("11_27", "Real Madrid"),
    ("12_27", "Napoli"),
    ("12_27", "Sassuolo"),
    ("7_27", "Gazélec Ajaccio"),
    ("7_27", "Bordeaux"),
]
GRID = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xt_grid.json")


def zone(loc):
    x = min(max(loc[0], 0.0), 119.999)
    y = min(max(loc[1], 0.0), 79.999)
    return int(x / 120 * NX), int(y / 80 * NY)


def move(e):
    """(start, end, completed, kind) for an open-play pass or a carry, else None."""
    t = e["type"]["name"]
    if t == "Pass":
        p = e.get("pass") or {}
        if (p.get("type") or {}).get("name") in SET_PASS or not e.get("location") or not p.get("end_location"):
            return None
        return e["location"], p["end_location"], "outcome" not in p, "pass"
    if t == "Carry":
        c = e.get("carry") or {}
        if not e.get("location") or not c.get("end_location"):
            return None
        return e["location"], c["end_location"], True, "carry"
    return None


def open_shot(e):
    return (
        e["type"]["name"] == "Shot"
        and e.get("location")
        and ((e.get("shot") or {}).get("type") or {}).get("name") == "Open Play"
    )


def fit(match_files):
    shots, goals, moves = np.zeros((NX, NY)), np.zeros((NX, NY)), np.zeros((NX, NY))
    T = np.zeros((NX, NY, NX, NY))
    n = 0
    for f in match_files:
        for e in json.load(open(f, encoding="utf-8")):
            if open_shot(e):
                i, j = zone(e["location"])
                shots[i, j] += 1
                goals[i, j] += e["shot"].get("outcome", {}).get("name") == "Goal"
                continue
            m = move(e)
            if m is None:
                continue
            i, j = zone(m[0])
            moves[i, j] += 1
            if m[2]:
                a, b = zone(m[1])
                T[i, j, a, b] += 1
        n += 1
    tot = shots + moves
    s = np.divide(shots, tot, out=np.zeros_like(tot), where=tot > 0)
    mv = np.divide(moves, tot, out=np.zeros_like(tot), where=tot > 0)
    g = np.divide(goals, shots, out=np.zeros_like(shots), where=shots > 0)
    T = np.divide(T, moves[:, :, None, None], out=np.zeros_like(T), where=moves[:, :, None, None] > 0).reshape(
        NX * NY, NX * NY
    )
    xt = np.zeros(NX * NY)
    base = (s * g).ravel()
    rounds = 0
    for rounds in range(1, 201):
        new = base + mv.ravel() * (T @ xt)
        if np.max(np.abs(new - xt)) < 1e-7:
            xt = new
            break
        xt = new
    return dict(
        nx=NX,
        ny=NY,
        pitch=[120, 80],
        matches=n,
        shots=int(shots.sum()),
        goals=int(goals.sum()),
        moves=int(moves.sum()),
        rounds=rounds,
        xt=xt.reshape(NX, NY).round(6).tolist(),
    )


def load_grid(path=GRID):
    g = json.load(open(path, encoding="utf-8"))
    return np.array(g["xt"]), g


if __name__ == "__main__":
    data = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else GRID
    ids = set()
    for mf, team in TEAMS:
        for g in json.load(open(os.path.join(data, "matches", f"{mf}.json"), encoding="utf-8")):
            if team in (g["home_team"]["home_team_name"], g["away_team"]["away_team_name"]):
                ids.add(g["match_id"])
    files = [os.path.join(data, "ev", f"{m}.json") for m in sorted(ids)]
    miss = [f for f in files if not os.path.exists(f)]
    if miss:
        sys.exit(f"{len(miss)} event files missing, e.g. {miss[0]}: download them first (src/week1/download_data.py).")
    res = fit(files)
    res["match_ids"] = sorted(ids)
    json.dump(res, open(out, "w", encoding="utf-8"), indent=0)
    print(
        f"xT grid from {res['matches']} matches ({res['moves']} moves, {res['shots']} open-play shots, {res['goals']} goals), {res['rounds']} rounds -> {out}"
    )
