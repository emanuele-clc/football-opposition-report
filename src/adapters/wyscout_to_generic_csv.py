"""Wyscout public soccer-logs (Pappalardo et al., 2019, Scientific Data; CC BY 4.0) -> generic CSV of docs/data_format.md.
Shows that the report runs on a second provider. Usage:
    python wyscout_to_generic_csv.py <events_X.json> <matches_X.json> <teams.json> <players.json> "<Team>" <out.csv>
Mapping (from the public data paper; checked on Serie A 2017/18):
- coordinates 0-100, attacking direction of the team performing the event, y small = left (same convention as StatsBomb) -> used as is (--coords 100).
- clock: eventSec per half -> cumulative minute (second half from 45). Extra time and penalties are dropped.
- Pass (all sub-events) -> pass; 'Others on the ball / Acceleration' -> carry; Shot -> shot; everything else -> other.
- Free Kick sub-events -> restart on the event: Goal kick -> goal_kick, Throw in -> throw_in, Corner -> corner, Free Kick / Free kick cross -> free_kick (pass),
  Free kick shot -> free_kick (shot), Penalty -> penalty (shot). Kick-off = first event of each half and first event after a goal.
  keeper = a pass by the goalkeeper right after a 'Save attempt' or 'Goalkeeper leaving line' by the same player.
- goal = tag 101 (own goals, tag 102, are not shots of the team). recipient = player of the next event of the same team after an accurate pass (tag 1801).
- Goal kicks: the start position is a placeholder in this data ((0,0) or (100,100)); it is set to the six-yard box (x 5, y 50), so the first-pass
  length is approximate (side of the box unknown). Found by comparing with StatsBomb (short goal kicks 6% before the fix).
- No possession identifiers and no xG in this data: possessions are reconstructed by src/adapters/generic_csv.py (biased, see docs/data_format.md)."""

import csv, json, sys, codecs


def name(s):
    s = s or ""
    """Some names are stored with literal \\uXXXX escapes."""
    if "\\u" not in s:
        return s
    try:
        return json.loads('"' + s.replace('"', '\\"') + '"')
    except ValueError:
        return codecs.decode(s, "unicode_escape")


def main(ev_path, m_path, t_path, p_path, team, out):
    teams = {t["wyId"]: name(t["name"]) for t in json.load(open(t_path, encoding="utf-8"))}
    players = {p["wyId"]: name(p["shortName"]) for p in json.load(open(p_path, encoding="utf-8"))}
    tid = next(k for k, v in teams.items() if v == team)
    matches = {m["wyId"]: m for m in json.load(open(m_path, encoding="utf-8")) if str(tid) in m["teamsData"]}
    evs = [
        e
        for e in json.load(open(ev_path, encoding="utf-8"))
        if e["matchId"] in matches and e["matchPeriod"] in ("1H", "2H")
    ]
    evs.sort(key=lambda e: (e["matchId"], e["matchPeriod"], e["eventSec"]))
    rows, last_goal, prev = [], False, None
    RS = {
        "Goal kick": "goal_kick",
        "Throw in": "throw_in",
        "Corner": "corner",
        "Free Kick": "free_kick",
        "Free kick cross": "free_kick",
        "Free kick shot": "free_kick",
        "Penalty": "penalty",
    }
    for i, e in enumerate(evs):
        m = matches[e["matchId"]]
        side = {v["side"]: int(k) for k, v in m["teamsData"].items()}
        per = 1 if e["matchPeriod"] == "1H" else 2
        sec = e["eventSec"]
        minute = int(sec // 60) + (45 if per == 2 else 0)
        new_half = prev is None or prev["matchId"] != e["matchId"] or prev["matchPeriod"] != e["matchPeriod"]
        tags = {t["id"] for t in e.get("tags", [])}
        en, sub = e["eventName"], e["subEventName"]
        etype = (
            "pass"
            if en == "Pass" or sub in ("Goal kick", "Throw in", "Corner", "Free Kick", "Free kick cross")
            else (
                "shot"
                if en == "Shot" or sub in ("Free kick shot", "Penalty")
                else "carry" if sub == "Acceleration" else "other"
            )
        )
        restart = RS.get(sub, "") if en == "Free Kick" else ""
        if not restart and etype in ("pass", "carry", "shot") and (new_half or last_goal):
            restart = "kick_off"
        if (
            not restart
            and etype == "pass"
            and prev is not None
            and prev["teamId"] == e["teamId"]
            and prev["playerId"] == e["playerId"]
            and prev["eventName"] in ("Save attempt", "Goalkeeper leaving line")
        ):
            restart = "keeper"
        if etype in ("pass", "carry", "shot"):
            last_goal = False
        if 101 in tags or 102 in tags:
            last_goal = True
        pos = e.get("positions") or [{}]
        p0 = pos[0]
        p1 = pos[1] if len(pos) > 1 else {}
        if sub == "Goal kick" and (p0.get("x"), p0.get("y")) in ((0, 0), (100, 100)):
            p0 = {"x": 5, "y": 50}  # start is a placeholder in this data: six-yard box, side unknown
        recipient = ""
        if etype == "pass" and 1801 in tags:
            nxt = next(
                (
                    f
                    for f in evs[i + 1 : i + 6]
                    if f["matchId"] == e["matchId"] and f["teamId"] == e["teamId"] and f["playerId"]
                ),
                None,
            )
            recipient = players.get(nxt["playerId"], "") if nxt and nxt["playerId"] != e["playerId"] else ""
        rows.append(
            dict(
                match_id=e["matchId"],
                match_date=m["dateutc"][:10],
                home_team=teams[side["home"]],
                away_team=teams[side["away"]],
                period=per,
                minute=minute,
                second=int(sec % 60),
                team=teams.get(e["teamId"], str(e["teamId"])),
                event_type=etype,
                x=p0.get("x", ""),
                y=p0.get("y", ""),
                end_x=p1.get("x", "") if etype in ("pass", "carry") else "",
                end_y=p1.get("y", "") if etype in ("pass", "carry") else "",
                restart=restart,
                shot_goal=int(101 in tags) if etype == "shot" else "",
                player=players.get(e["playerId"], ""),
                recipient=recipient,
            )
        )
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
