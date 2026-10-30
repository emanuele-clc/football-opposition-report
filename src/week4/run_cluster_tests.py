"""Runs exploratory_cluster_test.py on the 10 teams (4 initial + 6 from the selection). Run from the data folder.
Skips teams for which exploratory_cluster_test_<Team>.json already exists.
Usage: python run_cluster_tests.py <repo>/docs/replication10_selection.json [--print-only]"""

import sys, os, json, subprocess

sel = json.load(open(sys.argv[1], encoding="utf-8"))
po = "--print-only" in sys.argv
here = os.path.dirname(os.path.abspath(__file__))
script = os.path.join(here, "exploratory_cluster_test.py")
teams = [("9_281", "Bayer Leverkusen"), ("2_27", "Leicester City"), ("11_27", "Barcelona"), ("2_27", "Arsenal")] + [
    (f"{t['competition_id']}_{t['season_id']}", t["team"]) for t in sel["teams"] if t["role"] == "primary"
]
os.makedirs("run_logs", exist_ok=True)
for mid, nm in teams:
    fn = nm.replace(" ", "_")
    cmd = [sys.executable, "-X", "utf8", script, f"matches/{mid}.json", nm, "."]
    print(f"\n=== {nm} ===")
    if os.path.exists(f"exploratory_cluster_test_{fn}.json") and not po:
        print("gia' fatto, salto")
        continue
    print(" ".join(f'"{c}"' if " " in c else c for c in cmd))
    if po:
        continue
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    open(f"run_logs/{fn}_cluster_test.log", "w", encoding="utf-8").write(r.stdout + "\n" + r.stderr)
    print("\n".join(r.stdout.strip().splitlines()[-2:]))
    if r.returncode != 0:
        print(f"ERRORE: vedi run_logs/{fn}_cluster_test.log")
