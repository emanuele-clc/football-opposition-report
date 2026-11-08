"""Downloads the StatsBomb open data of one competition and season.

It gets the match list and then the events (and the 360 files when there are any) of every match, or only of one team if you give a name.
Files already on disk are skipped, so if the download stops you can just run it again.
Run it from the data folder: it creates matches/, ev/ and t360/ there. StatsBomb data is non-commercial, cite StatsBomb.

Usage: python download_data.py <competition_id> <season_id> [Team]      e.g. python download_data.py 9 281 "Bayer Leverkusen"
"""

import json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

URL = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
comp = sys.argv[1]
season = sys.argv[2]
team = sys.argv[3] if len(sys.argv) > 3 else None  # no team = every match

for folder in ("matches", "ev", "t360"):
    os.makedirs(folder, exist_ok=True)


def download(job):
    url, fn = job
    if os.path.exists(fn) and os.path.getsize(fn) > 100:
        return
    subprocess.run(["curl", "-sS", "-m", "120", "-o", fn, url])


download((f"{URL}/competitions.json", "competitions.json"))
match_file = f"matches/{comp}_{season}.json"
download((f"{URL}/matches/{comp}/{season}.json", match_file))

matches = json.load(open(match_file, encoding="utf-8"))
if team:
    matches = [g for g in matches if team in (g["home_team"]["home_team_name"], g["away_team"]["away_team_name"])]

jobs = []
for g in matches:
    mid = g["match_id"]
    jobs.append((f"{URL}/events/{mid}.json", f"ev/{mid}.json"))
    if g.get("match_status_360") == "available":
        jobs.append((f"{URL}/three-sixty/{mid}.json", f"t360/{mid}.json"))

# 8 downloads at the same time
with ThreadPoolExecutor(8) as pool:
    list(pool.map(download, jobs))
print(len(matches), "partite,", len(jobs), "file")
