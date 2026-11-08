"""Runs one analysis on all 10 teams, or prints the summary table with the rule of the protocol (at least 7 of 10).

Run it from the data folder (the one with matches/ and ev/). Teams already done are skipped. Protocol: docs/protocol_replication10.md.
    python ten_teams.py run simplerule|samplesize|clustertest <selection.json> [--confirm] [--print-only]
    python ten_teams.py summary replication|simplerule|samplesize <selection.json> [results_folder=results] [out]
The draw of the 6 new teams was made once with archive/select_and_replicate.py (removed on 8 Nov 2026; see git commit 7d6a28f)."""

import sys, os, json, math, collections, subprocess
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FIRST4 = [
    ("9_281", "Bayer Leverkusen", "Bundesliga 2023/24"),
    ("2_27", "Leicester City", "Premier League 2015/16"),
    ("11_27", "Barcelona", "La Liga 2015/16"),
    ("2_27", "Arsenal", "Premier League 2015/16"),
]


def ten_teams(selection):
    # (match file key, team, league) of the 4 teams chosen by hand + the 6 drawn
    teams = list(FIRST4)
    for t in selection["teams"]:
        if t["role"] == "primary":
            teams.append((f"{t['competition_id']}_{t['season_id']}", t["team"], f"{t['league']} 2015/16"))
    return teams


def run_logged(cmd, log):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    open(log, "w", encoding="utf-8").write(r.stdout + "\n" + r.stderr)
    return r


def show(cmd):
    return " ".join(f'"{c}"' if " " in c else c for c in cmd)


# ---------------------------------------------------------------- run one script on the 10 teams
SCRIPTS = {
    # name: (script and its first arguments, output file prefix, needs --confirm)
    "simplerule": (["compare_simple_rules.py"], "simplerule", True),
    "samplesize": (["sample_size.py"], "samplesize", False),
    "clustertest": (["exploratory_clusters.py", "copula"], "exploratory_cluster_test", False),
}


def run_all(what, selection, flags):
    script, prefix, needs_confirm = SCRIPTS[what]
    print_only = "--print-only" in flags
    if needs_confirm and "--confirm" not in flags and not print_only:
        sys.exit("Needs --confirm (after committing the protocol) or --print-only.")
    os.makedirs("run_logs", exist_ok=True)
    for mid, team, _ in ten_teams(selection):
        fn = team.replace(" ", "_")
        cmd = [sys.executable, "-X", "utf8", os.path.join(HERE, script[0])] + script[1:] + [f"matches/{mid}.json", team, "."]
        if needs_confirm:
            cmd.append("--confirm")
        print(f"\n=== {team} ===")
        if os.path.exists(f"{prefix}_{fn}.json") and not print_only:
            print("gia' fatto, salto")
            continue
        print(show(cmd))
        if print_only:
            continue
        r = run_logged(cmd, f"run_logs/{fn}_{what}.log")
        print("\n".join(r.stdout.strip().splitlines()[-3:]))
        if r.returncode != 0:
            print(f"ERRORE: vedi run_logs/{fn}_{what}.log")


# ---------------------------------------------------------------- summaries
def wilson(k, n, z=1.96):
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [(c - h) / d, (c + h) / d]


def yes_no(x):
    return "-" if x is None else ("si" if x else "no")


