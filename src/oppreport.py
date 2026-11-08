"""One command for the whole report.

Runs all the sheets for one team and puts everything in one folder.
Works with StatsBomb data or with a generic CSV from any provider. If some match events are missing it tells you what to download.

From a generic CSV of events (any provider, see docs/data_format.md):
    python src/oppreport.py --csv events.csv --team "LASK" --out reports [--video-offsets offsets.csv] [--coords 120x80]
From StatsBomb open data already downloaded:
    python src/oppreport.py --statsbomb matches/9_281.json --data-dir <data folder> --team "Bayer Leverkusen" --out reports"""

import argparse, json, os, sys, subprocess, shutil

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--team", required=True)
ap.add_argument("--out", default="reports")
ap.add_argument("--csv")
ap.add_argument("--statsbomb")
ap.add_argument("--data-dir", default=".")
ap.add_argument("--video-offsets")
ap.add_argument("--coords", default="100", choices=["100", "120x80"])
a = ap.parse_args()
if bool(a.csv) == bool(a.statsbomb):
    sys.exit("Exactly one of --csv and --statsbomb is required.")

here = os.path.dirname(os.path.abspath(__file__))
out = os.path.abspath(a.out)
os.makedirs(out, exist_ok=True)
py = [sys.executable, "-X", "utf8"]
fn = a.team.replace(" ", "_")

if a.csv:
    # convert the CSV into StatsBomb-style files in out/_work
    base = os.path.join(out, "_work")
    os.makedirs(base, exist_ok=True)
    cmd = py + [os.path.join(here, "adapters", "generic_csv.py"), os.path.abspath(a.csv), base]
    if a.coords == "120x80":
        cmd += ["--coords", a.coords]
    if subprocess.run(cmd).returncode:
        sys.exit("Conversion failed: see the messages above and docs/data_format.md")
    mf = os.path.join(base, "matches", "generic.json")
else:
    base = os.path.abspath(a.data_dir)
    mf = a.statsbomb
    if not os.path.exists(mf):
        mf = os.path.join(base, a.statsbomb)
    mf = os.path.abspath(mf)
    if not os.path.exists(mf):
        sys.exit(f"Match file not found: {a.statsbomb} (looked here and in {base})")
    games = []
    for g in json.load(open(mf, encoding="utf-8")):
        if a.team in (g["home_team"]["home_team_name"], g["away_team"]["away_team_name"]):
            games.append(g)
    if not games:
        sys.exit(f"{a.team} plays no match in {a.statsbomb}.")
    # stop early if some event files were never downloaded
    missing = []
    for g in games:
        p = os.path.join(base, "ev", f"{g['match_id']}.json")
        if not (os.path.exists(p) and os.path.getsize(p) > 100):
            missing.append(g["match_id"])
    if missing:
        cid, sid = os.path.basename(mf)[:-5].split("_")
        download = os.path.join(here, "analysis", "download_data.py")
        print(f"Events missing for {len(missing)} of {len(games)} matches of {a.team} (e.g. ev/{missing[0]}.json).")
        print("Download them first, from the data folder:")
        print(f'  cd "{base}"; python -X utf8 "{download}" {cid} {sid} "{a.team}"')
        sys.exit(1)

if a.video_offsets and not os.path.exists(a.video_offsets):
    sys.exit(f"Video offsets file not found: {a.video_offsets}. Remove --video-offsets or create the file (docs/data_format.md, section Video times).")
env = dict(os.environ, MPLBACKEND="Agg")
if a.video_offsets:
    env["OPPREPORT_OFFSETS"] = os.path.abspath(a.video_offsets)

print("Building the report (a few minutes: resampling for the reliability estimates)...")
# the first four sheets must work; the last four need StatsBomb-style events and are skipped if they fail
SHEETS = [
    ("make_report.py", "Report failed.", True),
    ("restarts.py", "Restart sheet failed.", True),
    ("setpieces.py", "Set-piece sheet failed.", True),
    ("transitions.py", "Transitions sheet failed.", True),
    ("defending.py", "Defending sheet skipped: it needs StatsBomb-style defensive events (Pressure, Duel, ...), not present in the generic CSV.", False),
    ("matchups.py", "Matchups sheet skipped: it needs StatsBomb-style defensive events and formations.", False),
    ("keyplayers.py", "Key players skipped: they need StatsBomb-style events.", False),
    ("xthreat.py", "Threat (xT) sheet skipped: it needs StatsBomb-style pass outcomes, not present in the generic CSV.", False),
]
for script, message, must_work in SHEETS:
    r = subprocess.run(py + [os.path.join(here, "report", script), mf, a.team, base], env=env)
    if r.returncode:
        if must_work:
            sys.exit(message)
        print(message)
if subprocess.run(py + [os.path.join(here, "report", "summary.py"), a.team, base], env=env).returncode:
    sys.exit("Prep page failed.")

# copy the outputs from the data folder to --out
names = [
    "prep_{}.html", "report_{}.html", "report_{}.json", "clips_{}.csv", "review_{}.csv", "review_{}.html",
    "restarts_{}.html", "restarts_{}.json", "restart_clips_{}.csv",
    "setpieces_{}.html", "setpieces_{}.json", "setpiece_clips_{}.csv",
    "transitions_{}.html", "transitions_{}.json", "transition_clips_{}.csv",
    "defending_{}.html", "defending_{}.json", "matchups_{}.json", "keyplayers_{}.json",
    "xthreat_{}.html", "xthreat_{}.json", "xt_clips_{}.csv",
]
for name in names:
    f = name.format(fn)
    if os.path.exists(os.path.join(base, f)) and out != base:
        shutil.copy(os.path.join(base, f), os.path.join(out, f))

print(f"Done. Open {os.path.join(out, f'prep_{fn}.html')}")
print("The other sheets (report, restarts, set pieces, transitions, defending, threat) and the clip lists are in the same folder.")
