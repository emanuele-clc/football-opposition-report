"""Matchup sheet: how the team's numbers differed in past matches depending on the opponent (pressing intensity, back line) and on home/away.
DESCRIPTIVE ONLY: it shows what happened, it does not say which formation or style would work. Groups are small, matches differ in many ways at once
(opponent strength, score, venue), so a difference here is a hint to check on video, never a recommendation.
Usage:  python matchups.py <matches.json> "<Team>" [data_dir=.]   ->  matchups_<Team>.json (needs StatsBomb-style events: Pressure, Duel, formations)
Definitions (fixed before looking at any team; locations on each team's own attacking direction, 0-120 x 0-80):
- opponent pressing in that match: opponent PPDA = our passes in our own 60% (x < 72) / opponent Duels, Interceptions and Fouls Committed at x >= 48.
  Split at the median over the team's matches: 'high press' = PPDA at or below the median (fewer passes allowed), 'lower press' = above.
- opponent back line: first digit of the opponent's starting formation (StatsBomb 'Starting XI'): 4 = back four, 3 or 5 = back three/five.
- venue: home or away.
- per-match outcomes of the team: xG for and against (StatsBomb xG, penalties included), shots for and against, balls lost in the own half per match
  (incomplete passes, Dispossessed and Miscontrol with x < 60), share of own-half passes made under pressure and their completion rate, own pressures, points (3/1/0).
- comparison: difference of the group means; 95% bootstrap interval resampling matches within each group (2,000 draws, seed 0).
  'clear' = interval excludes 0 and both groups have at least 6 matches; 'small group' = a group has fewer than 6 matches; otherwise 'uncertain'.
  With about 10 comparisons per split, one 'clear' result in 20 is expected by chance even with no real difference.
- other providers (added 29 Oct 2026, definitions unchanged): with events converted from the generic CSV (e.g. Wyscout) there are no
  pressures, no under-pressure flag, no xG and no starting formations. The measures that need them are left out (listed in 'unavailable'),
  never filled with zeros, and so is the back-line split. Points need the score in the match list; without it they are left out too.
- linked: for the opponent-pressing split, balls lost in the own half, own-half pass completion and passes under pressure share events with the
  opponent PPDA used to form the groups (our own-half passes, their duels and interceptions), so part of those differences holds by construction."""

import sys, json
import numpy as np

MF, TEAM = sys.argv[1], sys.argv[2]
BASE = sys.argv[3] if len(sys.argv) > 3 else "."
PPDA_ACT = ("Duel", "Interception", "Foul Committed")
MIN_N = 6

# What this data has (set while reading the matches). Measures that need something missing are dropped.
HAS = {"xg": False, "pressure": False, "formation": False, "score": False}
NEEDS = {
    "xg_for": "xg",
    "xg_against": "xg",
    "under_pressure_share": "pressure",
    "pressures": "pressure",
    "points": "score",
}
WHY = {"xg": "no xG in this data", "pressure": "no pressures in this data", "score": "no score in the match list"}
METRICS = [
    ("xg_for", "xG created", "num2", "more is better"),
    ("xg_against", "xG conceded", "num2", "less is better"),
    ("shots_for", "Shots", "num", "more is better"),
    ("shots_against", "Shots conceded", "num", "less is better"),
    ("lost_own_half", "Balls lost in own half", "num", "less is better"),
    ("under_pressure_share", "Own-half passes under pressure", "pct", "context"),
    ("own_half_completion", "Own-half pass completion", "pct", "more is better"),
    ("pressures", "Own pressures", "num", "context"),
    ("points", "Points per match", "num2", "more is better"),
]


def available(metric):
    return HAS.get(NEEDS.get(metric, ""), True)


def x_of(e):
    loc = e.get("location")
    return loc[0] if loc else None


def is_type(e, name):
    return e["type"]["name"] == name


def total_xg(shots):
    return float(sum(e["shot"].get("statsbomb_xg", 0) or 0 for e in shots))


