"""Turns a simple CSV of events (from any provider) into files that look like StatsBomb, so the rest of the code works the same.

If the CSV has no possession numbers, they are rebuilt. --validate-only just checks the file.

Usage:  python generic_csv.py events.csv out_folder [--coords 100|120x80] [--validate-only] [--provider="Provider name"]
Required columns: match_id, match_date, home_team, away_team, period, minute, second, team, event_type, x, y
Optional columns: end_x, end_y, possession_id, restart, pass_length, shot_goal, player, recipient, xg, pass_outcome
- event_type: pass, carry, shot, dribble, own_goal, and the defensive actions duel, interception, foul, clearance, ball_recovery, block; anything else = other.
- x from 0 (own goal) to 100 (opponent goal), y from 0 to 100, the team of the event always attacks left to right. --coords 120x80 for a 120 x 80 pitch.
- minute counts from the start of the match (second half starts at 45), period 1 or 2.
- no possession_id: possessions are rebuilt (see new_possessions). No restart column: set pieces cannot be excluded.
- pass_length in metres on the 120 x 80 pitch; computed from the coordinates if missing. pass_outcome: complete / incomplete (empty = complete)."""

import sys, os, json
import numpy as np, pandas as pd

REQ = ["match_id", "match_date", "home_team", "away_team", "period", "minute", "second", "team", "event_type", "x", "y"]
# our event_type -> StatsBomb type name
TYPE = {"pass": "Pass", "carry": "Carry", "shot": "Shot", "dribble": "Dribble"}
DEFT = {
    "duel": "Duel",
    "interception": "Interception",
    "foul": "Foul Committed",
    "clearance": "Clearance",
    "ball_recovery": "Ball Recovery",
    "block": "Block",
    "own_goal": "Own Goal Against",  # row team = the team that put the ball in its own net
}
# restart -> StatsBomb play pattern
RESTART = {
    "goal_kick": "From Goal Kick",
    "throw_in": "From Throw In",
    "corner": "From Corner",
    "free_kick": "From Free Kick",
    "kick_off": "From Kick Off",
    "penalty": "From Free Kick",
    "keeper": "From Keeper",
}
CTRL = {"pass", "carry", "shot", "dribble"}  # actions with the ball


def validate(df):
    # list of problems (warnings too), and the table with clean event types; None if columns are missing
    missing = [c for c in REQ if c not in df.columns]
    if missing:
        return [f"colonne mancanti: {missing}"], None
    problems = []
    d = df.copy()
    d["event_type"] = d.event_type.astype(str).str.lower().str.strip()
    d.loc[~d.event_type.isin(CTRL | set(DEFT)), "event_type"] = "altro"
    for c in ("period", "minute", "second"):
        bad = pd.to_numeric(d[c], errors="coerce").isna().sum()
        if bad:
            problems.append(f"{bad} valori non numerici in '{c}'")
    ctrl_rows = d[d.event_type.isin(CTRL)]
    for c in ("x", "y"):
        bad = pd.to_numeric(ctrl_rows[c], errors="coerce").isna().sum()
        if bad:
            problems.append(f"{bad} eventi pass/carry/shot/dribble senza '{c}': non utilizzabili")
    if not set(d.period.unique()) <= {1, 2, 3, 4, 5}:
        problems.append(f"valori di period inattesi: {sorted(d.period.unique())}")
    passes = d[d.event_type == "pass"]
    if len(passes) and ("end_x" not in d.columns or passes.end_x.isna().mean() > 0.05):
        problems.append("many passes without end_x/end_y: they are needed for length and path")
    if "restart" not in d.columns:
        problems.append("WARNING: column 'restart' is missing: set-piece restarts (goal kicks, throw-ins, corners) cannot be excluded")
    if "possession_id" not in d.columns:
        problems.append("WARNING: 'possession_id' is missing: possessions will be reconstructed with a heuristic")
    max_x = pd.to_numeric(d.x, errors="coerce").max()
    if 105 < max_x <= 120:
        problems.append("WARNING: x goes above 105: coordinates may be 120x80, use --coords 120x80")
    return problems, d


def has_value(v):
    if v is None or v == "":
        return False
    if isinstance(v, float) and np.isnan(v):
        return False
    return True


def new_possessions(g):
    """Possession number of every row, when the data have none. A new possession starts when the half changes, at a restart,
    or when the other team has the ball for 2 actions in a row (or shoots). One touch of the other team (a clearance) is not enough.
    It is a heuristic: tests/test_adapter_roundtrip.py checks how close it gets to StatsBomb."""
    team = g.team.values
    kind = g.event_type.values
    period = g.period.values
    n = len(g)
    if "restart" in g.columns:
        restart = g["restart"].values
    else:
        restart = [None] * n

    # for every action with the ball, the next action with the ball
    ctrl = [i for i in range(n) if kind[i] in CTRL]
    next_ctrl = {}
    for k in range(len(ctrl)):
        next_ctrl[ctrl[k]] = ctrl[k + 1] if k + 1 < len(ctrl) else None

    pid = 0
    owner = None
    out = []
    for i in range(n):
        new = i == 0 or period[i] != period[i - 1]
        is_restart = has_value(restart[i])
        if not new and is_restart:
            new = True
        elif not new and kind[i] in CTRL and team[i] != owner:
            j = next_ctrl.get(i)
            run = 1
            if j is not None and team[j] == team[i] and period[j] == period[i]:
                run = 2
            new = kind[i] == "shot" or run >= 2
        if new:
            pid += 1
            if kind[i] in CTRL or is_restart:
                owner = team[i]
        out.append(pid)
    return out


