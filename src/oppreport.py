"""Un comando per generare il report sull'avversario.
Da eventi in CSV generico (qualunque fornitore, vedi docs/data_format.md):
    python src/oppreport.py --csv eventi.csv --team "LASK" --out reports [--video-offsets offsets.csv] [--coords 120x80]
Da dati aperti StatsBomb gia' scaricati:
    python src/oppreport.py --statsbomb matches/9_281.json --data-dir <cartella dati> --team "Bayer Leverkusen" --out reports
Produce in --out: prep_<Squadra>.html (una pagina di preparazione partita con i fatti principali e i link alle schede), report_<Squadra>.html (e .json), clips_<Squadra>.csv (tutte le sequenze con la famiglia e il tempo video), review_<Squadra>.csv/.html (scheda per l'analista),
restarts_<Squadra>.html (uscite da rinvio, portiere e rimesse) con restart_clips_<Squadra>.csv, setpieces_<Squadra>.html (corner e punizioni) con setpiece_clips_<Squadra>.csv, transitions_<Squadra>.html (perdite, recuperi, transizioni) con transition_clips_<Squadra>.csv, xthreat_<Squadra>.html (minaccia xT di passaggi e conduzioni) con xt_clips_<Squadra>.csv; con --xml anche xml/ (un file per partita da importare nel programma video)."""

import argparse, json, os, sys, subprocess, shutil

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--team", required=True)
ap.add_argument("--out", default="reports")
ap.add_argument("--csv")
ap.add_argument("--statsbomb")
ap.add_argument("--data-dir", default=".")
ap.add_argument("--video-offsets")
ap.add_argument("--xml", action="store_true", help="scrive anche i file XML per il programma video")
ap.add_argument("--coords", default="100", choices=["100", "120x80"])
a = ap.parse_args()
if bool(a.csv) == bool(a.statsbomb):
    sys.exit("Serve esattamente una tra --csv e --statsbomb.")
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
print("Genero il report (qualche minuto: ricampionamenti per le stime di affidabilita')...")
r = subprocess.run(py + [os.path.join(here, "report", "make_report.py"), mf, a.team, base], env=env)
if r.returncode:
    sys.exit("Generazione del report fallita.")
r = subprocess.run(py + [os.path.join(here, "report", "restarts.py"), mf, a.team, base], env=env)
if r.returncode:
    sys.exit("Scheda delle uscite da fermo fallita.")
r = subprocess.run(py + [os.path.join(here, "report", "setpieces.py"), mf, a.team, base], env=env)
if r.returncode:
    sys.exit("Scheda delle palle inattive fallita.")
r = subprocess.run(py + [os.path.join(here, "report", "transitions.py"), mf, a.team, base], env=env)
if r.returncode:
    sys.exit("Scheda delle transizioni fallita.")
r = subprocess.run(py + [os.path.join(here, "report", "defending.py"), mf, a.team, base], env=env)
if r.returncode:
    print(
        "Scheda della fase difensiva saltata: servono eventi difensivi in stile StatsBomb (Pressure, Duel, ...), assenti nel CSV generico."
    )
r = subprocess.run(py + [os.path.join(here, "report", "matchups.py"), mf, a.team, base], env=env)
if r.returncode:
    print("Scheda dei confronti per avversario saltata: servono eventi difensivi e moduli in stile StatsBomb.")
r = subprocess.run(py + [os.path.join(here, "report", "keyplayers.py"), mf, a.team, base], env=env)
if r.returncode:
    print("Giocatori chiave saltati: servono gli eventi in stile StatsBomb.")
r = subprocess.run(py + [os.path.join(here, "report", "xthreat.py"), mf, a.team, base], env=env)
if r.returncode:
    print(
        "Scheda della minaccia (xT) saltata: servono gli esiti dei passaggi in stile StatsBomb, assenti nel CSV generico."
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
    if os.path.exists(os.path.join(base, f)):
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
