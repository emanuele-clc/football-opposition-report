"""Esegue la replica sulle squadre selezionate: per ogni squadra scarica i dati, controllo E1 (stabilita' vs dati nulli), validazione sulle partite riservate (--confirm).
Una squadra gia' validata (esiste holdout_<Squadra>.json) viene saltata: la validazione si esegue una volta sola.
Uso (dalla cartella dei dati): python run_new_teams.py <repo>/docs/replication10_selection.json --confirm [--print-only] [--only "Nome squadra"] [--reserves]"""
import sys, os, json, subprocess, argparse
ap = argparse.ArgumentParser(); ap.add_argument("selection"); ap.add_argument("--confirm", action="store_true"); ap.add_argument("--print-only", action="store_true")
ap.add_argument("--only", default=None); ap.add_argument("--reserves", action="store_true"); a = ap.parse_args()
if not a.confirm and not a.print_only: sys.exit("Serve --confirm (dopo aver committato docs/protocol_replication10.md) oppure --print-only.")
here = os.path.dirname(os.path.abspath(__file__)); dl = os.path.join(here, "..", "week1", "download_data.py"); e1 = os.path.join(here, "..", "week3", "stability_null_baseline.py"); val = os.path.join(here, "validate_replication.py")
sel = json.load(open(a.selection, encoding="utf-8")); os.makedirs("run_logs", exist_ok=True)
for t in sel["teams"]:
    if a.only and t["team"] != a.only: continue
    if not a.only and t["role"] != "primary" and not a.reserves: continue
    nm = t["team"]; fn = nm.replace(" ", "_"); mf = f"matches/{t['competition_id']}_{t['season_id']}.json"
    steps = [("download", [sys.executable, "-X", "utf8", dl, str(t["competition_id"]), str(t["season_id"]), nm]), ("E1", [sys.executable, "-X", "utf8", e1, mf, nm, "."]),
             ("validazione", [sys.executable, "-X", "utf8", val, mf, nm, ".", "--confirm"])]
    print(f"\n=== {nm} ({t['league']}, {t['role']}) ===")
    if os.path.exists(f"holdout_{fn}.json") and not a.print_only: print("gia' validata, salto"); continue
    for lab, cmd in steps:
        print(f"[{lab}]", " ".join(f'"{c}"' if " " in c else c for c in cmd))
        if a.print_only: continue
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8"); open(f"run_logs/{fn}_{lab}.log", "w", encoding="utf-8").write(r.stdout + "\n" + r.stderr)
        print("\n".join(r.stdout.strip().splitlines()[-4:]))
        if r.returncode != 0: print(f"ERRORE nel passo {lab}: vedi run_logs/{fn}_{lab}.log"); break
