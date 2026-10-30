"""One command to build the opposition report.
From events in a generic CSV (any provider, see docs/data_format.md):
    python src/oppreport.py --csv events.csv --team "LASK" --out reports [--video-offsets offsets.csv] [--coords 120x80]
From StatsBomb open data already downloaded:
    python src/oppreport.py --statsbomb matches/9_281.json --data-dir <data folder> --team "Bayer Leverkusen" --out reports
Writes to --out: prep_<Team>.html (one match-preparation page with the main facts and links to the sheets), report_<Team>.html (and .json), clips_<Team>.csv (every sequence with its family and video time), review_<Team>.csv/.html (analyst check sheet),
restarts_<Team>.html (goal kicks, keeper restarts, throw-ins) with restart_clips_<Team>.csv, setpieces_<Team>.html (corners and free kicks) with setpiece_clips_<Team>.csv, transitions_<Team>.html (losses, recoveries, transitions) with transition_clips_<Team>.csv, xthreat_<Team>.html (xT threat of passes and carries) with xt_clips_<Team>.csv; with --xml also xml/ (one file per match to import into the video tool)."""

import argparse, json, os, sys, subprocess, shutil

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--team", required=True)
ap.add_argument("--out", default="reports")
ap.add_argument("--csv")
ap.add_argument("--statsbomb")
ap.add_argument("--data-dir", default=".")
ap.add_argument("--video-offsets")
ap.add_argument("--xml", action="store_true", help="also writes the XML files for the video tool")
ap.add_argument("--coords", default="100", choices=["100", "120x80"])
a = ap.parse_args()
if bool(a.csv) == bool(a.statsbomb):
    sys.exit("Exactly one of --csv and --statsbomb is required.")
here = os.path.dirname(os.path.abspath(__file__))
out = os.path.abspath(a.out)
os.makedirs(out, exist_ok=True)
py = [sys.executable, "-X", "utf8"]
if a.csv:
    base = os.path.join(out, "_work")
    os.makedirs(base, exist_ok=True)
    r = subprocess.run(
        py + [os.path.join(here, "adapters", "generic_csv.py"), os.path.abspath(a.csv), base, "--coords", a.coords]
        if a.coords == "120x80"
        else py + [os.path.join(here, "adapters", "generic_csv.py"), os.path.abspath(a.csv), base]
    )
    if r.returncode:
        sys.exit("Conversione fallita: controlla i messaggi sopra e docs/data_format.md")
    mf = os.path.join(base, "matches", "generic.json")
else:
    base = os.path.abspath(a.data_dir)
    mf = a.statsbomb if os.path.exists(a.statsbomb) else os.path.join(base, a.statsbomb)
    mf = os.path.abspath(mf)
    if not os.path.exists(mf):
        sys.exit(f"File partite non trovato: {a.statsbomb} (cercato qui e in {base})")
    games = [
        g
        for g in json.load(open(mf, encoding="utf-8"))
        if a.team in (g["home_team"]["home_team_name"], g["away_team"]["away_team_name"])
    ]
    if not games:
        sys.exit(f"{a.team} non gioca nessuna partita in {a.statsbomb}.")
    missing = [
        g["match_id"]
        for g in games
        if not (os.path.exists(p := os.path.join(base, "ev", f"{g['match_id']}.json")) and os.path.getsize(p) > 100)
    ]
    if missing:
        cid, sid = os.path.basename(mf)[:-5].split("_")
        sys.exit(
            f"Mancano gli eventi di {len(missing)} partite su {len(games)} di {a.team} (es. ev/{missing[0]}.json). Scaricali prima, dalla cartella dati:\n"
            f'  cd "{base}"; python -X utf8 "{os.path.join(here, "week1", "download_data.py")}" {cid} {sid} "{a.team}"'
        )
if a.video_offsets and not os.path.exists(a.video_offsets):
    sys.exit(
        f"File degli offset video non trovato: {a.video_offsets}. Togli --video-offsets oppure crea il file (docs/data_format.md, sezione Video times)."
    )
env = dict(os.environ, MPLBACKEND="Agg")
if a.video_offsets:
    env["OPPREPORT_OFFSETS"] = os.path.abspath(a.video_offsets)
