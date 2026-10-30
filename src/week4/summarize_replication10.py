"""Summary of the 10-team replication: reads holdout_<Team>.json (and null_baseline_<Team>.json if present) and applies the protocol's decision rule.
Usage: python summarize_replication10.py <repo>/docs/replication10_selection.json [results_folder=results] [out=results/replication10_summary.json]"""

import sys, os, json, math

sel = json.load(open(sys.argv[1], encoding="utf-8"))
rd = sys.argv[2] if len(sys.argv) > 2 else "results"
outp = sys.argv[3] if len(sys.argv) > 3 else f"{rd}/replication10_summary.json"
first4 = [
    ("Bayer Leverkusen", "Bundesliga 2023/24"),
    ("Leicester City", "Premier League 2015/16"),
    ("Barcelona", "La Liga 2015/16"),
    ("Arsenal", "Premier League 2015/16"),
]
teams = first4 + [(t["team"], f"{t['league']} 2015/16") for t in sel["teams"] if t["role"] == "primary"]


def wilson(k, n, z=1.96):
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [(c - h) / d, (c + h) / d]


rows = []
for team, lab in teams:
    fn = team.replace(" ", "_")
    p = f"{rd}/holdout_{fn}.json"
    if not os.path.exists(p):
        rows.append(dict(team=team, league=lab, status="non eseguita"))
        continue
    d = json.load(open(p, encoding="utf-8"))
    c, v = d["costruzione"], d["avanzata"]
    r = dict(
        team=team,
        league=lab,
        status="eseguita",
        H1=c["H1_pass"],
        H2=c["H2_pass"],
        gain=c["guadagno"],
        gain_ci=c["guadagno_ci95"],
        build_up_pass=bool(c["H1_pass"] and c["H2_pass"]),
        H3_build=c.get("H3_pass"),
        H3_adv=v.get("H3_pass"),
        H1_adv=v["H1_pass"],
        H2_adv=v["H2_pass"],
    )
    nb = f"{rd}/null_baseline_{fn}.json"
    if os.path.exists(nb):
        b = json.load(open(nb, encoding="utf-8"))["costruzione"]
        r["E1_margin"] = b["osservato"]["jaccard_mean"] - max(
            b["null_shuffle"]["jaccard_mean"], b["null_gauss"]["jaccard_mean"]
        )
    rows.append(r)
done = [r for r in rows if r["status"] == "eseguita"]
k = sum(r["build_up_pass"] for r in done)
n = len(done)
h3b = [r for r in done if r["H3_build"] is not None]
h3a = [r for r in done if r["H3_adv"] is not None]
verdict = (
    "DECISIONE INCOMPLETA: mancano squadre"
    if n < 10
    else ("la regola del protocollo e' SODDISFATTA" if k >= 7 else "la regola del protocollo NON e' soddisfatta")
) + f" (soglia: almeno 7 su 10; ottenuto {k} su {n})"
res = dict(
    squadre_eseguite=n,
    build_up_H1_e_H2=k,
    intervallo_wilson_95=wilson(k, n),
    H1_solo=sum(r["H1"] for r in done),
    H2_solo=sum(r["H2"] for r in done),
    H3_build_up=[sum(r["H3_build"] for r in h3b), len(h3b)],
    H3_advanced=[sum(r["H3_adv"] for r in h3a), len(h3a)],
    verdetto=verdict,
    squadre=rows,
)
json.dump(res, open(outp, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(f"{'Squadra':26s}{'Lega':26s}{'H1':>5s}{'H2':>5s}{'guadagno':>10s}{'H3 b/a':>9s}{'E1':>7s}")
for r in rows:
    if r["status"] != "eseguita":
        print(f"{r['team']:26s}{r['league']:26s}  non eseguita")
        continue
    f = lambda x: "-" if x is None else ("si" if x else "no")
    print(
        f"{r['team']:26s}{r['league']:26s}{f(r['H1']):>5s}{f(r['H2']):>5s}{r['gain']:>+10.3f}{f(r['H3_build'])+'/'+f(r['H3_adv']):>9s}{('%+.2f' % r['E1_margin']) if 'E1_margin' in r else '-':>7s}"
    )
w = res["intervallo_wilson_95"]
print(
    f"\nBuild-up (H1 e H2): {k} su {n}"
    + (f", intervallo di Wilson 95% [{w[0]:.2f}, {w[1]:.2f}]" if w[0] is not None else "")
)
print(
    f"H3 build-up: {res['H3_build_up'][0]} su {res['H3_build_up'][1]} | H3 advanced: {res['H3_advanced'][0]} su {res['H3_advanced'][1]}"
)
print(verdict)
print("salvato", outp)
