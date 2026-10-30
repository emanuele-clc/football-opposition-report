"""Downloads StatsBomb open data from GitHub for one competition-season.
Usage: python download_data.py <competition_id> <season_id> [Team]   (e.g. 9 281 "Bayer Leverkusen")
Creates the folders matches/, ev/ (events), t360/ (360 frames, if available). StatsBomb non-commercial licence: cite StatsBomb."""

import json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

BASE = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
cid, sid = sys.argv[1], sys.argv[2]
team = sys.argv[3] if len(sys.argv) > 3 else None
for d in ("matches", "ev", "t360"):
    os.makedirs(d, exist_ok=True)


def curl(url, fn):
    if os.path.exists(fn) and os.path.getsize(fn) > 100:
        return
    subprocess.run(["curl", "-sS", "-m", "120", "-o", fn, url])


curl(f"{BASE}/competitions.json", "competitions.json")
curl(f"{BASE}/matches/{cid}/{sid}.json", f"matches/{cid}_{sid}.json")
ms = json.load(open(f"matches/{cid}_{sid}.json", encoding="utf-8"))
if team:
    ms = [g for g in ms if team in (g["home_team"]["home_team_name"], g["away_team"]["away_team_name"])]
jobs = []
for g in ms:
    i = g["match_id"]
    jobs.append((f"{BASE}/events/{i}.json", f"ev/{i}.json"))
    if g.get("match_status_360") == "available":
        jobs.append((f"{BASE}/three-sixty/{i}.json", f"t360/{i}.json"))
with ThreadPoolExecutor(8) as ex:
    list(ex.map(lambda a: curl(*a), jobs))
print(len(ms), "partite,", len(jobs), "file")
