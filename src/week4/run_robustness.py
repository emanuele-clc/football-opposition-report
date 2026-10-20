"""Lancia exploratory_robustness.py sulle 10 squadre (4 iniziali + 6 della selezione). Da eseguire nella cartella dei dati.
Salta le squadre per cui esiste gia' exploratory_robustness_<Squadra>.json.
Uso: python run_robustness.py <repo>/docs/replication10_selection.json [--print-only]"""

import sys, os, json, subprocess

sel = json.load(open(sys.argv[1], encoding="utf-8"))
po = "--print-only" in sys.argv
here = os.path.dirname(os.path.abspath(__file__))
script = os.path.join(here, "exploratory_robustness.py")
teams = [("9_281", "Bayer Leverkusen"), ("2_27", "Leicester City"), ("11_27", "Barcelona"), ("2_27", "Arsenal")] + [
    (f"{t['competition_id']}_{t['season_id']}", t["team"]) for t in sel["teams"] if t["role"] == "primary"
]
os.makedirs("run_logs", exist_ok=True)
for mid, nm in teams:
    fn = nm.replace(" ", "_")
    cmd = [sys.executable, "-X", "utf8", script, f"matches/{mid}.json", nm, "."]
    print(f"\n=== {nm} ===", flush=True)
    if os.path.exists(f"exploratory_robustness_{fn}.json") and not po:
        print("gia' fatto, salto")
        continue
    if po:
        print(" ".join(cmd))
        continue
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    open(f"run_logs/{fn}_robustness.log", "w", encoding="utf-8").write(r.stdout + "\n" + r.stderr)
    print("\n".join(r.stdout.strip().splitlines()[:6]), flush=True)
    if r.returncode != 0:
        print(f"ERRORE: vedi run_logs/{fn}_robustness.log")