def play_pattern(restart):
    if restart in (None, ""):
        return "Regular Play"
    return RESTART.get(str(restart).lower(), "Regular Play")


def to_event(i, r, g, sx, sy, owner, pattern):
    # one CSV row -> one StatsBomb-style event
    kind = r.event_type
    e = {
        "index": i,
        "period": int(r.period),
        "minute": int(r.minute),
        "second": int(r.second),
        "team": {"name": r.team},
        "possession": int(r._pid),
        "possession_team": {"name": owner},
        "type": {"name": TYPE.get(kind, DEFT.get(kind, "Other"))},
        "location": [None, None] if pd.isna(r.x) else [float(r.x) * sx, float(r.y) * sy],
        "play_pattern": {"name": pattern},
    }
    cols = g.columns

    if kind in ("pass", "carry") and "end_x" in cols and pd.notna(r.end_x):
        end = [float(r.end_x) * sx, float(r.end_y) * sy]
        if kind == "pass":
            if "pass_length" in cols and pd.notna(r.pass_length):
                length = float(r.pass_length)
            else:
                length = float(np.hypot(end[0] - e["location"][0], end[1] - e["location"][1]))
            e["pass"] = {"end_location": end, "length": length}
        else:
            e["carry"] = {"end_location": end}
    elif kind == "pass":  # no end point: zero-length pass
        e["pass"] = {"end_location": e["location"], "length": 0.0}
    elif kind == "carry":
        e["carry"] = {"end_location": e["location"]}

    if kind == "shot":
        goal = "shot_goal" in cols and r.shot_goal == 1
        e["shot"] = {"outcome": {"name": "Goal" if goal else "Other"}}
        if "xg" in cols and pd.notna(r.xg):
            e["shot"]["statsbomb_xg"] = float(r.xg)
    if kind == "pass" and "pass_outcome" in cols and str(r.pass_outcome).strip().lower() == "incomplete":
        e["pass"]["outcome"] = {"name": "Incomplete"}
    if "player" in cols and pd.notna(r.player):
        e["player"] = {"name": str(r.player)}
    if kind == "pass" and "recipient" in cols and pd.notna(r.recipient):
        e["pass"]["recipient"] = {"name": str(r.recipient)}
    return e


def convert(csv_path, out_dir, coords="100", provider=None):
    problems, d = validate(pd.read_csv(csv_path))
    for p in problems:
        print(p)
    if d is None:
        sys.exit(1)
    if coords == "100":
        sx, sy = 1.2, 0.8  # 0-100 -> 120 x 80
    else:
        sx, sy = 1.0, 1.0
    d = d.sort_values(["match_id", "period", "minute", "second"], kind="stable").reset_index(drop=True)
    os.makedirs(f"{out_dir}/matches", exist_ok=True)
    os.makedirs(f"{out_dir}/ev", exist_ok=True)

    matches = []
    for mid, g in d.groupby("match_id", sort=False):
        g = g.reset_index(drop=True)
        if "possession_id" in g.columns and g.possession_id.notna().all():
            g["_pid"] = g.possession_id.astype(int).values
        else:
            g["_pid"] = new_possessions(g)
        if "restart" in g.columns:
            restart = g["restart"].astype(object).where(g["restart"].notna(), None)
        else:
            restart = pd.Series([None] * len(g))

        # first row of each possession, and the team of its first action with the ball
        first = {}
        owner = {}
        for i, r in g.iterrows():
            first.setdefault(r._pid, i)
            if r.event_type in CTRL:
                owner.setdefault(r._pid, r.team)

        events = []
        for i, r in g.iterrows():
            pattern = play_pattern(restart.iloc[first[r._pid]])
            e = to_event(i, r, g, sx, sy, owner.get(r._pid, r.team), pattern)
            events.append(e)
            if r.event_type == "own_goal":
                # as StatsBomb does: the other team gets an 'Own Goal For' at the same moment
                other = r.away_team if r.team == r.home_team else r.home_team
                og = dict(e, index=i + 0.5, team={"name": other}, type={"name": "Own Goal For"})
                og.pop("player", None)
                events.append(og)
        json.dump(events, open(f"{out_dir}/ev/{mid}.json", "w", encoding="utf-8"))

        r0 = g.iloc[0]
        match = {
            "match_id": int(mid) if str(mid).isdigit() else mid,
            "match_date": str(r0.match_date),
            "home_team": {"home_team_name": r0.home_team},
            "away_team": {"away_team_name": r0.away_team},
        }
        if provider:
            match["data_provider"] = provider
        matches.append(match)
    json.dump(matches, open(f"{out_dir}/matches/generic.json", "w", encoding="utf-8"))
    print(f"convertite {len(matches)} partite in {out_dir}")
    return len(problems)


if __name__ == "__main__":
    args = [x for x in sys.argv[1:] if not x.startswith("--")]
    flags = [x for x in sys.argv[1:] if x.startswith("--")]
    if len(args) < 1:
        sys.exit(__doc__)
    if "--validate-only" in flags:
        problems, _ = validate(pd.read_csv(args[0]))
        print("\n".join(problems) if problems else "nessun problema trovato")
        sys.exit(0)
    if len(args) < 2:
        sys.exit(__doc__)
    provider = None
    for x in flags:
        if x.startswith("--provider="):
            provider = x.split("=", 1)[1]
    coords = "100"
    if "--coords" in flags or any("120x80" in x for x in sys.argv):
        coords = "120x80"
    convert(args[0], args[1], coords, provider)
