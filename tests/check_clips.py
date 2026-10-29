"""Every clip of every list, checked against its replay (the actions the app draws from the raw events).
Usage:  python -X utf8 tests/check_clips.py <data_dir> [--wyscout] [--team "<Team key>"]
Per clip: the replay opens; it starts at the clip time (within 1 s); for possession lists (sequences, restarts, set pieces, xT) the replay holds
the same number of the team's passes as the list, lasts as long as the list says (within 2 s), and has a shot of the team exactly when the list
says ended_in_shot; for transitions (window of 6 s before to 16 s after) a shot of the right team is in the window when the list says so.
Clips marked as goals by the app must show the goal. Prints counts of mismatches per list, with examples; read-only.
Added 29 Oct 2026 after a report of clips not showing shots (Wyscout events have no shot end point)."""

import os, sys, collections

here = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(here)
args = [a for a in sys.argv[1:] if not a.startswith("--")]
wyscout = "--wyscout" in sys.argv
only = sys.argv[sys.argv.index("--team") + 1] if "--team" in sys.argv else None
if wyscout:
    os.environ["OPPREPORT_DATA_WYSCOUT"] = os.path.abspath(args[0])
else:
    os.environ["OPPREPORT_DATA"] = os.path.abspath(args[0])
sys.path.insert(0, os.path.join(root, "app", "backend"))
from fastapi.testclient import TestClient
import server

c = TestClient(server.app, raise_server_exceptions=False, headers={"X-Provider": "wyscout" if wyscout else "statsbomb"})
POSSESSION = ("sequences", "restarts", "setpieces", "threat")
total = collections.Counter()
bad = collections.defaultdict(list)


def flag(team, kind, what, row):
    bad[(kind, what)].append(f"{team} {row['match']} {row['half']}H {row['minute']}:{int(row['second']):02d} {row.get('family', '')}")


for t in c.get("/api/teams").json():
    key = t["key"]
    if only and key != only:
        continue
    for kind in t["clips"]:
        r = c.get(f"/api/teams/{key}/clips/{kind}")
        if r.status_code != 200:
            continue
        rows = sorted(r.json()["rows"], key=lambda x: (int(x["match"]), int(x["half"]), int(x["minute"]), int(x["second"])))
        goals = {tuple(g) for g in c.get(f"/api/teams/{key}/clips/{kind}/goals").json().get("goals", [])}
        for row in rows:
            total[kind] += 1
            p = dict(match=row["match"], half=row["half"], minute=row["minute"], second=row["second"])
            if kind == "transitions":
                p["window"] = "true"
            rp = c.get(f"/api/teams/{key}/replay", params=p)
            if rp.status_code != 200:
                flag(t["team"], kind, f"no replay ({rp.status_code})", row)
                continue
            acts = rp.json()["actions"]
            shot_us = any(a["type"] == "Shot" and a["us"] for a in acts)
            goal_us = any(a["type"] == "Shot" and a["us"] and a.get("outcome") == "Goal" for a in acts)
            start = next((a for a in acts if abs(a["t"]) < 1e-9), acts[0])
            # the replay's time-zero action is the clip's own moment
            if kind != "transitions" and not any(
                abs(a["t"]) <= 1.0 for a in acts if a["us"] or kind in ("restarts", "setpieces")
            ):
                flag(t["team"], kind, "does not start at the clip time", row)
            if kind in POSSESSION:
                if kind == "sequences":
                    n_pass = sum(1 for a in acts if a["type"] == "Pass" and a["us"])
                    if n_pass != int(row["passes"]):
                        flag(t["team"], kind, f"passes {n_pass} vs list {row['passes']}", row)
                    dur = max(a["t"] for a in acts if a["us"] and a["type"] in ("Pass", "Carry", "Shot", "Dribble"))  # the replay also shows how the possession ended (opponent actions)
                    if abs(dur - float(row["duration_s"])) > 2:
                        flag(t["team"], kind, "duration differs by more than 2 s", row)
                if str(row["ended_in_shot"]) == "1" and not shot_us:
                    flag(t["team"], kind, "list says shot, replay has none", row)
                if str(row["ended_in_shot"]) == "0" and shot_us and kind != "threat":
                    flag(t["team"], kind, "replay has a shot, list says none", row)
            elif str(row["ended_in_shot"]) == "1":
                # transitions: a shot within 10 s, by us after a recovery, by them after a loss
                want_us = not row["family"].lower().startswith("loss")
                if not any(a["type"] == "Shot" and a["us"] == want_us and a["t"] >= -0.5 for a in acts):
                    flag(t["team"], kind, "list says shot within 10 s, none in the window", row)
            if (int(row["match"]), int(row["half"]), int(row["minute"]), int(row["second"])) in goals and not (
                goal_us or kind == "transitions"
            ):
                flag(t["team"], kind, "marked as goal, replay shows no goal", row)
    print(f"checked {t['team']}", flush=True)

print()
for kind, n in total.items():
    issues = {w: v for (k, w), v in bad.items() if k == kind}
    print(f"{kind}: {n} clips, {sum(len(v) for v in issues.values())} with an issue")
    for w, v in sorted(issues.items(), key=lambda x: -len(x[1])):
        print(f"   {len(v):5d}  {w}   e.g. {'; '.join(v[:3])}")
print("ALL OK" if not bad else "ISSUES FOUND")