def summary_replication(selection, folder, out):
    # H1 and H2 in the build-up for each team, and the protocol rule: at least 7 of 10
    rows = []
    for _, team, league in ten_teams(selection):
        fn = team.replace(" ", "_")
        p = f"{folder}/holdout_{fn}.json"
        if not os.path.exists(p):
            rows.append({"team": team, "league": league, "status": "non eseguita"})
            continue
        d = json.load(open(p, encoding="utf-8"))
        c = d["costruzione"]
        v = d["avanzata"]
        r = {
            "team": team,
            "league": league,
            "status": "eseguita",
            "H1": c["H1_pass"],
            "H2": c["H2_pass"],
            "gain": c["guadagno"],
            "gain_ci": c["guadagno_ci95"],
            "build_up_pass": bool(c["H1_pass"] and c["H2_pass"]),
            "H3_build": c.get("H3_pass"),
            "H3_adv": v.get("H3_pass"),
            "H1_adv": v["H1_pass"],
            "H2_adv": v["H2_pass"],
        }
        nb = f"{folder}/null_baseline_{fn}.json"
        if os.path.exists(nb):
            b = json.load(open(nb, encoding="utf-8"))["costruzione"]
            r["E1_margin"] = b["osservato"]["jaccard_mean"] - max(b["null_shuffle"]["jaccard_mean"], b["null_gauss"]["jaccard_mean"])
        rows.append(r)

    done = [r for r in rows if r["status"] == "eseguita"]
    k = sum(r["build_up_pass"] for r in done)
    n = len(done)
    h3b = [r for r in done if r["H3_build"] is not None]
    h3a = [r for r in done if r["H3_adv"] is not None]
    if n < 10:
        verdict = "DECISIONE INCOMPLETA: mancano squadre"
    elif k >= 7:
        verdict = "la regola del protocollo e' SODDISFATTA"
    else:
        verdict = "la regola del protocollo NON e' soddisfatta"
    verdict += f" (soglia: almeno 7 su 10; ottenuto {k} su {n})"
    res = {
        "squadre_eseguite": n,
        "build_up_H1_e_H2": k,
        "intervallo_wilson_95": wilson(k, n),
        "H1_solo": sum(r["H1"] for r in done),
        "H2_solo": sum(r["H2"] for r in done),
        "H3_build_up": [sum(r["H3_build"] for r in h3b), len(h3b)],
        "H3_advanced": [sum(r["H3_adv"] for r in h3a), len(h3a)],
        "verdetto": verdict,
        "squadre": rows,
    }
    json.dump(res, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)

    for r in done:
        print(f"{r['team']:26s} H1 {yes_no(r['H1'])}  H2 {yes_no(r['H2'])}  guadagno {r['gain']:+.3f}  H3 {yes_no(r['H3_build'])}/{yes_no(r['H3_adv'])}")
    print(f"\nBuild-up (H1 e H2): {k} su {n}, Wilson 95% {res['intervallo_wilson_95']}")
    print(verdict)
    print("salvato", out)


def summary_simplerule(selection, folder):
    # families vs end-position rule: count of verdicts per phase, rule of the protocol (>= 7 of 10 'families better')
    count = {"costruzione": collections.Counter(), "avanzata": collections.Counter()}
    done = 0
    for _, team, _ in ten_teams(selection):
        p = f"{folder}/simplerule_{team.replace(' ', '_')}.json"
        if not os.path.exists(p):
            print(f"{team:20s}non eseguita")
            continue
        d = json.load(open(p, encoding="utf-8"))
        done += 1
        for phase in count:
            count[phase][d[phase]["verdetto"]] += 1
        print(f"{team:20s} build-up: {d['costruzione']['verdetto']:24s} advanced: {d['avanzata']['verdetto']}")
    print(f"\nSquadre valutate: {done} su 10 (regola: almeno 7 'famiglie meglio')")
    for phase in count:
        print(phase, dict(count[phase]))


def summary_samplesize(selection, folder):
    # error with n matches (90th percentile) divided by the spread between the teams; below 0.5 = good enough
    T = []
    for _, team, _ in ten_teams(selection):
        p = f"{folder}/samplesize_{team.replace(' ', '_')}.json"
        if os.path.exists(p):
            T.append(json.load(open(p, encoding="utf-8")))
    metrics = ["passes", "long", "buildup_share", "shot"]
    sd = {m: np.std([t["full"][m] for t in T]) for m in metrics}
    for n in ["3", "5", "8", "10", "15"]:
        row = []
        for m in metrics:
            r = [t["n"][n][m + "_p90"] / sd[m] for t in T if n in t["n"]]
            row.append(f"{m} {np.median(r):.2f} ({sum(x <= 0.5 for x in r)}/{len(r)})")
        print(f"n={n:>2} (errore P90 / SD tra squadre, mediana; squadre sotto 0.5): " + " | ".join(row))


if __name__ == "__main__":
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)

    if args[0] == "run" and len(args) == 3 and args[1] in SCRIPTS:
        run_all(args[1], json.load(open(args[2], encoding="utf-8")), flags)
    elif args[0] == "summary" and len(args) >= 3:
        selection = json.load(open(args[2], encoding="utf-8"))
        folder = args[3] if len(args) > 3 else "results"
        if args[1] == "replication":
            out = args[4] if len(args) > 4 else f"{folder}/replication10_summary.json"
            summary_replication(selection, folder, out)
        elif args[1] == "simplerule":
            summary_simplerule(selection, folder)
        elif args[1] == "samplesize":
            summary_samplesize(selection, folder)
        else:
            sys.exit(__doc__)
    else:
        sys.exit(__doc__)
