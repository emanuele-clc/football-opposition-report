"""Wyscout public data (Pappalardo et al. 2019, Scientific Data, CC BY 4.0) -> the generic CSV of docs/data_format.md.
Usage: python wyscout_to_generic_csv.py <events_X.json> <matches_X.json> <teams.json> <players.json> "<Team>" <out.csv>
       Team = ALL: every match of the file (a whole league, needed for the league baselines).
How the events are mapped (checked on Serie A 2017/18):
- coordinates 0-100, the team of the event attacks left to right, small y = left: same as our CSV, used as they are.
- time: eventSec of each half -> minute from the start (second half from 45). Extra time and penalties are dropped.
- Pass -> pass, 'Acceleration' -> carry, Shot -> shot. Free kick sub-events give the restart: goal kick, throw-in, corner, free kick, penalty.
  Kick-off = first action of a half or after a goal. keeper = a goalkeeper pass right after his own save or 'leaving line'.
- goal = tag 101. Own goal = tag 102 -> an own_goal row for that player's team. A goal scored straight from a corner is a corner
  pass in this data, not a shot: left as it is (changing it would change shot and corner counts used in RQ1).
- recipient = player of the next event of the same team after an accurate pass (tag 1801). pass_outcome: 1801 complete, 1802 incomplete.
- Goal kicks start at a placeholder ((0,0) or (100,100)): moved to the six-yard box (5, 50), so their first-pass length is approximate.
- Defensive actions: interception = tag 1401 (an extra row if the event is a pass, carry or shot); duel = ground defending duel or
  air duel lost (tag 701); foul = the Foul sub-events in FOULS; clearance. No Ball Recovery and no Block in this data.
- No possession ids and no xG: generic_csv.py rebuilds the possessions (biased, see docs/data_format.md)."""

import csv, json, sys, codecs

FOULS = {"Foul", "Hand foul", "Late card foul", "Out of game foul", "Violent Foul"}
RESTARTS = {
    "Goal kick": "goal_kick",
    "Throw in": "throw_in",
    "Corner": "corner",
    "Free Kick": "free_kick",
    "Free kick cross": "free_kick",
    "Free kick shot": "free_kick",
    "Penalty": "penalty",
}
EMPTY = {"end_x": "", "end_y": "", "restart": "", "shot_goal": "", "recipient": "", "pass_outcome": ""}


def name(s):
    # some names are saved with \uXXXX escapes written out
    s = s or ""
    if "\\u" not in s:
        return s
    try:
        return json.loads('"' + s.replace('"', '\\"') + '"')
    except ValueError:
        return codecs.decode(s, "unicode_escape")


def event_type(en, sub, tags):
    if en == "Pass" or sub in ("Goal kick", "Throw in", "Corner", "Free Kick", "Free kick cross"):
        return "pass"
    if en == "Shot" or sub in ("Free kick shot", "Penalty"):
        return "shot"
    if sub == "Acceleration":
        return "carry"
    if 1401 in tags:
        return "interception"
    if en == "Duel" and sub == "Ground defending duel":
        return "duel"
    if en == "Duel" and sub == "Air duel" and 701 in tags:
        return "duel"
    if en == "Foul" and sub in FOULS:
        return "foul"
    if sub == "Clearance":
        return "clearance"
    return "other"


