"""What the replays would draw, checked for things that look wrong on the pitch (complements check_clips.py, which checks the numbers).
Usage:  python -X utf8 tests/check_replays.py <data_dir> [--wyscout] [--per-list N]
For every team and clip list (first N clips per list, default all): actions outside the pitch, end points on a pitch corner (placeholder
coordinates), passes and carries of zero length (drawn as a dot), completed passes whose receiver's next action starts far from the end
point (a long 'ball moved, not recorded' link), and failed passes that end on a line (ball out of play: fine, counted for information).
Added 29 Oct 2026 after clips with gaps and a player 'off the pitch' (a failed pass labelled with the passer's name)."""

import os, sys, math, collections

here = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(here)
args = [a for a in sys.argv[1:] if not a.startswith("--")]
wyscout = "--wyscout" in sys.argv
per = int(sys.argv[sys.argv.index("--per-list") + 1]) if "--per-list" in sys.argv else None
os.environ["OPPREPORT_DATA_WYSCOUT" if wyscout else "OPPREPORT_DATA"] = os.path.abspath(args[0])
sys.path.insert(0, os.path.join(root, "app", "backend"))
from fastapi.testclient import TestClient
import server

c = TestClient(server.app, raise_server_exceptions=False, headers={"X-Provider": "wyscout" if wyscout else "statsbomb"})
count, examples, actions = collections.Counter(), collections.defaultdict(list), 0
CORNERS = {(0, 0), (120, 0), (0, 80), (120, 80)}


def note(what, where):
    count[what] += 1
    if len(examples[what]) < 3:
        examples[what].append(where)


for t in c.get("/api/teams").json():
    for kind in t["clips"]:
        r = c.get(f"/api/teams/{t['key']}/clips/{kind}")
        if r.status_code != 200:
            continue
        rows = r.json()["rows"][:per] if per else r.json()["rows"]
        for row in rows:
            p = dict(match=row["match"], half=row["half"], minute=row["minute"], second=row["second"])
            if kind == "transitions":
                p["window"] = "true"
            rp = c.get(f"/api/teams/{t['key']}/replay", params=p)
            if rp.status_code != 200:
                continue
            acts = rp.json()["actions"]
            where = f"{t['team']} {kind} {row['match']} {row['minute']}:{int(row['second']):02d}"
            for i, a in enumerate(acts):
                actions += 1
                pts = [(a["x"], a["y"])] + ([(a["ex"], a["ey"])] if "ex" in a else [])
                if any(x < -0.5 or x > 120.5 or y < -0.5 or y > 80.5 for x, y in pts):
                    note("outside the pitch", where)
                if "ex" in a and (round(a["ex"]), round(a["ey"])) in CORNERS:
                    note("end point on a pitch corner (placeholder?)", where)
                if a["type"] in ("Pass", "Carry") and "ex" in a and math.hypot(a["ex"] - a["x"], a["ey"] - a["y"]) < 0.5:
                    note(f"{a['type'].lower()} of zero length (drawn as a dot)", where)
                if a["type"] == "Pass" and a.get("ok") and "ex" in a and i + 1 < len(acts) and acts[i + 1]["us"] == a["us"]:
                    nx = acts[i + 1]
                    if math.hypot(nx["x"] - a["ex"], nx["y"] - a["ey"]) > 15:
                        note("receiver's next action > 15 m from the pass end", where)
                if a["type"] == "Pass" and not a.get("ok") and "ex" in a and (
                    a["ex"] <= 0 or a["ex"] >= 120 or a["ey"] <= 0 or a["ey"] >= 80
                ):
                    note("failed pass ending on a line (ball out: fine)", where)
    print(f"checked {t['team']}", flush=True)

print(f"\n{actions} actions")
for w, n in count.most_common():
    print(f"{n:7d}  {w}   e.g. {'; '.join(examples[w])}")