print("Building the report (a few minutes: resampling for the reliability estimates)...")
r = subprocess.run(py + [os.path.join(here, "report", "make_report.py"), mf, a.team, base], env=env)
if r.returncode:
    sys.exit("Generazione del report fallita.")
r = subprocess.run(py + [os.path.join(here, "report", "restarts.py"), mf, a.team, base], env=env)
if r.returncode:
    sys.exit("Restart sheet failed.")
r = subprocess.run(py + [os.path.join(here, "report", "setpieces.py"), mf, a.team, base], env=env)
if r.returncode:
    sys.exit("Scheda delle palle inattive fallita.")
r = subprocess.run(py + [os.path.join(here, "report", "transitions.py"), mf, a.team, base], env=env)
if r.returncode:
    sys.exit("Scheda delle transizioni fallita.")
r = subprocess.run(py + [os.path.join(here, "report", "defending.py"), mf, a.team, base], env=env)
if r.returncode:
    print(
        "Defending sheet skipped: it needs StatsBomb-style defensive events (Pressure, Duel, ...), not present in the generic CSV."
    )
r = subprocess.run(py + [os.path.join(here, "report", "matchups.py"), mf, a.team, base], env=env)
if r.returncode:
    print("Matchups sheet skipped: it needs StatsBomb-style defensive events and formations.")
r = subprocess.run(py + [os.path.join(here, "report", "keyplayers.py"), mf, a.team, base], env=env)
if r.returncode:
    print("Key players skipped: they need StatsBomb-style events.")
r = subprocess.run(py + [os.path.join(here, "report", "xthreat.py"), mf, a.team, base], env=env)
if r.returncode:
    print(
        "Threat (xT) sheet skipped: it needs StatsBomb-style pass outcomes, not present in the generic CSV."
    )
r = subprocess.run(py + [os.path.join(here, "report", "summary.py"), a.team, base], env=env)
if r.returncode:
    sys.exit("Pagina di preparazione fallita.")
fn = a.team.replace(" ", "_")
for f in (
    f"prep_{fn}.html",
    f"report_{fn}.html",
    f"report_{fn}.json",
    f"clips_{fn}.csv",
    f"review_{fn}.csv",
    f"review_{fn}.html",
    f"restarts_{fn}.html",
    f"restarts_{fn}.json",
    f"restart_clips_{fn}.csv",
    f"setpieces_{fn}.html",
    f"setpieces_{fn}.json",
    f"setpiece_clips_{fn}.csv",
    f"transitions_{fn}.html",
    f"transitions_{fn}.json",
    f"transition_clips_{fn}.csv",
    f"defending_{fn}.html",
    f"defending_{fn}.json",
    f"matchups_{fn}.json",
    f"keyplayers_{fn}.json",
    f"xthreat_{fn}.html",
    f"xthreat_{fn}.json",
    f"xt_clips_{fn}.csv",
):
    if os.path.exists(os.path.join(base, f)) and os.path.abspath(out) != base:
        shutil.copy(os.path.join(base, f), os.path.join(out, f))
if a.xml:
    for c in (
        f"clips_{fn}.csv",
        f"restart_clips_{fn}.csv",
        f"setpiece_clips_{fn}.csv",
        f"transition_clips_{fn}.csv",
        f"xt_clips_{fn}.csv",
    ):
        if not os.path.exists(os.path.join(out, c)):
            continue
        subprocess.run(
            py
            + [os.path.join(here, "report", "clips_to_xml.py"), os.path.join(out, c), os.path.join(out, "xml", c[:-4])]
            + (["--video-offsets", os.path.abspath(a.video_offsets)] if a.video_offsets else [])
            + (["--events-dir", os.path.join(base, "ev")] if os.path.isdir(os.path.join(base, "ev")) else [])
        )
print(
    f"Fatto. Apri {os.path.join(out, f'prep_{fn}.html')}. Altri file: report_{fn}.html, restarts_{fn}.html, setpieces_{fn}.html, transitions_{fn}.html, defending_{fn}.html, xthreat_{fn}.html, matchups_{fn}.json (sezione Matchups dell'app), clips_{fn}.csv, restart_clips_{fn}.csv, review_{fn}.csv/.html"
    + (", xml/" if a.xml else "")
)
