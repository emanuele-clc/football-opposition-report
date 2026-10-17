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
- linked: for the opponent-pressing split, balls lost in the own half, own-half pass completion and passes under pressure share events with the
  opponent PPDA used to form the groups (our own-half passes, their duels and interceptions), so part of those differences holds by construction."""
import sys, json
import numpy as np
MF, TEAM = sys.argv[1], sys.argv[2]; BASE = sys.argv[3] if len(sys.argv) > 3 else "."
PPDA_ACT = ("Duel", "Interception", "Foul Committed"); MIN_N = 6
METRICS = [("xg_for", "xG created", "num2", "more is better"), ("xg_against", "xG conceded", "num2", "less is better"), ("shots_for", "Shots", "num", "more is better"),
           ("shots_against", "Shots conceded", "num", "less is better"), ("lost_own_half", "Balls lost in own half", "num", "less is better"),
           ("under_pressure_share", "Own-half passes under pressure", "pct", "context"), ("own_half_completion", "Own-half pass completion", "pct", "more is better"),
           ("pressures", "Own pressures", "num", "context"), ("points", "Points per match", "num2", "more is better")]

def per_match():
    ms = sorted([g for g in json.load(open(MF, encoding="utf-8")) if TEAM in (g["home_team"]["home_team_name"], g["away_team"]["away_team_name"])], key=lambda g: g["match_date"])
    out = []
    for g in ms:
        home = g["home_team"]["home_team_name"] == TEAM; opp = g["away_team"]["away_team_name"] if home else g["home_team"]["home_team_name"]
        ev = json.load(open(f"{BASE}/ev/{g['match_id']}.json", encoding="utf-8")); us = [e for e in ev if e["team"]["name"] == TEAM]; them = [e for e in ev if e["team"]["name"] != TEAM]
        loc = lambda e: e.get("location") or [None, None]
        my_pass_60 = sum(1 for e in us if e["type"]["name"] == "Pass" and loc(e)[0] is not None and loc(e)[0] < 72)
        opp_act = sum(1 for e in them if e["type"]["name"] in PPDA_ACT and loc(e)[0] is not None and loc(e)[0] >= 48)
        own_half = [e for e in us if e["type"]["name"] == "Pass" and loc(e)[0] is not None and loc(e)[0] < 60]
        lost = sum(1 for e in us if loc(e)[0] is not None and loc(e)[0] < 60 and ((e["type"]["name"] == "Pass" and "outcome" in e["pass"]) or e["type"]["name"] in ("Dispossessed", "Miscontrol")))
        xi = {e["team"]["name"]: e["tactics"]["formation"] for e in ev if e["type"]["name"] == "Starting XI"}
        f_opp = str(xi.get(opp, "")); gf, ga = (g["home_score"], g["away_score"]) if home else (g["away_score"], g["home_score"])
        sh = lambda es: [e for e in es if e["type"]["name"] == "Shot"]
        out.append(dict(match=g["match_id"], date=g["match_date"], opponent=opp, venue="home" if home else "away", score=f"{gf}-{ga}",
                        formation=str(xi.get(TEAM, "")), opp_formation=f_opp, opp_back_line=("back four" if f_opp[:1] == "4" else "back three/five" if f_opp[:1] in ("3", "5") else "unknown"),
                        opp_ppda=my_pass_60 / max(opp_act, 1), xg_for=float(sum(e["shot"].get("statsbomb_xg", 0) or 0 for e in sh(us))),
                        xg_against=float(sum(e["shot"].get("statsbomb_xg", 0) or 0 for e in sh(them))), shots_for=len(sh(us)), shots_against=len(sh(them)), lost_own_half=lost,
                        under_pressure_share=sum(1 for e in own_half if e.get("under_pressure")) / max(len(own_half), 1),
                        own_half_completion=sum(1 for e in own_half if "outcome" not in e["pass"]) / max(len(own_half), 1),
                        pressures=sum(1 for e in us if e["type"]["name"] == "Pressure"), points=3 if gf > ga else 1 if gf == ga else 0))
    return out

def compare(rows, key_a, key_b, label, linked=()):
    A = [r for r in rows if key_a(r)]; B = [r for r in rows if key_b(r)]; rng = np.random.default_rng(0); res = []
    for m, lab, unit, direction in METRICS:
        a = np.array([r[m] for r in A], float); b = np.array([r[m] for r in B], float)
        if len(a) == 0 or len(b) == 0: continue
        d = [rng.choice(a, len(a)).mean() - rng.choice(b, len(b)).mean() for _ in range(2000)]; lo, hi = np.percentile(d, [2.5, 97.5])
        verdict = "small group" if min(len(a), len(b)) < MIN_N else ("clear" if lo > 0 or hi < 0 else "uncertain")
        res.append(dict(id=m, label=lab, unit=unit, direction=direction, linked=m in linked, a=float(a.mean()), b=float(b.mean()), diff=float(a.mean() - b.mean()), ci=[float(lo), float(hi)], verdict=verdict))
    return dict(label=label, n_a=len(A), n_b=len(B), metrics=res)

if __name__ == "__main__":
    rows = per_match()
    if not any(r["pressures"] for r in rows): sys.exit(f"No StatsBomb-style defensive events for {TEAM}: the matchup sheet needs Pressure/Duel events and formations.")
    med = float(np.median([r["opp_ppda"] for r in rows]))
    for r in rows: r["opp_press"] = "high press" if r["opp_ppda"] <= med else "lower press"
    splits = {"opp_press": dict(compare(rows, lambda r: r["opp_press"] == "high press", lambda r: r["opp_press"] == "lower press", "Opponent pressing", linked=("lost_own_half", "own_half_completion", "under_pressure_share")),
                                groups=["against a high press", "against a lower press"], rule=f"opponent PPDA in that match at or below the median ({med:.1f}) = high press"),
              "back_line": dict(compare(rows, lambda r: r["opp_back_line"] == "back three/five", lambda r: r["opp_back_line"] == "back four", "Opponent back line"),
                                groups=["against a back three/five", "against a back four"], rule="first digit of the opponent's starting formation"),
              "venue": dict(compare(rows, lambda r: r["venue"] == "home", lambda r: r["venue"] == "away", "Venue"), groups=["at home", "away"], rule="home or away")}
    res = {"team": TEAM, "matches": len(rows), "note": "DESCRIPTIVE: differences in past matches, not recommendations; groups differ in many ways at once.",
           "min_group": MIN_N, "median_opp_ppda": med, "formations_used": sorted({r["formation"] for r in rows}), "splits": splits, "per_match": rows}
    json.dump(res, open(f"{BASE}/matchups_{TEAM.replace(' ', '_')}.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    for k, s in splits.items():
        print(f"[{TEAM}] {s['label']}: {s['n_a']} vs {s['n_b']} matches | clear: {[m['label'] + (' (linked)' if m['linked'] else '') for m in s['metrics'] if m['verdict'] == 'clear']}")