def back_line(formation):
    if formation[:1] == "4":
        return "back four"
    if formation[:1] in ("3", "5"):
        return "back three/five"
    return "unknown"


def points(gf, ga):
    if gf > ga:
        return 3
    return 1 if gf == ga else 0


def one_match(g):
    home = g["home_team"]["home_team_name"] == TEAM
    opp = g["away_team"]["away_team_name"] if home else g["home_team"]["home_team_name"]
    ev = json.load(open(f"{BASE}/ev/{g['match_id']}.json", encoding="utf-8"))
    us = [e for e in ev if e["team"]["name"] == TEAM]
    them = [e for e in ev if e["team"]["name"] != TEAM]

    my_pass_60 = sum(1 for e in us if is_type(e, "Pass") and x_of(e) is not None and x_of(e) < 72)
    opp_act = sum(1 for e in them if e["type"]["name"] in PPDA_ACT and x_of(e) is not None and x_of(e) >= 48)
    own_half = [e for e in us if is_type(e, "Pass") and x_of(e) is not None and x_of(e) < 60]
    lost = 0
    for e in us:
        if x_of(e) is None or x_of(e) >= 60:
            continue
        if (is_type(e, "Pass") and "outcome" in e["pass"]) or e["type"]["name"] in ("Dispossessed", "Miscontrol"):
            lost += 1

    xi = {e["team"]["name"]: e["tactics"]["formation"] for e in ev if is_type(e, "Starting XI")}
    opp_formation = str(xi.get(opp, ""))
    scored = "home_score" in g and "away_score" in g
    if scored:
        gf, ga = (g["home_score"], g["away_score"]) if home else (g["away_score"], g["home_score"])
    else:
        gf = ga = None

    HAS["xg"] |= any("statsbomb_xg" in e.get("shot", {}) for e in ev if is_type(e, "Shot"))
    HAS["pressure"] |= any(is_type(e, "Pressure") for e in ev)
    HAS["formation"] |= bool(xi)
    HAS["score"] |= scored

    our_shots = [e for e in us if is_type(e, "Shot")]
    their_shots = [e for e in them if is_type(e, "Shot")]
    n_own = max(len(own_half), 1)
    return {
        "match": g["match_id"],
        "date": g["match_date"],
        "opponent": opp,
        "venue": "home" if home else "away",
        "score": f"{gf}-{ga}" if scored else "",
        "formation": str(xi.get(TEAM, "")),
        "opp_formation": opp_formation,
        "opp_back_line": back_line(opp_formation),
        "opp_ppda": my_pass_60 / max(opp_act, 1),
        "xg_for": total_xg(our_shots),
        "xg_against": total_xg(their_shots),
        "shots_for": len(our_shots),
        "shots_against": len(their_shots),
        "lost_own_half": lost,
        "under_pressure_share": sum(1 for e in own_half if e.get("under_pressure")) / n_own,
        "own_half_completion": sum(1 for e in own_half if "outcome" not in e["pass"]) / n_own,
        "pressures": sum(1 for e in us if is_type(e, "Pressure")),
        "points": points(gf, ga) if scored else None,
    }


def per_match():
    matches = [g for g in json.load(open(MF, encoding="utf-8"))
               if TEAM in (g["home_team"]["home_team_name"], g["away_team"]["away_team_name"])]
    matches.sort(key=lambda g: g["match_date"])
    return [one_match(g) for g in matches]


