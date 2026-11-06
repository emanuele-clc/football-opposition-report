"""The 10-team replication: choose the teams, run the analyses on all of them, print the summaries.
Run it from the data folder (the one with matches/ and ev/). Protocol: docs/protocol_replication10.md.
    python ten_teams.py select [data_info] [out]                                   draw the 6 new teams (seed 20261013)
    python ten_teams.py replicate <selection.json> --confirm [--only "Team"] [--reserves] [--print-only]
                                                                                   download + E1 + validation, once per team
    python ten_teams.py run simplerule|samplesize|clustertest <selection.json> [--confirm] [--print-only]
                                                                                   one script on the 10 teams (teams already done are skipped)
    python ten_teams.py summary replication|simplerule|samplesize <selection.json> [results_folder=results] [out]
(Until 6 Nov 2026 these were six files: select_teams.py, run_new_teams.py, summarize_replication10.py,
run_simple_rule.py, run_sample_size.py, run_cluster_tests.py.)"""

import sys, os, json, glob, math, collections, subprocess
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


# ---------------------------------------------------------------- select
# the rule as it was written in the selection file on 13 Oct 2026
RULE = (
    "Selezione delle squadre per la replica su 10 squadre (protocollo: docs/protocol_replication10.md).\n"
    "Regola fissata prima: stagioni complete 2015/2016 di La Liga, Serie A e Ligue 1 (competizioni con almeno 300 partite disponibili), squadre con almeno 30 partite,\n"
    "escluse le 4 squadre gia' usate. Sorteggio stratificato per campionato con seed fisso: 2 squadre primarie + 1 di riserva per campionato (la riserva si usa solo\n"
    "per un guasto tecnico, mai per un risultato)."
)


