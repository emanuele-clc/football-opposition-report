"""Key players and goal timeline of a team, from the StatsBomb events. Descriptive.
Usage:  python keyplayers.py <matches.json> "<Team>" [data_dir=.]   ->  keyplayers_<Team>.json (read by the app, section Game plan)
"""

import sys, os, json

# From the events (needs <data>/ev): key players and when goals and chances come. Definitions fixed before looking at the output.
# - builds through: completed open-play passes received in the own half (end x < 60); set-piece passes (corner, free kick, throw-in, goal kick, kick-off) excluded.
# - into the final third: completed passes and carries that start before x = 80 and end at x >= 80.
# - shots and xG: all shots by the player, penalties included (StatsBomb xG).
# - set-piece takers: corners taken; free kicks taken in the opponent half (passes and direct shots).
# - loses the ball in own half: incomplete passes, Dispossessed and Miscontrol at x < 60.
# Per match = per match in which the player has at least one event. Top 3 by total.
# - timeline: goals (shots scored + own goals in their favour) and xG for and against by 15-minute slot; stoppage time goes to the slot before
#   the half ends (45+ in 30-45, 90+ in 75-90); extra time (if played) in its own slot 90-120, the penalty shootout left out.
# - goals: every goal scored and conceded (shots scored + own goals), with scorer, xG, shot location (team view: goals scored towards x = 120, conceded
#   towards x = 0) and origin = StatsBomb play pattern of the possession (how it started: regular play, counter, corner, free kick, throw-in, goal kick,
#   keeper, kick-off, other); penalties and own goals separately. Origin is StatsBomb's label, not a definition of ours.
ORIGIN = {
    "Regular Play": "Open play",
    "From Counter": "Counter-attack",
    "From Corner": "Corner",
    "From Free Kick": "Free kick",
    "From Throw In": "Throw-in",
    "From Goal Kick": "Goal kick",
    "From Keeper": "Keeper",
    "From Kick Off": "Kick-off",
    "Other": "Other",
}
# - under pressure (own half, x < 60, 3 x 3 zones: x 0-20 / 20-40 / 40-60, y thirds of 0-80): open-play passes by the team; share made under pressure
#   (StatsBomb 'under_pressure' flag), completion under pressure and when free, share of long passes (30+ m) under pressure, and Dispossessed/Miscontrol
#   under pressure. Zones with fewer than 40 passes under pressure are marked 'few'.
# - fouls (own half, same 3 x 3 zones): fouls committed by the team (StatsBomb 'Foul Committed', handballs excluded), with the yellow and red cards given for them.
# - starters: the team's starting eleven in each match (StatsBomb 'Starting XI'), for the 'without a player' comparison in the app.
ZX, ZY = (20, 40, 60), (80 / 3, 160 / 3, 80)
SET = {"Corner", "Free Kick", "Throw-in", "Goal Kick", "Kick Off"}
SLOTS = ["0-15", "15-30", "30-45", "45-60", "60-75", "75-90"]
ET = "90-120"  # extra time (periods 3-4; the shootout, period 5, is not a goal); slot written only if the team played extra time

ROLES = [
    ("buildup", "Builds through", "passes received in own half",
     "Who the build-up goes through: pressing or marking them may disrupt it."),
    ("final_third", "Breaks the lines", "passes and carries into the final third",
     "Who moves the ball into the final third: watch how they receive."),
    ("xg", "Main threat", "xG from shots", "Who the chances fall to (penalties included)."),
    ("corners", "Takes corners", "corners taken", "Check their deliveries in Set pieces."),
    ("free_kicks", "Takes free kicks", "free kicks in the opponent half", "Direct and indirect free kicks."),
    ("losses", "Loses the ball in own half", "balls lost in own half",
     "Where pressure may pay. Players who have the ball most also lose it most (a goalkeeper here is mostly long balls that do not arrive): read it with Builds through."),
]