def compare(rows, in_a, in_b, label, linked=()):
    """Mean of group A minus mean of group B for each measure, with a bootstrap interval inside each group."""
    A = [r for r in rows if in_a(r)]
    B = [r for r in rows if in_b(r)]
    rng = np.random.default_rng(0)  # one generator for all measures of this split, in METRICS order
    res = []
    for m, lab, unit, direction in METRICS:
        if not available(m):
            continue
        a = np.array([r[m] for r in A], float)
        b = np.array([r[m] for r in B], float)
        if len(a) == 0 or len(b) == 0:
            continue
        d = [rng.choice(a, len(a)).mean() - rng.choice(b, len(b)).mean() for _ in range(2000)]
        lo, hi = np.percentile(d, [2.5, 97.5])
        if min(len(a), len(b)) < MIN_N:
            verdict = "small group"
        elif lo > 0 or hi < 0:
            verdict = "clear"
        else:
            verdict = "uncertain"
        res.append({
            "id": m,
            "label": lab,
            "unit": unit,
            "direction": direction,
            "linked": m in linked,
            "a": float(a.mean()),
            "b": float(b.mean()),
            "diff": float(a.mean() - b.mean()),
            "ci": [float(lo), float(hi)],
            "verdict": verdict,
        })
    return {"label": label, "n_a": len(A), "n_b": len(B), "metrics": res}


if __name__ == "__main__":
    rows = per_match()
    # opp_ppda != opp_ppda is the NaN test
    if not any(r["opp_ppda"] != r["opp_ppda"] or r["opp_ppda"] > 0 for r in rows) or not any(r["shots_for"] for r in rows):
        sys.exit(f"No usable events for {TEAM}: the matchup sheet needs passes, shots and defensive actions.")
    for r in rows:  # measures this data cannot give are removed, not left at zero
        for m, need in NEEDS.items():
            if not HAS[need]:
                r[m] = None

    med = float(np.median([r["opp_ppda"] for r in rows]))
    for r in rows:
        r["opp_press"] = "high press" if r["opp_ppda"] <= med else "lower press"

    splits = {}
    splits["opp_press"] = compare(
        rows,
        lambda r: r["opp_press"] == "high press",
        lambda r: r["opp_press"] == "lower press",
        "Opponent pressing",
        linked=("lost_own_half", "own_half_completion", "under_pressure_share"),
    )
    splits["opp_press"]["groups"] = ["against a high press", "against a lower press"]
    splits["opp_press"]["rule"] = f"opponent PPDA in that match at or below the median ({med:.1f}) = high press"
    if HAS["formation"]:
        splits["back_line"] = compare(
            rows,
            lambda r: r["opp_back_line"] == "back three/five",
            lambda r: r["opp_back_line"] == "back four",
            "Opponent back line",
        )
        splits["back_line"]["groups"] = ["against a back three/five", "against a back four"]
        splits["back_line"]["rule"] = "first digit of the opponent's starting formation"
    splits["venue"] = compare(rows, lambda r: r["venue"] == "home", lambda r: r["venue"] == "away", "Venue")
    splits["venue"]["groups"] = ["at home", "away"]
    splits["venue"]["rule"] = "home or away"

    res = {
        "team": TEAM,
        "matches": len(rows),
        "note": "DESCRIPTIVE: differences in past matches, not recommendations; groups differ in many ways at once.",
        "min_group": MIN_N,
        "median_opp_ppda": med,
        "formations_used": sorted({r["formation"] for r in rows}) if HAS["formation"] else [],
        "splits": splits,
        "per_match": rows,
    }
    # Only for data without xG, pressures or formations (StatsBomb output unchanged).
    unavailable = [{"id": m, "label": lab, "why": WHY[NEEDS[m]]} for m, lab, *_ in METRICS if not available(m)]
    if not HAS["formation"]:
        unavailable.append({"id": "back_line", "label": "Opponent back line", "why": "no formations in this data"})
    if unavailable:
        res["unavailable"] = unavailable

    out = f"{BASE}/matchups_{TEAM.replace(' ', '_')}.json"
    json.dump(res, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    for s in splits.values():
        clear = [m["label"] + (" (linked)" if m["linked"] else "") for m in s["metrics"] if m["verdict"] == "clear"]
        print(f"[{TEAM}] {s['label']}: {s['n_a']} vs {s['n_b']} matches | clear: {clear}")
