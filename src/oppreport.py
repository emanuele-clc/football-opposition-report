"""Un comando per generare il report sull'avversario.
Da eventi in CSV generico (qualunque fornitore, vedi docs/data_format.md):
    python src/oppreport.py --csv eventi.csv --team "LASK" --out reports [--video-offsets offsets.csv] [--coords 120x80]
Da dati aperti StatsBomb gia' scaricati:
    python src/oppreport.py --statsbomb matches/9_281.json --data-dir <cartella dati> --team "Bayer Leverkusen" --out reports
Produce in --out: report_<Squadra>.html (e .json), clips_<Squadra>.csv (tutte le sequenze con la famiglia e il tempo video), review_<Squadra>.csv/.html (scheda per l'analista)."""
import argparse, os, sys, subprocess, shutil
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--team", required=True); ap.add_argument("--out", default="reports"); ap.add_argument("--csv"); ap.add_argument("--statsbomb"); ap.add_argument("--data-dir", default=".")
ap.add_argument("--video-offsets"); ap.add_argument("--coords", default="100", choices=["100", "120x80"]); a = ap.parse_args()
if bool(a.csv) == bool(a.statsbomb): sys.exit("Serve esattamente una tra --csv e --statsbomb.")
here = os.path.dirname(os.path.abspath(__file__)); out = os.path.abspath(a.out); os.makedirs(out, exist_ok=True); py = [sys.executable, "-X", "utf8"]
if a.csv:
    base = os.path.join(out, "_work"); os.makedirs(base, exist_ok=True)
    r = subprocess.run(py + [os.path.join(here, "adapters", "generic_csv.py"), os.path.abspath(a.csv), base, "--coords", a.coords] if a.coords == "120x80" else py + [os.path.join(here, "adapters", "generic_csv.py"), os.path.abspath(a.csv), base])
    if r.returncode: sys.exit("Conversione fallita: controlla i messaggi sopra e docs/data_format.md")
    mf = os.path.join(base, "matches", "generic.json")
else: base = os.path.abspath(a.data_dir); mf = os.path.abspath(a.statsbomb)
env = dict(os.environ, MPLBACKEND="Agg")
if a.video_offsets: env["OPPREPORT_OFFSETS"] = os.path.abspath(a.video_offsets)
print("Genero il report (qualche minuto: ricampionamenti per le stime di affidabilita')...")
r = subprocess.run(py + [os.path.join(here, "report", "make_report.py"), mf, a.team, base], env=env)
if r.returncode: sys.exit("Generazione del report fallita.")
fn = a.team.replace(" ", "_")
for f in (f"report_{fn}.html", f"report_{fn}.json", f"clips_{fn}.csv", f"review_{fn}.csv", f"review_{fn}.html"):
    if os.path.exists(os.path.join(base, f)): shutil.copy(os.path.join(base, f), os.path.join(out, f))
print(f"Fatto. File in {out}: report_{fn}.html, clips_{fn}.csv, review_{fn}.csv/.html")
