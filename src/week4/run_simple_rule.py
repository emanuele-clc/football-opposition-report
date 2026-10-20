"""Lancia compare_simple_rules.py sulle 10 squadre (4 iniziali + 6 della selezione) e stampa il riassunto con la regola di decisione del protocollo.
Da eseguire nella cartella dei dati. Una squadra gia' valutata (simplerule_<Squadra>.json) viene saltata: si esegue una volta sola.
Uso: python run_simple_rule.py <repo>/docs/replication10_selection.json --confirm [--print-only] [--summary-only]"""

import sys, os, json, subprocess

sel = json.load(open(sys.argv[1], encoding="utf-8"))
a = set(sys.argv[2:])
po = "--print-only" in a
so = "--summary-only" in a
if not (po or so or "--confirm" in a):
    sys.exit(
        "Serve --confirm (dopo aver committato docs/protocol_simple_rule.md), oppure --print-only / --summary-only."
    )
here = os.path.dirname(os.path.abspath(__file__))
script = os.path.join(here, "compare_simple_rules.py")
teams = [("9_281", "Bayer Leverkusen"), ("2_27", "Leicester City"), ("11_27", "Barcelona"), ("2_27", "Arsenal")] + [
    (f"{t['competition_id']}_{t['season_id']}", t["team"]) for t in sel["teams"] if t["role"] == "primary"
]
os.makedirs("run_logs", exist_ok=True)
if not so:
    for mid, nm in teams:
        fn = nm.replace(" ", "_")
        cmd = [sys.executable, "-X", "utf8", script, f"matches/{mid}.json", nm, ".", "--confirm"]
        print(f"\n=== {nm} ===")
        if os.path.exists(f"simplerule_{fn}.json") and not po:
            print("gia' valutata, salto")
            continue
        print(" ".join(f'"{c}"' if " " in c else c for c in cmd))
        if po:
            continue
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        open(f"run_logs/{fn}_simplerule.log", "w", encoding="utf-8").write(r.stdout + "\n" + r.stderr)
        print("\n".join(r.stdout.strip().splitlines()[-3:-1]))
        if r.returncode != 0:
            print(f"ERRORE: vedi run_logs/{fn}_simplerule.log")
if po:
    sys.exit(0)
print(f"\n{'Squadra':20s}{'build-up (x1 - famiglie, IC95)':48s}{'advanced (x1 - famiglie, IC95)'}")
cnt = {"costruzione": {}, "avanzata": {}}
n = 0
for mid, nm in teams:
    p = f"simplerule_{nm.replace(' ', '_')}.json"
    if not os.path.exists(p):
        print(f"{nm:20s}non eseguita")
        continue
    d = json.load(open(p, encoding="utf-8"))
    n += 1
    cells = []
    for ph in ("costruzione", "avanzata"):
        r = d[ph]
        cnt[ph][r["verdetto"]] = cnt[ph].get(r["verdetto"], 0) + 1
        c = r["diff_x1_ci95"]
        cells.append(f"{r['diff_x1']:+.4f} [{c[0]:+.4f}, {c[1]:+.4f}] {r['verdetto']}")
    print(f"{nm:20s}{cells[0]:48s}{cells[1]}")
print(f"\nSquadre valutate: {n} su 10")
for ph, lab in (("costruzione", "Build-up"), ("avanzata", "Advanced")):
    b = cnt[ph].get("famiglie meglio", 0)
    print(
        f"{lab}: famiglie meglio {b}, nessuna differenza {cnt[ph].get('nessuna differenza', 0)}, regola semplice meglio {cnt[ph].get('regola semplice meglio', 0)} -> "
        + (
            "regola del protocollo SODDISFATTA (almeno 7 su 10)"
            if b >= 7 and n == 10
            else ("regola NON soddisfatta" if n == 10 else "decisione incompleta")
        )
    )
