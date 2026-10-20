"""Threat sheet: how much a team moves the ball into dangerous zones with passes and carries (Expected Threat, xT), where it does it from, who does it,
and how much threat it concedes. Descriptive, one page; no hypothesis was tested.
Usage:  python xthreat.py <matches.json> "<Team>" [data_dir=.]
Output in data_dir: xthreat_<Team>.html, xthreat_<Team>.json and xt_clips_<Team>.csv (same columns as clips_<Team>.csv, plus player and xt).
Uses the grid of xt_model.py (xt_grid.json, fitted once on the matches of the 10 thesis teams), so the same zone values for every team.
Needs StatsBomb-style pass outcomes (completed or not) and pass types: the generic CSV has neither, so with it the script stops with a message.
Definitions (fixed before looking at any team):
- xT added: for each completed open-play pass and carry of the team (as in xt_model.py), xT(end zone) - xT(start zone); summed per match. Back passes count negative.
  Failed passes are NOT subtracted (Singh's definition); 'threat given up' reports them separately: the xT of the start zone of each incomplete open-play pass.
- by type: passes and carries. By origin: start of the move, thirds of x (own < 40, middle, final >= 80) times channels of y (left < 80/3, centre, right > 160/3;
  StatsBomb y small = left). Map: xT added per match by start zone on a 6 x 4 grid.
- players: top 5 by total xT added; per match = per match in which the player has at least one event; share of the team's total.
- conceded: the same xT added, computed on the opponents' moves.
- clips: the 40 moves of the season with the largest xT added (family 'xT pass' / 'xT carry'); ended_in_shot = the team shoots later in the same StatsBomb possession.
- last 5: the five most recent matches. Intervals: 95% bootstrap over matches (1000 resamples, seed 0).
Not done on purpose: xT by sequence family. The families were already tested against a simple end-position rule for shots (pre-registered, negative);
xT is itself a value of the end position, so splitting it by family would be a new outcome tried after seeing that result (CLAUDE.md rule 3)."""

import sys, os, io, csv, json, base64, html as H
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xt_model import load_grid, zone, move, NX, NY

MF, TEAM = sys.argv[1], sys.argv[2]
BASE = sys.argv[3] if len(sys.argv) > 3 else "."
THIRDS = ["own third", "middle third", "final third"]
CHAN = ["left", "centre", "right"]
third = lambda x: THIRDS[0] if x < 40 else (THIRDS[1] if x < 80 else THIRDS[2])
chan = lambda y: CHAN[0] if y < 80 / 3 else (CHAN[2] if y > 160 / 3 else CHAN[1])
XT, GRID = load_grid()
val = lambda loc: float(XT[zone(loc)])


def extract():
    ms = sorted(
        [
            g
            for g in json.load(open(MF, encoding="utf-8"))
            if TEAM in (g["home_team"]["home_team_name"], g["away_team"]["away_team_name"])
        ],
        key=lambda g: g["match_date"],
    )
    per, A, outcomes = [], [], 0
    for gi, g in enumerate(ms):
        ev = json.load(open(f"{BASE}/ev/{g['match_id']}.json", encoding="utf-8"))
        opp = (
            g["away_team"]["away_team_name"]
            if g["home_team"]["home_team_name"] == TEAM
            else g["home_team"]["home_team_name"]
        )
        shot_pos = {e["possession"] for e in ev if e["type"]["name"] == "Shot" and e["team"]["name"] == TEAM}
        m = dict(
            gi=gi,
            date=g["match_date"],
            xt=0.0,
            xt_pass=0.0,
            xt_carry=0.0,
            given_up=0.0,
            conceded=0.0,
            origin={f"{t}|{c}": 0.0 for t in THIRDS for c in CHAN},
        )
        for e in ev:
            if e["type"]["name"] == "Pass" and "outcome" in (e.get("pass") or {}):
                outcomes += 1
            mv = move(e)
            if mv is None:
                continue
            s, t, done, kind = mv
            us = e["team"]["name"] == TEAM
            if not done:
                if us and kind == "pass":
                    m["given_up"] += val(s)
                continue
            d = val(t) - val(s)
            if not us:
                m["conceded"] += d
                continue
            m["xt"] += d
            m[f"xt_{kind}"] += d
            m["origin"][f"{third(s[0])}|{chan(s[1])}"] += d
            A.append(
                dict(
                    gi=gi,
                    match=g["match_id"],
                    date=g["match_date"],
                    opponent=opp,
                    half=e["period"],
                    minute=e["minute"],
                    second=e["second"],
                    kind=kind,
                    player=(e.get("player") or {}).get("name", ""),
                    start_type=(e.get("play_pattern") or {}).get("name", ""),
                    x=s[0],
                    y=s[1],
                    x1=t[0],
                    y1=t[1],
                    dur=float(e.get("duration") or 0),
                    shot=int(e.get("possession") in shot_pos),
                    xt=d,
                )
            )
        m["players"] = sorted(
            {(e.get("player") or {}).get("name") for e in ev if e["team"]["name"] == TEAM and e.get("player")}
        )
        per.append(m)
    return per, A, len(ms), outcomes