def short(name):
    """Full name as in the data: cutting to first + last name gets Spanish double surnames wrong (Alejandro Grimaldo García -> 'Alejandro García')."""
    return name


def zone(loc):
    """3 x 3 own-half zone (i, j) of a location, None outside the own half."""
    if not loc or loc[0] >= 60:
        return None
    i = next(i for i, v in enumerate(ZX) if loc[0] < v)
    j = next(j for j, v in enumerate(ZY) if min(loc[1], 80) <= v)  # a few events lie just off the pitch (y 80.4)
    return i, j


def zone_box(i, j):
    return {"x0": [0, 20, 40][i], "x1": ZX[i], "y0": [0, ZY[0], ZY[1]][j], "y1": ZY[j]}


def time_slot(e):
    minute = e["minute"]
    if e["period"] in (3, 4):
        return ET
    if e["period"] == 1:
        minute = min(minute, 44)
    else:
        minute = min(max(minute, 45), 89)
    return SLOTS[minute // 15]


def shot_xg(e):
    return e["shot"].get("statsbomb_xg", 0) or 0


def goal_origin(e):
    if e["type"]["name"] == "Own Goal For":
        return "Own goal"
    if e.get("shot", {}).get("type", {}).get("name", "") == "Penalty":
        return "Penalty"
    return ORIGIN.get(e.get("play_pattern", {}).get("name", ""), "Other")


def match_goals(ev, m, team_name, meta):
    """Every goal of the match (both sides), with where the possession started."""
    start = {}
    for e in ev:
        if e.get("possession") is not None and (e.get("period"), e["possession"]) not in start:
            start[(e.get("period"), e["possession"])] = e
    opp = next((e["team"]["name"] for e in ev if e["team"]["name"] != team_name), "")
    info = (meta or {}).get(m, {})

    goals = []
    for e in ev:
        t = e["type"]["name"]
        is_goal = t == "Shot" and e["shot"]["outcome"]["name"] == "Goal"
        if not (is_goal or t == "Own Goal For") or e.get("period") not in (1, 2, 3, 4):
            continue
        us = e["team"]["name"] == team_name
        loc = e.get("location") or [None, None]
        if loc[0] is not None and not us:
            loc = [120 - loc[0], 80 - loc[1]]
        st = start.get((e.get("period"), e.get("possession")), e)
        goals.append({
            "side": "for" if us else "against",
            "match": m,
            "date": info.get("date"),
            "opponent": info.get("opponent", opp),
            "half": e["period"],
            "minute": e["minute"],
            "second": e["second"],
            "start_minute": st["minute"],
            "start_second": st["second"],
            "possession": e.get("possession"),
            "scorer": e.get("player", {}).get("name", "own goal") if t == "Shot" else "own goal",
            "xg": round(shot_xg(e), 3) if t == "Shot" else None,
            "origin": goal_origin(e),
            "body": e.get("shot", {}).get("body_part", {}).get("name"),
            "x": loc[0],
            "y": loc[1],
        })
    return goals


def events_view(team_name, match_ids, ev_dir, meta=None):
    counts = {k: {} for k in ("buildup", "final_third", "shots", "xg", "corners", "free_kicks", "losses")}
    played, shirt, pos, starters = {}, {}, {}, {}
    timeline = {s: {"goals_for": 0, "goals_against": 0, "xg_for": 0.0, "xg_against": 0.0} for s in SLOTS + [ET]}
    extra_time = False
    goals = []
    zones = [(i, j) for i in range(3) for j in range(3)]
    press = {z: {"passes": 0, "under_pressure": 0, "up_ok": 0, "free_ok": 0, "up_long": 0, "up_lost": 0} for z in zones}
    fouls = {z: {"fouls": 0, "cards": 0} for z in zones}

    def add(k, p, v=1):
        counts[k][p] = counts[k].get(p, 0) + v

    for m in match_ids:
        ev = json.load(open(os.path.join(ev_dir, f"{m}.json"), encoding="utf-8"))
        goals += match_goals(ev, m, team_name, meta)
        seen = set()
        for e in ev:
            t = e["type"]["name"]
            us = e["team"]["name"] == team_name
            loc = e.get("location")
            if loc and loc[0] is None:
                loc = None  # converted data (generic CSV) writes [None, None] for events without a position

            if t == "Starting XI" and us:
                starters[str(m)] = [pl["player"]["name"] for pl in e["tactics"]["lineup"]]
            if t in ("Starting XI", "Tactical Shift") and us:
                for pl in e.get("tactics", {}).get("lineup", []):
                    shirt[pl["player"]["name"]] = pl.get("jersey_number")
                    pos[pl["player"]["name"]] = pl.get("position", {}).get("name")

            if e.get("period") in (1, 2, 3, 4):
                extra_time = extra_time or e["period"] > 2
                slot = timeline[time_slot(e)]
                side = "for" if us else "against"
                if t == "Shot":
                    slot[f"xg_{side}"] += shot_xg(e)
                    if e["shot"]["outcome"]["name"] == "Goal":
                        slot[f"goals_{side}"] += 1
                if t == "Own Goal For":
                    slot[f"goals_{side}"] += 1

            if not us or "player" not in e:
                continue
            p = e["player"]["name"]
            seen.add(p)

            # own-half zones: passes under pressure and fouls
            z = zone(loc)
            if z and t == "Pass" and e["pass"].get("type", {}).get("name") not in SET:
                zz = press[z]
                zz["passes"] += 1
                good = "outcome" not in e["pass"]
                if e.get("under_pressure"):
                    zz["under_pressure"] += 1
                    zz["up_ok"] += good
                    zz["up_long"] += e["pass"].get("length", 0) >= 30
                    zz["up_lost"] += not good
                else:
                    zz["free_ok"] += good
            if z and t in ("Dispossessed", "Miscontrol") and e.get("under_pressure"):
                press[z]["up_lost"] += 1
            if z and t == "Foul Committed" and e.get("foul_committed", {}).get("type", {}).get("name") != "Handball":
                fouls[z]["fouls"] += 1
                fouls[z]["cards"] += "card" in e.get("foul_committed", {})

            # player counts
            if t == "Pass":
                pa = e["pass"]
                ok = "outcome" not in pa
                kind = pa.get("type", {}).get("name")
                if ok and kind not in SET and pa.get("recipient") and pa["end_location"][0] < 60:
                    add("buildup", pa["recipient"]["name"])
                if ok and loc and loc[0] < 80 <= pa["end_location"][0]:
                    add("final_third", p)
                if kind == "Corner":
                    add("corners", p)
                if kind == "Free Kick" and loc and loc[0] >= 60:
                    add("free_kicks", p)
                if not ok and loc and loc[0] < 60:
                    add("losses", p)
            elif t == "Carry" and loc and loc[0] < 80 <= e["carry"]["end_location"][0]:
                add("final_third", p)
            elif t == "Shot":
                add("shots", p)
                add("xg", p, shot_xg(e))
                if e["shot"].get("type", {}).get("name") == "Free Kick":
                    add("free_kicks", p)
            elif t in ("Dispossessed", "Miscontrol") and loc and loc[0] < 60:
                add("losses", p)

        for p in seen:
            played[p] = played.get(p, 0) + 1

    n = len(match_ids)

    def top(k):
        best = sorted(counts[k].items(), key=lambda x: -x[1])[:3]
        return [{
            "player": short(p),
            "full": p,
            "shirt": shirt.get(p),
            "keeper": pos.get(p) == "Goalkeeper",
            "total": round(v, 2),
            "matches": played.get(p, 0),
            "per_match": round(v / max(played.get(p, 1), 1), 2),
        } for p, v in best]

    foul_zones = []
    for (i, j), v in sorted(fouls.items()):
        foul_zones.append({**zone_box(i, j), **v, "per_match": round(v["fouls"] / max(n, 1), 3)})

    press_zones = []
    for (i, j), v in sorted(press.items()):
        press_zones.append({
            **zone_box(i, j),
            **v,
            "up_share": round(v["under_pressure"] / max(v["passes"], 1), 3),
            "up_completion": round(v["up_ok"] / max(v["under_pressure"], 1), 3),
            "free_completion": round(v["free_ok"] / max(v["passes"] - v["under_pressure"], 1), 3),
            "up_long_share": round(v["up_long"] / max(v["under_pressure"], 1), 3),
            "few": v["under_pressure"] < 40,
        })

    n_up = sum(v["under_pressure"] for v in press.values())
    n_free = sum(v["passes"] - v["under_pressure"] for v in press.values())
    press_total = {
        "passes": n_up,
        "completion": round(sum(v["up_ok"] for v in press.values()) / max(n_up, 1), 3),
        "free_completion": round(sum(v["free_ok"] for v in press.values()) / max(n_free, 1), 3),
    }

    by_origin = {}
    for side in ("for", "against"):
        origins = sorted({g["origin"] for g in goals if g["side"] == side})
        by_origin[side] = {o: sum(1 for g in goals if g["side"] == side and g["origin"] == o) for o in origins}

    slots = []
    for s in SLOTS + ([ET] if extra_time else []):
        row = {"slot": s}
        for k, v in timeline[s].items():
            row[k] = round(v / max(n, 1), 3) if k.startswith("xg") else v
        slots.append(row)

    return {
        "matches": n,
        "players": [{"id": k, "role": r, "unit": u, "note": note, "top": top(k)} for k, r, u, note in ROLES],
        "goals": goals,
        "starters": starters,
        "fouls": foul_zones,
        "under_pressure": press_zones,
        "under_pressure_total": press_total,
        "goals_by_origin": by_origin,
        "timeline": slots,
    }


if __name__ == "__main__":
    MF, TEAM = sys.argv[1], sys.argv[2]
    BASE = sys.argv[3] if len(sys.argv) > 3 else "."
    matches = [g for g in json.load(open(MF, encoding="utf-8"))
               if TEAM in (g["home_team"]["home_team_name"], g["away_team"]["away_team_name"])]
    matches.sort(key=lambda g: g["match_date"])
    meta = {}
    for g in matches:
        home = g["home_team"]["home_team_name"] == TEAM
        opponent = g["away_team"]["away_team_name"] if home else g["home_team"]["home_team_name"]
        meta[g["match_id"]] = {"date": g["match_date"], "opponent": opponent}

    res = {"team": TEAM, **events_view(TEAM, [g["match_id"] for g in matches], os.path.join(BASE, "ev"), meta)}

    # Data without xG or the under-pressure flag (e.g. Wyscout via the generic CSV): drop what it cannot give instead of
    # writing zeros that the app would rank as real values.
    unavailable = []
    xg_role = next((p for p in res["players"] if p["id"] == "xg"), None)
    if xg_role and xg_role["top"] and not any(t["total"] for t in xg_role["top"]):
        res["players"] = [p for p in res["players"] if p["id"] != "xg"]
        unavailable.append("xG")
    if res["under_pressure_total"]["passes"] == 0:
        res["under_pressure_total"]["completion"] = None
        res["under_pressure"] = []
        unavailable.append("passes under pressure")
    if unavailable:
        res["unavailable"] = unavailable

    name = f"keyplayers_{TEAM.replace(' ', '_')}.json"
    json.dump(res, open(os.path.join(BASE, name), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    goals_for = sum(s["goals_for"] for s in res["timeline"])
    goals_against = sum(s["goals_against"] for s in res["timeline"])
    print("saved", name, "| goals", goals_for, "-", goals_against)