def main(ev_path, m_path, t_path, p_path, team, out):
    teams = {}
    for t in json.load(open(t_path, encoding="utf-8")):
        teams[t["wyId"]] = name(t["name"])
    players = {}
    for p in json.load(open(p_path, encoding="utf-8")):
        players[p["wyId"]] = name(p["shortName"])

    tid = None
    if team != "ALL":
        for k, v in teams.items():
            if v == team:
                tid = k
                break
        if tid is None:
            sys.exit(f"team not found in {t_path}: {team}")
    matches = {}
    for m in json.load(open(m_path, encoding="utf-8")):
        if tid is None or str(tid) in m["teamsData"]:
            matches[m["wyId"]] = m

    evs = []
    for e in json.load(open(ev_path, encoding="utf-8")):
        if e["matchId"] in matches and e["matchPeriod"] in ("1H", "2H"):
            evs.append(e)
    evs.sort(key=lambda e: (e["matchId"], e["matchPeriod"], e["eventSec"]))

    rows = []
    after_goal = False
    prev = None
    for i, e in enumerate(evs):
        m = matches[e["matchId"]]
        side = {}
        for k, v in m["teamsData"].items():
            side[v["side"]] = int(k)
        period = 1 if e["matchPeriod"] == "1H" else 2
        sec = e["eventSec"]
        minute = int(sec // 60)
        if period == 2:
            minute += 45
        new_half = prev is None or prev["matchId"] != e["matchId"] or prev["matchPeriod"] != e["matchPeriod"]
        tags = {t["id"] for t in e.get("tags", [])}
        en = e["eventName"]
        sub = e["subEventName"]
        etype = event_type(en, sub, tags)
        on_ball = etype in ("pass", "carry", "shot")

        # own goal on a defensive touch: the row becomes own_goal, and the touch is written again after it
        also = None
        if 102 in tags and not on_ball:
            if etype != "other":
                also = etype
            etype = "own_goal"

        restart = ""
        if en == "Free Kick":
            restart = RESTARTS.get(sub, "")
        if not restart and on_ball and (new_half or after_goal):
            restart = "kick_off"
        if not restart and etype == "pass" and prev is not None:
            same_player = prev["teamId"] == e["teamId"] and prev["playerId"] == e["playerId"]
            if same_player and prev["eventName"] in ("Save attempt", "Goalkeeper leaving line"):
                restart = "keeper"
        if on_ball:
            after_goal = False
        if 101 in tags or 102 in tags:
            after_goal = True

        positions = e.get("positions") or [{}]
        p0 = positions[0]
        p1 = positions[1] if len(positions) > 1 else {}
        if sub == "Goal kick" and (p0.get("x"), p0.get("y")) in ((0, 0), (100, 100)):
            p0 = {"x": 5, "y": 50}  # placeholder start: six-yard box

        # receiver: next event of the same team (within 5 events) after an accurate pass
        recipient = ""
        if etype == "pass" and 1801 in tags:
            for f in evs[i + 1 : i + 6]:
                if f["matchId"] == e["matchId"] and f["teamId"] == e["teamId"] and f["playerId"]:
                    if f["playerId"] != e["playerId"]:
                        recipient = players.get(f["playerId"], "")
                    break

        outcome = ""
        if etype == "pass":
            if 1801 in tags:
                outcome = "complete"
            elif 1802 in tags:
                outcome = "incomplete"
        moves = etype in ("pass", "carry")
        row = {
            "match_id": e["matchId"],
            "match_date": m["dateutc"][:10],
            "home_team": teams[side["home"]],
            "away_team": teams[side["away"]],
            "period": period,
            "minute": minute,
            "second": int(sec % 60),
            "team": teams.get(e["teamId"], str(e["teamId"])),
            "event_type": etype,
            "x": p0.get("x", ""),
            "y": p0.get("y", ""),
            "end_x": p1.get("x", "") if moves else "",
            "end_y": p1.get("y", "") if moves else "",
            "restart": restart,
            "shot_goal": int(101 in tags) if etype == "shot" else "",
            "player": players.get(e["playerId"], ""),
            "recipient": recipient,
            "pass_outcome": outcome,
        }
        rows.append(row)
        if also:
            rows.append(dict(row, event_type=also))
        if 102 in tags and on_ball:  # own goal on a pass or shot: keep the action, add the own goal
            rows.append(dict(rows[-1], event_type="own_goal", **EMPTY))
        if on_ball and 1401 in tags:  # the action was also an interception
            rows.append(dict(rows[-1], event_type="interception", **EMPTY))
        prev = e

    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{team}: {len(matches)} matches, {len(rows)} events -> {out}")


if __name__ == "__main__":
    if len(sys.argv) != 7:
        sys.exit(__doc__)
    main(*sys.argv[1:])
