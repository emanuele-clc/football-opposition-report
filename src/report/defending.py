"""Defending sheet: how a team defends without the ball (pressing intensity, where it presses and wins duels, how high it defends, what it concedes). Descriptive, one page.
Usage:  python defending.py <matches.json> "<Team>" [data_dir=.]
Output in data_dir: defending_<Team>.html and defending_<Team>.json. Needs StatsBomb-style defensive events (Pressure, Duel, Interception, ...): with the generic CSV
of another provider these events are missing and the script stops with a message.
Definitions (fixed before looking at any team; locations are on the team's own attacking direction, 0-120 x 0-80):
- defensive actions: Duel, Interception, Foul Committed, Ball Recovery, Block, Clearance by the team. Pressures are counted separately.
- PPDA (passes per defensive action): opponent passes in the opponent's own 60% of the pitch (opponent x < 72) divided by the team's Duels, Interceptions
  and Fouls Committed in the same area (team x >= 48). Lower = the opponent is allowed fewer passes before the team acts: more intense pressing high up.
- pressures: StatsBomb Pressure events per match, share by third (own x < 40, middle, final x >= 80) and share flagged 'counterpress' by StatsBomb
  (pressure within 5 s of losing the ball).
- defensive height: mean and median x of the team's defensive actions (not pressures); higher = defends further from its own goal.
- conceded: opponent shots and the sum of their StatsBomb xG per match (penalties included; own goals are not shots).
- last 5: the five most recent matches. Intervals: 95% bootstrap over matches."""
import sys, os, io, json, base64, html as H
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
MF, TEAM = sys.argv[1], sys.argv[2]; BASE = sys.argv[3] if len(sys.argv) > 3 else "."
DEF = ("Duel", "Interception", "Foul Committed", "Ball Recovery", "Block", "Clearance"); PPDA_ACT = ("Duel", "Interception", "Foul Committed")
THIRDS = ["own third", "middle third", "final third"]; third = lambda x: THIRDS[0] if x < 40 else (THIRDS[1] if x < 80 else THIRDS[2])

def extract():
    ms = sorted([g for g in json.load(open(MF, encoding="utf-8")) if TEAM in (g["home_team"]["home_team_name"], g["away_team"]["away_team_name"])], key=lambda g: g["match_date"])
    per = []; P = []
    for gi, g in enumerate(ms):
        ev = json.load(open(f"{BASE}/ev/{g['match_id']}.json", encoding="utf-8"))
        us = [e for e in ev if e["team"]["name"] == TEAM]; them = [e for e in ev if e["team"]["name"] != TEAM]
        opp_pass = sum(1 for e in them if e["type"]["name"] == "Pass" and e.get("location") and e["location"][0] < 72)
        act_hi = sum(1 for e in us if e["type"]["name"] in PPDA_ACT and e.get("location") and e["location"][0] >= 48)
        dx = [e["location"][0] for e in us if e["type"]["name"] in DEF and e.get("location")]
        pr = [e for e in us if e["type"]["name"] == "Pressure" and e.get("location")]
        shots = [e for e in them if e["type"]["name"] == "Shot"]
        per.append(dict(gi=gi, date=g["match_date"], opp_pass=opp_pass, act_hi=act_hi, def_actions=len(dx), def_x_sum=float(sum(dx)), pressures=len(pr),
                        counterpress=sum(1 for e in pr if e.get("counterpress")), shots=len(shots), xg=float(sum(e["shot"].get("statsbomb_xg", 0) or 0 for e in shots))))
        P += [dict(gi=gi, x=e["location"][0], y=e["location"][1]) for e in pr]
        per[-1]["dx"] = dx
    return per, P, len(ms)

def boot(stat, games, B=1000, seed=0):
    rng = np.random.default_rng(seed); out = [stat(rng.choice(games, len(games))) for _ in range(B)]
    return [float(np.nanpercentile(out, 2.5)), float(np.nanpercentile(out, 97.5))]

