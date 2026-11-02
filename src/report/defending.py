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
- xG per shot conceded (added 26 Oct 2026, fixed before computing it): sum of opponent xG / number of opponent shots over the matches (ratio of sums,
  same shots as above). Shows whether the team concedes few good chances or many poor ones; descriptive, not graded.
- last 5: the five most recent matches. Intervals: 95% bootstrap over matches."""

import sys, io, json, copy, base64, html as H
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

MF, TEAM = sys.argv[1], sys.argv[2]
BASE = sys.argv[3] if len(sys.argv) > 3 else "."

# StatsBomb match lists have competition fields; lists made from the generic CSV can name their provider (--provider=...).
first_match = (json.load(open(MF, encoding="utf-8")) or [{}])[0]
IS_SB = "competition" in first_match
PROVIDER = first_match.get("data_provider") or ("StatsBomb" if IS_SB else "the data provider")

DEF = ("Duel", "Interception", "Foul Committed", "Ball Recovery", "Block", "Clearance")
PPDA_ACT = ("Duel", "Interception", "Foul Committed")
THIRDS = ["own third", "middle third", "final third"]


def third(x):
    if x < 40:
        return THIRDS[0]
    if x < 80:
        return THIRDS[1]
    return THIRDS[2]


def is_type(e, name):
    return e["type"]["name"] == name


def match_stats(g, gi):
    """Counts for one match, plus the team's pressures in that match."""
    ev = json.load(open(f"{BASE}/ev/{g['match_id']}.json", encoding="utf-8"))
    us = [e for e in ev if e["team"]["name"] == TEAM]
    them = [e for e in ev if e["team"]["name"] != TEAM]

    def_x = [e["location"][0] for e in us if e["type"]["name"] in DEF and e.get("location")]
    pressures = [e for e in us if is_type(e, "Pressure") and e.get("location")]
    shots = [e for e in them if is_type(e, "Shot")]

    m = {
        "gi": gi,
        "date": g["match_date"],
        "opp_pass": sum(1 for e in them if is_type(e, "Pass") and e.get("location") and e["location"][0] < 72),
        "act_hi": sum(1 for e in us if e["type"]["name"] in PPDA_ACT and e.get("location") and e["location"][0] >= 48),
        "def_actions": len(def_x),
        "def_x_sum": float(sum(def_x)),
        "pressures": len(pressures),
        "counterpress": sum(1 for e in pressures if e.get("counterpress")),
        "shots": len(shots),
        "xg": float(sum(e["shot"].get("statsbomb_xg", 0) or 0 for e in shots)),
        "has_xg": any("statsbomb_xg" in e["shot"] for e in shots),
        "dx": def_x,
    }
    points = [{"gi": gi, "x": e["location"][0], "y": e["location"][1]} for e in pressures]
    return m, points


def extract():
    matches = [g for g in json.load(open(MF, encoding="utf-8"))
               if TEAM in (g["home_team"]["home_team_name"], g["away_team"]["away_team_name"])]
    matches.sort(key=lambda g: g["match_date"])
    per, press = [], []
    for gi, g in enumerate(matches):
        m, points = match_stats(g, gi)
        per.append(m)
        press += points
    return per, press, len(matches)


def boot(stat, games, B=1000, seed=0):
    rng = np.random.default_rng(seed)
    out = [stat(rng.choice(games, len(games))) for _ in range(B)]
    return [float(np.nanpercentile(out, 2.5)), float(np.nanpercentile(out, 97.5))]


def pressure_map(grid, mean_height):
    """Heat map of pressures per match (6 x 4 zones), returned as base64 PNG."""
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    ax.imshow(grid.T, extent=[0, 120, 80, 0], cmap="Oranges", vmin=0, vmax=max(grid.max(), 0.1), aspect="equal")
    for i in range(6):
        for j in range(4):
            color = "white" if grid[i, j] > 0.6 * grid.max() else "black"
            ax.text(10 + 20 * i, 10 + 20 * j, f"{grid[i, j]:.1f}", ha="center", va="center", fontsize=8, color=color)
    lines = [
        [[0, 0], [120, 0], [120, 80], [0, 80], [0, 0]],
        [[60, 0], [60, 80]],
        [[0, 18], [18, 18], [18, 62], [0, 62]],
        [[120, 18], [102, 18], [102, 62], [120, 62]],
    ]
    for xy in lines:
        a = np.array(xy)
        ax.plot(a[:, 0], a[:, 1], color="#555", lw=0.8)
    ax.axvline(mean_height, color="#1F3A5F", lw=2, ls="--")
    ax.text(mean_height + 1, 78, "mean height of defensive actions", fontsize=7, color="#1F3A5F")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("Pressures per match by zone (attacking left to right; top = left side)", fontsize=8.5)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def pc(x):
    return f"{100 * x:.0f}%"