def select(data_info, out):
    seed = 20261013
    used = {"Bayer Leverkusen", "Leicester City", "Barcelona", "Arsenal"}
    comps = {}
    for c in json.load(open(f"{data_info}/competitions.json", encoding="utf-8")):
        comps[(c["competition_id"], c["season_id"])] = c
    rng = np.random.default_rng(seed)
    teams = []
    for league in ["La Liga", "Serie A", "Ligue 1"]:
        candidates = []
        for f in sorted(glob.glob(f"{data_info}/[0-9]*_*.json")):
            cid, sid = map(int, os.path.basename(f)[:-5].split("_"))
            c = comps.get((cid, sid))
            if c is None or c["competition_name"] != league or c["season_name"] != "2015/2016":
                continue
            ms = json.load(open(f, encoding="utf-8"))
            if len(ms) < 300:
                continue
            count = collections.Counter()
            for g in ms:
                if g.get("match_status") == "available":
                    count[g["home_team"]["home_team_name"]] += 1
                    count[g["away_team"]["away_team_name"]] += 1
            for t, n in count.items():
                if n >= 30 and t not in used:
                    candidates.append((t, cid, sid, n))
        candidates.sort(key=lambda x: x[0])
        order = rng.permutation(len(candidates))
        for rank, i in enumerate(order[:3]):  # 2 primary + 1 reserve
            t, cid, sid, n = candidates[i]
            teams.append(
                {
                    "team": t,
                    "league": league,
                    "season": "2015/2016",
                    "competition_id": cid,
                    "season_id": sid,
                    "matches": n,
                    "role": "primary" if rank < 2 else "reserve",
                    "candidates_in_stratum": len(candidates),
                }
            )
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    result = {"seed": seed, "rule": RULE, "already_used": sorted(used), "teams": teams}
    json.dump(result, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    for t in teams:
        print(f"{t['role']:8s} {t['league']:8s} {t['team']:28s} ({t['matches']} partite, {t['candidates_in_stratum']} candidate nello strato)")
    print("salvato", out)


# ---------------------------------------------------------------- replicate
def replicate(selection, flags, only):
    if "--confirm" not in flags and "--print-only" not in flags:
        sys.exit("Needs --confirm (after committing docs/protocol_replication10.md) or --print-only.")
    print_only = "--print-only" in flags
    py = [sys.executable, "-X", "utf8"]
    os.makedirs("run_logs", exist_ok=True)
    for t in selection["teams"]:
        if only and t["team"] != only:
            continue
        if not only and t["role"] != "primary" and "--reserves" not in flags:
            continue
        team = t["team"]
        fn = team.replace(" ", "_")
        mf = f"matches/{t['competition_id']}_{t['season_id']}.json"
        steps = [
            ("download", py + [os.path.join(HERE, "..", "week1", "download_data.py"), str(t["competition_id"]), str(t["season_id"]), team]),
            ("E1", py + [os.path.join(HERE, "..", "week3", "stability_null_baseline.py"), mf, team, "."]),
            ("validazione", py + [os.path.join(HERE, "validate_replication.py"), mf, team, ".", "--confirm"]),
        ]
        print(f"\n=== {team} ({t['league']}, {t['role']}) ===")
        if os.path.exists(f"holdout_{fn}.json") and not print_only:
            print("gia' validata, salto")
            continue
        for label, cmd in steps:
            print(f"[{label}]", show(cmd))
            if print_only:
                continue
            r = run_logged(cmd, f"run_logs/{fn}_{label}.log")
            print("\n".join(r.stdout.strip().splitlines()[-4:]))
            if r.returncode != 0:
                print(f"ERRORE nel passo {label}: vedi run_logs/{fn}_{label}.log")
                break


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
    if x is None:
        return "-"
    return "si" if x else "no"


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

    print(f"{'Squadra':26s}{'Lega':26s}{'H1':>5s}{'H2':>5s}{'guadagno':>10s}{'H3 b/a':>9s}{'E1':>7s}")
    for r in rows:
        if r["status"] != "eseguita":
            print(f"{r['team']:26s}{r['league']:26s}  non eseguita")
            continue
        h3 = yes_no(r["H3_build"]) + "/" + yes_no(r["H3_adv"])
        e1 = ("%+.2f" % r["E1_margin"]) if "E1_margin" in r else "-"
        print(f"{r['team']:26s}{r['league']:26s}{yes_no(r['H1']):>5s}{yes_no(r['H2']):>5s}{r['gain']:>+10.3f}{h3:>9s}{e1:>7s}")
    w = res["intervallo_wilson_95"]
    line = f"\nBuild-up (H1 e H2): {k} su {n}"
    if w[0] is not None:
        line += f", intervallo di Wilson 95% [{w[0]:.2f}, {w[1]:.2f}]"
    print(line)
    print(f"H3 build-up: {res['H3_build_up'][0]} su {res['H3_build_up'][1]} | H3 advanced: {res['H3_advanced'][0]} su {res['H3_advanced'][1]}")
    print(verdict)
    print("salvato", out)


def summary_simplerule(selection, folder):
    # families vs end-position rule: count of verdicts per phase, rule of the protocol (>= 7 of 10 'families better')
    print(f"\n{'Squadra':20s}{'build-up (x1 - famiglie, IC95)':48s}advanced (x1 - famiglie, IC95)")
    count = {"costruzione": collections.Counter(), "avanzata": collections.Counter()}
    done = 0
    for _, team, _ in ten_teams(selection):
        p = f"{folder}/simplerule_{team.replace(' ', '_')}.json"
        if not os.path.exists(p):
            print(f"{team:20s}non eseguita")
            continue
        d = json.load(open(p, encoding="utf-8"))
        done += 1
        cells = []
        for phase in ("costruzione", "avanzata"):
            r = d[phase]
            count[phase][r["verdetto"]] += 1
            c = r["diff_x1_ci95"]
            cells.append(f"{r['diff_x1']:+.4f} [{c[0]:+.4f}, {c[1]:+.4f}] {r['verdetto']}")
        print(f"{team:20s}{cells[0]:48s}{cells[1]}")
    print(f"\nSquadre valutate: {done} su 10")
    for phase, label in (("costruzione", "Build-up"), ("avanzata", "Advanced")):
        better = count[phase]["famiglie meglio"]
        if done < 10:
            decision = "decisione incompleta"
        elif better >= 7:
            decision = "regola del protocollo SODDISFATTA (almeno 7 su 10)"
        else:
            decision = "regola NON soddisfatta"
        print(
            f"{label}: famiglie meglio {better}, nessuna differenza {count[phase]['nessuna differenza']}, "
            f"regola semplice meglio {count[phase]['regola semplice meglio']} -> {decision}"
        )


def summary_samplesize(selection, folder):
    # error with n matches (90th percentile) divided by the spread between the teams; below 0.5 = good enough
    T = []
    for _, team, _ in ten_teams(selection):
        p = f"{folder}/samplesize_{team.replace(' ', '_')}.json"
        if os.path.exists(p):
            T.append(json.load(open(p, encoding="utf-8")))
    metrics = ["passes", "long", "buildup_share", "shot"]
    sd = {}
    for m in metrics:
        sd[m] = np.std([t["full"][m] for t in T])
    print(f"\nSquadre: {len(T)}. Deviazione standard tra squadre: " + ", ".join(f"{m} {sd[m]:.3f}" for m in metrics))
    for n in ["3", "5", "8", "10", "15"]:
        row = []
        for m in metrics:
            r = [t["n"][n][m + "_p90"] / sd[m] for t in T if n in t["n"]]
            row.append(f"{m} {np.median(r):.2f} ({sum(x <= 0.5 for x in r)}/{len(r)})")
        sb = [t["n"][n]["shares_build-up_p90"] for t in T if n in t["n"]]
        sa = [t["n"][n]["shares_advanced_p90"] for t in T if n in t["n"]]
        print(
            f"n={n:>2}: errore P90 / SD tra squadre, mediana (squadre sotto 0.5): "
            + " | ".join(row)
            + f" || quote famiglie errore P90: build-up {np.median(sb):.3f}, advanced {np.median(sa):.3f}"
        )


if __name__ == "__main__":
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1]
        args.remove(only)
    if not args:
        sys.exit(__doc__)

    if args[0] == "select":
        data_info = args[1] if len(args) > 1 else "data_info"
        out = args[2] if len(args) > 2 else "docs/replication10_selection.json"
        select(data_info, out)
    elif args[0] == "replicate" and len(args) == 2:
        replicate(json.load(open(args[1], encoding="utf-8")), flags, only)
    elif args[0] == "run" and len(args) == 3 and args[1] in SCRIPTS:
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