def boot(stat, games, B=1000, seed=0):
    rng = np.random.default_rng(seed)
    out = [stat(rng.choice(games, len(games))) for _ in range(B)]
    return [float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))]


if __name__ == "__main__":
    per, A, nm, outcomes = extract()
    fn = TEAM.replace(" ", "_")
    if outcomes == 0:
        sys.exit(
            f"No pass outcomes for {TEAM}: xT needs to know which passes were completed (StatsBomb pass outcome), which the generic CSV does not carry."
        )
    by = {m["gi"]: m for m in per}
    games = np.arange(nm)
    last = games[-5:]
    pm = lambda key: (lambda gs: sum(by[g][key] for g in gs) / len(gs))
    row = lambda key: dict(per_match=pm(key)(games), ci=boot(pm(key), games), last5=pm(key)(last))
    origin = {k: sum(m["origin"][k] for m in per) / nm for k in per[0]["origin"]}
    grid = np.zeros((6, 4))
    for a in A:
        grid[min(int(a["x"] / 20), 5), min(int(a["y"] / 20), 3)] += a["xt"]
    tot = {}
    played = {}
    for a in A:
        if a["player"]:
            tot[a["player"]] = tot.get(a["player"], 0.0) + a["xt"]
    for m in per:
        for p in m["players"]:
            played[p] = played.get(p, 0) + 1
    team_tot = sum(m["xt"] for m in per)
    top = sorted(tot.items(), key=lambda kv: -kv[1])[:5]
    res = {
        "team": TEAM,
        "matches": int(nm),
        "period": f"{per[0]['date']} to {per[-1]['date']}",
        "grid": {k: GRID[k] for k in ("nx", "ny", "matches", "moves", "shots", "goals")},
        "xt": row("xt"),
        "xt_pass": row("xt_pass"),
        "xt_carry": row("xt_carry"),
        "given_up": row("given_up"),
        "conceded": row("conceded"),
        "origin_per_match": origin,
        "map_per_match": (grid / nm).round(4).tolist(),
        "players": [
            dict(
                player=p,
                xt=v,
                per_match=v / played.get(p, 1),
                matches=played.get(p, 0),
                share=v / team_tot if team_tot else None,
            )
            for p, v in top
        ],
    }
    json.dump(res, open(f"{BASE}/xthreat_{fn}.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)

    best = sorted(A, key=lambda a: -a["xt"])[:40]
    with open(f"{BASE}/xt_clips_{fn}.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "family",
                "match",
                "date",
                "opponent",
                "half",
                "minute",
                "second",
                "start_type",
                "passes",
                "duration_s",
                "ended_in_shot",
                "player",
                "xt",
            ]
        )
        for a in sorted(best, key=lambda a: (a["date"], a["half"], a["minute"], a["second"])):
            w.writerow(
                [
                    f"xT {a['kind']}",
                    a["match"],
                    a["date"],
                    a["opponent"],
                    a["half"],
                    a["minute"],
                    a["second"],
                    a["start_type"],
                    int(a["kind"] == "pass"),
                    round(a["dur"]),
                    a["shot"],
                    a["player"],
                    f"{a['xt']:.4f}",
                ]
            )

    fig, axs = plt.subplots(1, 2, figsize=(11, 3.8))
    for ax, g, title, cm, fmt in (
        (axs[0], XT, f"xT of each zone (same grid for every team; {GRID['matches']} matches)", "Greens", ".2f"),
        (axs[1], grid / nm, "xT added per match by start zone of the move", "Purples", ".2f"),
    ):
        ax.imshow(
            np.array(g).T,
            extent=[0, 120, 80, 0],
            cmap=cm,
            vmin=min(0, float(np.min(g))),
            vmax=max(float(np.max(g)), 1e-6),
            aspect="equal",
        )
        if g is not XT:
            for i in range(6):
                for j in range(4):
                    ax.text(
                        10 + 20 * i,
                        10 + 20 * j,
                        format(g[i, j], fmt),
                        ha="center",
                        va="center",
                        fontsize=8,
                        color="white" if g[i, j] > 0.6 * np.max(g) else "black",
                    )
        for xy in (
            [[0, 0], [120, 0], [120, 80], [0, 80], [0, 0]],
            [[60, 0], [60, 80]],
            [[0, 18], [18, 18], [18, 62], [0, 62]],
            [[120, 18], [102, 18], [102, 62], [120, 62]],
        ):
            a = np.array(xy)
            ax.plot(a[:, 0], a[:, 1], color="#555", lw=0.8)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(title + "\n(attacking left to right; top = left side)", fontsize=8.5)
    b = io.BytesIO()
    fig.savefig(b, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    img = base64.b64encode(b.getvalue()).decode()
    r = res
    f2 = lambda v: f"{v:.2f}"
    tr = (
        lambda lab, k: f"<tr><td>{lab}</td><td>{f2(r[k]['per_match'])}</td><td>{f2(r[k]['ci'][0])} to {f2(r[k]['ci'][1])}</td><td>{f2(r[k]['last5'])}</td></tr>"
    )
    css = "body{font-family:Arial,sans-serif;max-width:980px;margin:24px auto;color:#222;font-size:13px}h1,h2{color:#1F3A5F}h2{border-bottom:1px solid #ccc;padding-top:10px}table{border-collapse:collapse;width:100%;margin:6px 0}th,td{border:1px solid #ccc;padding:4px 6px;text-align:right}th{background:#E6ECF4}td:first-child,th:first-child{text-align:left}.small{color:#666;font-size:11px}img{width:100%}"
    h = [
        f"<html><head><meta charset='utf-8'><title>Threat: {H.escape(TEAM)}</title><style>{css}</style></head><body><h1>{H.escape(TEAM)}: how they move the ball into danger</h1>",
        f"<div class='small'>{nm} matches ({r['period']}). Expected Threat (xT, Singh 2018): value of a zone = chance that holding the ball there leads to a goal in the next actions. "
        "A move's xT = value where it ends minus value where it starts. Intervals: 95% bootstrap over matches.</div>",
        f"<img src='data:image/png;base64,{img}'>",
        "<table><tr><th>Per match</th><th>Season</th><th>95% interval</th><th>Last 5</th></tr>",
        tr("xT added by completed passes and carries", "xt"),
        tr("&nbsp;&nbsp;from passes", "xt_pass"),
        tr("&nbsp;&nbsp;from carries", "xt_carry"),
        tr("Threat given up (xT of the start zone of incomplete passes; not subtracted above)", "given_up"),
        tr("xT conceded (opponents' completed moves)", "conceded"),
        "</table>",
        "<h2>Where the threat comes from (xT added per match, by start of the move)</h2><table><tr><th>Third</th>"
        + "".join(f"<th>{c}</th>" for c in CHAN)
        + "</tr>"
        + "".join(
            f"<tr><td>{t}</td>" + "".join(f"<td>{f2(origin[f'{t}|{c}'])}</td>" for c in CHAN) + "</tr>" for t in THIRDS
        )
        + "</table>",
        "<h2>Who adds it</h2><table><tr><th>Player</th><th>xT total</th><th>Per match played</th><th>Matches</th><th>Share of team</th></tr>"
        + "".join(
            f"<tr><td>{H.escape(p['player'])}</td><td>{f2(p['xt'])}</td><td>{f2(p['per_match'])}</td><td>{p['matches']}</td><td>{100 * p['share']:.0f}%</td></tr>"
            for p in r["players"]
        )
        + "</table>",
        f"<p class='small'>Clip list: xt_clips_{fn}.csv, the 40 moves with the largest xT added. Descriptive. xT values only where the ball goes, not how: it does not see pressure, "
        "defenders' positions or the receiver's situation, and failed passes are not penalised in the main figure (see 'threat given up'). The grid is fitted on the matches of the 10 thesis teams "
        f"and their opponents ({GRID['matches']} matches, {GRID['shots']} open-play shots), seasons 2015/16 and 2023/24, so values in zones with few shots are rough. "
        "xT is not computed by sequence family on purpose: the families did not explain shots better than a simple rule on where the sequence ends (pre-registered test, 10 teams).</p></body></html>",
    ]
    open(f"{BASE}/xthreat_{fn}.html", "w", encoding="utf-8").write("".join(h))
    print("saved", f"{BASE}/xthreat_{fn}.html")