CSS = "body{font-family:Arial,sans-serif;max-width:980px;margin:24px auto;color:#222;font-size:13px}h1,h2{color:#1F3A5F}h2{border-bottom:1px solid #ccc;padding-top:10px}table{border-collapse:collapse;width:100%;margin:6px 0}th,td{border:1px solid #ccc;padding:4px 6px;text-align:right}th{background:#E6ECF4}td:first-child,th:first-child{text-align:left}.small{color:#666;font-size:11px}img{width:70%}"

NOTE_SB = "<p class='small'>Descriptive. PPDA as commonly defined (opponent passes in their own 60% / tackles, interceptions and fouls in the same area); StatsBomb counts all duels, so values are not comparable with other providers. Pressures and the counterpress flag are StatsBomb definitions. PPDA also depends on how much the opponent has the ball: against a team that dominates possession opponents make few passes, so its PPDA can be high even when it presses high (read it with the pressures in the final third and the height). Seasons and StatsBomb data versions differ between teams (2015/16 vs 2023/24), so compare ranks loosely. Event data do not show positions off the ball, so the defensive line itself is not observed: the height of defensive actions is a proxy.</p></body></html>"
NOTE_OTHER = "<p class='small'>Descriptive. PPDA as commonly defined (opponent passes in their own 60% / tackles, interceptions and fouls in the same area); {provider} defines duels and other defensive actions in its own way, so values are not comparable with other providers. Pressures are not in this data, so that part of the sheet is empty. PPDA also depends on how much the opponent has the ball: against a team that dominates possession opponents make few passes, so its PPDA can be high even when it presses high (read it with the height). Event data do not show positions off the ball, so the defensive line itself is not observed: the height of defensive actions is a proxy.</p></body></html>"


def html_page(r, per, nm, img, no_press, no_xg):
    p, c = r["pressures"], r["conceded"]
    h = [
        f"<html><head><meta charset='utf-8'><title>Defending: {H.escape(TEAM)}</title><style>{CSS}</style></head><body><h1>{H.escape(TEAM)}: how they defend</h1>",
        f"<div class='small'>{nm} matches ({per[0]['date']} to {per[-1]['date']}). Intervals: 95% bootstrap over matches. Locations are on the team's own attacking direction.</div>",
    ]
    if not no_press:
        h.append(f"<img src='data:image/png;base64,{img}'>")
    h.append("<table><tr><th></th><th>Season</th><th>95% interval</th><th>Last 5</th></tr>")
    h.append(f"<tr><td>PPDA (opponent passes per defensive action; lower = more intense)</td><td>{r['ppda']['value']:.1f}</td><td>{r['ppda']['ci'][0]:.1f}-{r['ppda']['ci'][1]:.1f}</td><td>{r['ppda']['last5']:.1f}</td></tr>")
    if not no_press:
        h.append(f"<tr><td>Pressures per match</td><td>{p['per_match']:.0f}</td><td>{p['ci'][0]:.0f}-{p['ci'][1]:.0f}</td><td>{p['last5']:.0f}</td></tr>")
        h.append(f"<tr><td>Counter-pressures (share of pressures)</td><td>{pc(p['counterpress_share'])}</td><td>{pc(p['counterpress_ci'][0])}-{pc(p['counterpress_ci'][1])}</td><td></td></tr>")
    h.append(f"<tr><td>Height of defensive actions (mean x, 0-120)</td><td>{r['height']['mean_x']:.1f}</td><td>{r['height']['ci'][0]:.1f}-{r['height']['ci'][1]:.1f}</td><td>{r['height']['last5']:.1f}</td></tr>")
    h.append(f"<tr><td>Shots conceded per match</td><td>{c['shots_per_match']:.1f}</td><td>{c['shots_ci'][0]:.1f}-{c['shots_ci'][1]:.1f}</td><td>{c['last5_shots']:.1f}</td></tr>")
    if not no_xg:
        h.append(f"<tr><td>xG conceded per match</td><td>{c['xg_per_match']:.2f}</td><td>{c['xg_ci'][0]:.2f}-{c['xg_ci'][1]:.2f}</td><td>{c['last5_xg']:.2f}</td></tr>")
        h.append(f"<tr><td>xG per shot conceded</td><td>{c['xg_per_shot']:.3f}</td><td>{c['xg_per_shot_ci'][0]:.3f}-{c['xg_per_shot_ci'][1]:.3f}</td><td>{c['last5_xg_per_shot']:.3f}</td></tr>")
    h.append("</table>")
    if not no_press:
        h.append("<h2>Where they press</h2><table><tr><th>Third</th><th>Share of pressures</th><th>Per match</th></tr>")
        for t, v in p["by_third"].items():
            h.append(f"<tr><td>{t}</td><td>{pc(v['share'])}</td><td>{v['per_match']:.0f}</td></tr>")
        h.append("</table>")
    h.append(NOTE_SB if IS_SB else NOTE_OTHER.format(provider=H.escape(PROVIDER)))
    return "".join(h)


