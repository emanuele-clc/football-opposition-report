"""Lancia sample_size.py sulle 10 squadre (4 iniziali + 6 della selezione) e stampa il riassunto. Da eseguire nella cartella dei dati.
Salta le squadre gia' fatte. Uso: python run_sample_size.py <repo>/docs/replication10_selection.json"""

import sys, os, json, subprocess, glob
import numpy as np

sel = json.load(open(sys.argv[1], encoding="utf-8"))
here = os.path.dirname(os.path.abspath(__file__))
script = os.path.join(here, "sample_size.py")
os.makedirs("run_logs", exist_ok=True)
teams = [("9_281", "Bayer Leverkusen"), ("2_27", "Leicester City"), ("11_27", "Barcelona"), ("2_27", "Arsenal")] + [
    (f"{t['competition_id']}_{t['season_id']}", t["team"]) for t in sel["teams"] if t["role"] == "primary"
]
for mid, nm in teams:
    fn = nm.replace(" ", "_")
    print(f"=== {nm} ===")
    if os.path.exists(f"samplesize_{fn}.json"):
        print("gia' fatto, salto")
        continue
    r = subprocess.run(
        [sys.executable, "-X", "utf8", script, f"matches/{mid}.json", nm, "."],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    open(f"run_logs/{fn}_samplesize.log", "w", encoding="utf-8").write(r.stdout + "\n" + r.stderr)
    if r.returncode != 0:
        print(f"ERRORE: vedi run_logs/{fn}_samplesize.log")
T = [
    json.load(open(f"samplesize_{n.replace(' ', '_')}.json", encoding="utf-8"))
    for _, n in teams
    if os.path.exists(f"samplesize_{n.replace(' ', '_')}.json")
]
mets = ["passes", "long", "buildup_share", "shot"]
sd = {m: np.std([t["full"][m] for t in T]) for m in mets}
print(f"\nSquadre: {len(T)}. Deviazione standard tra squadre: " + ", ".join(f"{m} {sd[m]:.3f}" for m in mets))
for n in ["3", "5", "8", "10", "15"]:
    row = []
    for m in mets:
        r = [t["n"][n][m + "_p90"] / sd[m] for t in T if n in t["n"]]
        row.append(f"{m} {np.median(r):.2f} ({sum(x <= 0.5 for x in r)}/{len(r)})")
    sb = [t["n"][n]["shares_build-up_p90"] for t in T if n in t["n"]]
    sa = [t["n"][n]["shares_advanced_p90"] for t in T if n in t["n"]]
    print(
        f"n={n:>2}: errore P90 / SD tra squadre, mediana (squadre sotto 0.5): "
        + " | ".join(row)
        + f" || quote famiglie errore P90: build-up {np.median(sb):.3f}, advanced {np.median(sa):.3f}"
    )
