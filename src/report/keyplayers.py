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
#   the half ends (45+ in 30-45, 90+ in 75-90); extra time left out.
SET = {"Corner", "Free Kick", "Throw-in", "Goal Kick", "Kick Off"}
SLOTS = ["0-15", "15-30", "30-45", "45-60", "60-75", "75-90"]


def short(name):
    """Full name as in the data: cutting to first + last name gets Spanish double surnames wrong (Alejandro Grimaldo García -> 'Alejandro García')."""
    return name


def events_view(team_name, match_ids, ev_dir):
    C = {k: {} for k in ("buildup", "final_third", "shots", "xg", "corners", "free_kicks", "losses")}
    played, shirt, pos = {}, {}, {}
    tl = {s: {"goals_for": 0, "goals_against": 0, "xg_for": 0.0, "xg_against": 0.0} for s in SLOTS}

    def add(k, p, v=1): C[k][p] = C[k].get(p, 0) + v
    for m in match_ids:
        ev = json.load(open(os.path.join(ev_dir, f"{m}.json"), encoding="utf-8")); seen = set()
        for e in ev:
            t = e["type"]["name"]; us = e["team"]["name"] == team_name; loc = e.get("location")
            if t in ("Starting XI", "Tactical Shift") and us:
                for pl in e.get("tactics", {}).get("lineup", []): shirt[pl["player"]["name"]] = pl.get("jersey_number"); pos[pl["player"]["name"]] = pl.get("position", {}).get("name")
            if e.get("period") in (1, 2):
                mi = e["minute"]; mi = min(mi, 44) if e["period"] == 1 else min(max(mi, 45), 89); slot = SLOTS[mi // 15]
                side = "for" if us else "against"
                if t == "Shot":
                    tl[slot][f"xg_{side}"] += e["shot"].get("statsbomb_xg", 0) or 0
                    if e["shot"]["outcome"]["name"] == "Goal": tl[slot][f"goals_{side}"] += 1
                if t == "Own Goal For": tl[slot][f"goals_{side}"] += 1
            if not us or "player" not in e: continue
            p = e["player"]["name"]; seen.add(p)
            if t == "Pass":
                pa = e["pass"]; ok = "outcome" not in pa; typ = pa.get("type", {}).get("name")
                if ok and typ not in SET and pa.get("recipient") and pa["end_location"][0] < 60: add("buildup", pa["recipient"]["name"])
                if ok and loc and loc[0] < 80 <= pa["end_location"][0]: add("final_third", p)
                if typ == "Corner": add("corners", p)
                if typ == "Free Kick" and loc and loc[0] >= 60: add("free_kicks", p)
                if not ok and loc and loc[0] < 60: add("losses", p)
            elif t == "Carry" and loc and loc[0] < 80 <= e["carry"]["end_location"][0]: add("final_third", p)
            elif t == "Shot":
                add("shots", p); add("xg", p, e["shot"].get("statsbomb_xg", 0) or 0)
                if e["shot"].get("type", {}).get("name") == "Free Kick": add("free_kicks", p)
            elif t in ("Dispossessed", "Miscontrol") and loc and loc[0] < 60: add("losses", p)
        for p in seen: played[p] = played.get(p, 0) + 1
    n = len(match_ids)

    def top(k):
        return [{"player": short(p), "full": p, "shirt": shirt.get(p), "keeper": pos.get(p) == "Goalkeeper", "total": round(v, 2), "matches": played.get(p, 0), "per_match": round(v / max(played.get(p, 1), 1), 2)}
                for p, v in sorted(C[k].items(), key=lambda x: -x[1])[:3]]
    roles = [("buildup", "Builds through", "passes received in own half", "Who the build-up goes through: pressing or marking them may disrupt it."),
             ("final_third", "Breaks the lines", "passes and carries into the final third", "Who moves the ball into the final third: watch how they receive."),
             ("xg", "Main threat", "xG from shots", "Who the chances fall to (penalties included)."),
             ("corners", "Takes corners", "corners taken", "Check their deliveries in Set pieces."),
             ("free_kicks", "Takes free kicks", "free kicks in the opponent half", "Direct and indirect free kicks."),
             ("losses", "Loses the ball in own half", "balls lost in own half", "Where pressure may pay. Players who have the ball most also lose it most (a goalkeeper here is mostly long balls that do not arrive): read it with Builds through.")]
    return {"matches": n, "players": [{"id": k, "role": r, "unit": u, "note": note, "top": top(k)} for k, r, u, note in roles],
            "timeline": [{"slot": s, **{k: (round(v / max(n, 1), 3) if k.startswith("xg") else v) for k, v in tl[s].items()}} for s in SLOTS]}


if __name__ == "__main__":
    MF, TEAM = sys.argv[1], sys.argv[2]; BASE = sys.argv[3] if len(sys.argv) > 3 else "."
    ms = sorted([g for g in json.load(open(MF, encoding="utf-8")) if TEAM in (g["home_team"]["home_team_name"], g["away_team"]["away_team_name"])], key=lambda g: g["match_date"])
    res = {"team": TEAM, **events_view(TEAM, [g["match_id"] for g in ms], os.path.join(BASE, "ev"))}
    json.dump(res, open(os.path.join(BASE, f"keyplayers_{TEAM.replace(' ', '_')}.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("saved", f"keyplayers_{TEAM.replace(' ', '_')}.json", "| goals", sum(s["goals_for"] for s in res["timeline"]), "-", sum(s["goals_against"] for s in res["timeline"]))