if __name__ == "__main__":
    per, press, nm = extract()
    fn = TEAM.replace(" ", "_")
    if sum(m["pressures"] for m in per) == 0 and sum(m["def_actions"] for m in per) == 0:
        sys.exit(
            f"No defensive events for {TEAM}: this sheet needs StatsBomb-style Pressure/Duel/Interception events (not in the generic CSV)."
        )
    by = {m["gi"]: m for m in per}
    games = np.arange(nm)
    last = games[-5:]

    def total(key, gs):
        return sum(by[g][key] for g in gs)

    def ppda(gs):
        return total("opp_pass", gs) / max(total("act_hi", gs), 1)

    def per_match(key):
        return lambda gs: total(key, gs) / len(gs)

    def height(gs):
        return total("def_x_sum", gs) / max(total("def_actions", gs), 1)

    def counterpress(gs):
        return total("counterpress", gs) / max(total("pressures", gs), 1)

    def xg_per_shot(gs):
        return total("xg", gs) / max(total("shots", gs), 1)

    all_x = [x for m in per for x in m["dx"]]
    n_press = max(len(press), 1)
    per_third = {t: sum(1 for p in press if third(p["x"]) == t) for t in THIRDS}
    grid, _, _ = np.histogram2d([p["x"] for p in press], [p["y"] for p in press], bins=[6, 4], range=[[0, 120], [0, 80]])
    pressures, shots, xg = per_match("pressures"), per_match("shots"), per_match("xg")

    res = {
        "team": TEAM,
        "matches": int(nm),
        "ppda": {
            "value": ppda(games),
            "ci": boot(ppda, games),
            "last5": ppda(last),
            "opp_passes": int(total("opp_pass", games)),
            "actions": int(total("act_hi", games)),
        },
        "pressures": {
            "per_match": pressures(games),
            "ci": boot(pressures, games),
            "last5": pressures(last),
            "by_third": {t: {"share": per_third[t] / n_press, "per_match": per_third[t] / nm} for t in THIRDS},
            "counterpress_share": counterpress(games),
            "counterpress_ci": boot(counterpress, games),
            "grid_per_match": (grid / nm).round(3).tolist(),
        },
        "height": {
            "mean_x": height(games),
            "ci": boot(height, games),
            "median_x": float(np.median(all_x)) if all_x else None,
            "last5": height(last),
            "actions_per_match": per_match("def_actions")(games),
        },
        "conceded": {
            "shots_per_match": shots(games),
            "shots_ci": boot(shots, games),
            "xg_per_match": xg(games),
            "xg_ci": boot(xg, games),
            "last5_shots": shots(last),
            "last5_xg": xg(last),
            "xg_per_shot": xg_per_shot(games),
            "xg_per_shot_ci": boot(xg_per_shot, games),
            "last5_xg_per_shot": xg_per_shot(last),
        },
    }

    # Data without pressures or xG (e.g. Wyscout via the generic CSV): those parts are null, never zeros that would rank as real values.
    no_press = sum(m["pressures"] for m in per) == 0
    no_xg = not any(m["has_xg"] for m in per)
    out = copy.deepcopy(res)
    if no_press:
        out["pressures"] = None
    if no_xg:
        for k in ("xg_per_match", "xg_ci", "last5_xg", "xg_per_shot", "xg_per_shot_ci", "last5_xg_per_shot"):
            out["conceded"][k] = None
    json.dump(out, open(f"{BASE}/defending_{fn}.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)

    img = pressure_map(np.array(res["pressures"]["grid_per_match"]), res["height"]["mean_x"])
    open(f"{BASE}/defending_{fn}.html", "w", encoding="utf-8").write(html_page(res, per, nm, img, no_press, no_xg))
    print("saved", f"{BASE}/defending_{fn}.html")