if __name__ == "__main__":
    per, P, nm = extract(); fn = TEAM.replace(" ", "_")
    if sum(m["pressures"] for m in per) == 0 and sum(m["def_actions"] for m in per) == 0:
        sys.exit(f"No defensive events for {TEAM}: this sheet needs StatsBomb-style Pressure/Duel/Interception events (not in the generic CSV).")
    by = {m["gi"]: m for m in per}; games = np.arange(nm)
    S = lambda key, gs: sum(by[g][key] for g in gs)
    ppda = lambda gs: S("opp_pass", gs) / max(S("act_hi", gs), 1)
    pm = lambda key: (lambda gs: S(key, gs) / len(gs))
    height = lambda gs: S("def_x_sum", gs) / max(S("def_actions", gs), 1)
    cp = lambda gs: S("counterpress", gs) / max(S("pressures", gs), 1)
    allx = [x for m in per for x in m["dx"]]
    pt = {t: sum(1 for p in P if third(p["x"]) == t) for t in THIRDS}; npr = max(len(P), 1)
    grid, _, _ = np.histogram2d([p["x"] for p in P], [p["y"] for p in P], bins=[6, 4], range=[[0, 120], [0, 80]])
    last = games[-5:]
    res = {"team": TEAM, "matches": int(nm),
           "ppda": dict(value=ppda(games), ci=boot(ppda, games), last5=ppda(last), opp_passes=int(S("opp_pass", games)), actions=int(S("act_hi", games))),
           "pressures": dict(per_match=pm("pressures")(games), ci=boot(pm("pressures"), games), last5=pm("pressures")(last),
                             by_third={t: dict(share=pt[t] / npr, per_match=pt[t] / nm) for t in THIRDS},
                             counterpress_share=cp(games), counterpress_ci=boot(cp, games), grid_per_match=(grid / nm).round(3).tolist()),
           "height": dict(mean_x=height(games), ci=boot(height, games), median_x=float(np.median(allx)) if allx else None, last5=height(last), actions_per_match=pm("def_actions")(games)),
           "conceded": dict(shots_per_match=pm("shots")(games), shots_ci=boot(pm("shots"), games), xg_per_match=pm("xg")(games), xg_ci=boot(pm("xg"), games),
                            last5_shots=pm("shots")(last), last5_xg=pm("xg")(last))}
    json.dump(res, open(f"{BASE}/defending_{fn}.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)

    fig, ax = plt.subplots(figsize=(6.2, 4.0)); g = np.array(res["pressures"]["grid_per_match"])
    ax.imshow(g.T, extent=[0, 120, 80, 0], cmap="Oranges", vmin=0, vmax=max(g.max(), 0.1), aspect="equal")
    for i in range(6):
        for j in range(4): ax.text(10 + 20 * i, 10 + 20 * j, f"{g[i, j]:.1f}", ha="center", va="center", fontsize=8, color="white" if g[i, j] > 0.6 * g.max() else "black")
    for xy in ([[0, 0], [120, 0], [120, 80], [0, 80], [0, 0]], [[60, 0], [60, 80]], [[0, 18], [18, 18], [18, 62], [0, 62]], [[120, 18], [102, 18], [102, 62], [120, 62]]):
        a = np.array(xy); ax.plot(a[:, 0], a[:, 1], color="#555", lw=0.8)
    ax.axvline(res["height"]["mean_x"], color="#1F3A5F", lw=2, ls="--"); ax.text(res["height"]["mean_x"] + 1, 78, "mean height of defensive actions", fontsize=7, color="#1F3A5F")
    ax.set_xticks([]); ax.set_yticks([]); ax.set_title("Pressures per match by zone (attacking left to right; top = left side)", fontsize=8.5)
    b = io.BytesIO(); fig.savefig(b, format="png", dpi=110, bbox_inches="tight"); plt.close(fig); img = base64.b64encode(b.getvalue()).decode()
    pc = lambda x: f"{100 * x:.0f}%"; r = res
    css = "body{font-family:Arial,sans-serif;max-width:980px;margin:24px auto;color:#222;font-size:13px}h1,h2{color:#1F3A5F}h2{border-bottom:1px solid #ccc;padding-top:10px}table{border-collapse:collapse;width:100%;margin:6px 0}th,td{border:1px solid #ccc;padding:4px 6px;text-align:right}th{background:#E6ECF4}td:first-child,th:first-child{text-align:left}.small{color:#666;font-size:11px}img{width:70%}"
    h = [f"<html><head><meta charset='utf-8'><title>Defending: {H.escape(TEAM)}</title><style>{css}</style></head><body><h1>{H.escape(TEAM)}: how they defend</h1>",
         f"<div class='small'>{nm} matches ({per[0]['date']} to {per[-1]['date']}). Intervals: 95% bootstrap over matches. Locations are on the team's own attacking direction.</div>",
         f"<img src='data:image/png;base64,{img}'>",
         "<table><tr><th></th><th>Season</th><th>95% interval</th><th>Last 5</th></tr>",
         f"<tr><td>PPDA (opponent passes per defensive action; lower = more intense)</td><td>{r['ppda']['value']:.1f}</td><td>{r['ppda']['ci'][0]:.1f}-{r['ppda']['ci'][1]:.1f}</td><td>{r['ppda']['last5']:.1f}</td></tr>",
         f"<tr><td>Pressures per match</td><td>{r['pressures']['per_match']:.0f}</td><td>{r['pressures']['ci'][0]:.0f}-{r['pressures']['ci'][1]:.0f}</td><td>{r['pressures']['last5']:.0f}</td></tr>",
         f"<tr><td>Counter-pressures (share of pressures)</td><td>{pc(r['pressures']['counterpress_share'])}</td><td>{pc(r['pressures']['counterpress_ci'][0])}-{pc(r['pressures']['counterpress_ci'][1])}</td><td></td></tr>",
         f"<tr><td>Height of defensive actions (mean x, 0-120)</td><td>{r['height']['mean_x']:.1f}</td><td>{r['height']['ci'][0]:.1f}-{r['height']['ci'][1]:.1f}</td><td>{r['height']['last5']:.1f}</td></tr>",
         f"<tr><td>Shots conceded per match</td><td>{r['conceded']['shots_per_match']:.1f}</td><td>{r['conceded']['shots_ci'][0]:.1f}-{r['conceded']['shots_ci'][1]:.1f}</td><td>{r['conceded']['last5_shots']:.1f}</td></tr>",
         f"<tr><td>xG conceded per match</td><td>{r['conceded']['xg_per_match']:.2f}</td><td>{r['conceded']['xg_ci'][0]:.2f}-{r['conceded']['xg_ci'][1]:.2f}</td><td>{r['conceded']['last5_xg']:.2f}</td></tr></table>",
         "<h2>Where they press</h2><table><tr><th>Third</th><th>Share of pressures</th><th>Per match</th></tr>" + "".join(f"<tr><td>{t}</td><td>{pc(v['share'])}</td><td>{v['per_match']:.0f}</td></tr>" for t, v in r["pressures"]["by_third"].items()) + "</table>",
         "<p class='small'>Descriptive. PPDA as commonly defined (opponent passes in their own 60% / tackles, interceptions and fouls in the same area); StatsBomb counts all duels, so values are not comparable with other providers. Pressures and the counterpress flag are StatsBomb definitions. PPDA also depends on how much the opponent has the ball: against a team that dominates possession opponents make few passes, so its PPDA can be high even when it presses high (read it with the pressures in the final third and the height). Seasons and StatsBomb data versions differ between teams (2015/16 vs 2023/24), so compare ranks loosely. Event data do not show positions off the ball, so the defensive line itself is not observed: the height of defensive actions is a proxy.</p></body></html>"]
    open(f"{BASE}/defending_{fn}.html", "w", encoding="utf-8").write("".join(h)); print("saved", f"{BASE}/defending_{fn}.html")
