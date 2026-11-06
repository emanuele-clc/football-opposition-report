"""Restart sheet: how a team plays out from goal kicks, keeper distributions and throw-ins. Descriptive, one page, for pressing plans.
Usage:  python restarts.py <matches.json> "<Team>" [data_dir=.]
Output in data_dir: restarts_<Team>.html, restarts_<Team>.json and restart_clips_<Team>.csv (every restart possession with its label, same columns as clips_<Team>.csv).
Definitions (fixed before looking at any team):
- restart possession: possession of the team whose play pattern is From Goal Kick, From Keeper or From Throw In; throw-ins split by own half (x < 60) and opponent half.
- first pass: first pass of the team in the possession. Short = under 30 m (as in the long-pass share of the report). Side = end of the first pass, y in thirds (left, centre, right; StatsBomb y small = left).
- outcomes of the possession: reached the opponent half (any team action ending at x >= 60), reached the final third (x >= 80), shot, ended in own half (no shot and the last team action ends at x < 60: ball lost, out of play or foul).
Intervals are 95% bootstrap over matches. 'Last 5' uses only the five most recent matches and is shown with its own interval: with 5 matches it is wide."""

import sys, json, html as H
import numpy as np, pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from common import team_matches, opponent, boot, pc, ci, fig_png

MF, TEAM = sys.argv[1], sys.argv[2]
BASE = sys.argv[3] if len(sys.argv) > 3 else "."
PP = {"From Goal Kick": "Goal kick", "From Keeper": "Keeper", "From Throw In": "Throw-in"}
KINDS = ["Goal kick", "Keeper", "Throw-in own half", "Throw-in opp. half"]
METRICS = [
    ("short", "First pass short (< 30 m)"),
    ("left", "First pass to the left"),
    ("centre", "First pass central"),
    ("right", "First pass to the right"),
    ("opp_half", "Reached the opponent half"),
    ("final_third", "Reached the final third"),
    ("lost_own_half", "Possession ended in own half (lost, out or foul)"),
    ("shot", "Ended in a shot"),
]


def end_of(e):
    t = e["type"]["name"]
    if t == "Pass":
        return e["pass"]["end_location"]
    if t == "Carry":
        return e["carry"]["end_location"]
    return e.get("location")


def side_of(y):
    if y < 80 / 3:
        return "left"
    if y > 160 / 3:
        return "right"
    return "centre"


def restart_row(es, g, gi, opp):
    """One restart possession (the team's actions in it), or None if it has no pass or no location."""
    passes = [e for e in es if e["type"]["name"] == "Pass"]
    if not passes or es[0].get("location") is None:
        return None
    p0 = passes[0]
    kind = PP[es[0]["play_pattern"]["name"]]
    if kind == "Throw-in":
        kind += " own half" if es[0]["location"][0] < 60 else " opp. half"
    xs = [end_of(e)[0] for e in es if end_of(e) is not None]
    shot = any(e["type"]["name"] == "Shot" for e in es)
    y = p0["pass"]["end_location"][1]
    t0 = es[0]["minute"] * 60 + es[0]["second"]
    t1 = es[-1]["minute"] * 60 + es[-1]["second"]
    return {
        "match": g["match_id"],
        "gi": gi,
        "data": g["match_date"],
        "avv": opp,
        "tempo": es[0]["period"],
        "minuto": es[0]["minute"],
        "sec": es[0]["second"],
        "kind": kind,
        "short": int(p0["pass"].get("length", 0) < 30),
        "side": side_of(y),
        "n_pass": len(passes),
        "dur": max(t1 - t0, 0),
        "opp_half": int(max(xs) >= 60),
        "final_third": int(max(xs) >= 80),
        "shot": int(shot),
        "lost_own_half": int(not shot and xs[-1] < 60),
        "px0": p0["location"][0],
        "py0": p0["location"][1],
        "px1": p0["pass"]["end_location"][0],
        "py1": y,
        "receiver": (p0["pass"].get("recipient") or {}).get("name"),
    }


def extract():
    matches = team_matches(MF, TEAM)
    rows = []
    for gi, g in enumerate(matches):
        opp = opponent(g, TEAM)
        poss = {}
        for e in json.load(open(f"{BASE}/ev/{g['match_id']}.json", encoding="utf-8")):
            if (e.get("possession_team", {}).get("name") == TEAM
                    and e["team"]["name"] == TEAM
                    and e["play_pattern"]["name"] in PP
                    and e["type"]["name"] in ("Pass", "Carry", "Shot", "Dribble")):
                poss.setdefault(e["possession"], []).append(e)
        for es in poss.values():
            row = restart_row(es, g, gi, opp)
            if row:
                rows.append(row)
    return pd.DataFrame(rows), len(matches)


PITCH_LINES = [
    [[0, 0], [120, 0], [120, 80], [0, 80], [0, 0]],
    [[60, 0], [60, 80]],
    [[0, 18], [18, 18], [18, 62], [0, 62]],
    [[120, 18], [102, 18], [102, 62], [120, 62]],
    [[0, 30], [6, 30], [6, 50], [0, 50]],
]


def pitch(d, title):
    """First pass of each restart: start to end on the pitch (own goal on the left), short in blue, long in orange; thick arrows = mean of each group."""
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    ax.set_facecolor("#3d7a3d")
    for xy in PITCH_LINES:
        a = np.array(xy)
        ax.plot(a[:, 0], a[:, 1], color="white", lw=1)
    for short, color in ((1, "#4FA3FF"), (0, "#FF9F40")):
        q = d[d.short == short]
        for r in q.itertuples():
            ax.plot([r.px0, r.px1], [r.py0, r.py1], color=color, lw=0.5, alpha=0.35)
        ax.scatter(q.px1, q.py1, s=9, color=color, alpha=0.8, label=f"{'short' if short else 'long'} ({len(q)})")
        for side in ("left", "centre", "right"):
            z = q[q.side == side]
            if len(z) >= max(5, 0.1 * len(d)):
                ax.annotate("", (z.px1.mean(), z.py1.mean()), (z.px0.mean(), z.py0.mean()),
                            arrowprops=dict(arrowstyle="-|>", color=color, lw=2.5))
    ax.set_xlim(-2, 122)
    ax.set_ylim(82, -2)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.legend(loc="lower right", fontsize=8)
    ax.set_title(f"{title}: where the first pass goes (attacking left to right; top = left side)", fontsize=9)
    return fig_png(fig)


def summarise(df, nm):
    games = np.arange(nm)
    last = games[-5:]
    res = {"team": TEAM, "matches": int(nm), "kinds": {}}
    for k in KINDS:
        d = df[df.kind == k]
        d5 = d[d.gi.isin(last)]
        if not len(d):
            continue
        metrics = {}
        for m, _ in METRICS:
            metrics[m] = {
                "season": float(d[m].mean()),
                "ci": boot(d[m].values, d.gi.values, games),
                "last5": float(d5[m].mean()) if len(d5) else None,
                "last5_ci": boot(d5[m].values, d5.gi.values, last) if len(d5) else None,
            }
        kind = {
            "n": int(len(d)),
            "per_match": float(len(d) / nm),
            "n_last5": int(len(d5)),
            "passes": float(d.n_pass.mean()),
            "metrics": metrics,
        }
        if d.receiver.notna().mean() > 0.5:
            kind["receivers"] = {p: {"n": int(c), "share": float(c / len(d))} for p, c in d.receiver.value_counts().head(5).items()}
        # short vs long first passes behave differently: outcome by first-pass length
        kind["by_length"] = {}
        for label, q in (("short", d[d.short == 1]), ("long", d[d.short == 0])):
            if len(q):
                kind["by_length"][label] = {
                    "n": int(len(q)),
                    "opp_half": float(q.opp_half.mean()),
                    "lost_own_half": float(q.lost_own_half.mean()),
                    "shot": float(q.shot.mean()),
                }
        res["kinds"][k] = kind
    return res


def write_clips(df, path):
    family = [f"{r.kind} {'short' if r.short else 'long'} {r.side}" for r in df.itertuples()]
    cols = ["family", "match", "data", "avv", "tempo", "minuto", "sec", "kind", "n_pass", "dur", "shot"]
    names = {
        "data": "date",
        "avv": "opponent",
        "tempo": "half",
        "minuto": "minute",
        "sec": "second",
        "kind": "start_type",
        "n_pass": "passes",
        "dur": "duration_s",
        "shot": "ended_in_shot",
    }
    clips = df.assign(family=family).sort_values(["family", "data", "tempo", "minuto", "sec"])
    clips[cols].rename(columns=names).to_csv(path, index=False)


CSS = "body{font-family:Arial,sans-serif;max-width:980px;margin:24px auto;color:#222;font-size:13px}h1,h2{color:#1F3A5F}h2{border-bottom:1px solid #ccc;padding-top:10px}table{border-collapse:collapse;width:100%;margin:6px 0}th,td{border:1px solid #ccc;padding:4px 6px;text-align:right}th{background:#E6ECF4}td:first-child,th:first-child{text-align:left}.small{color:#666;font-size:11px}.diff{background:#FFF4D6}"


def html_page(res, df, nm, fn):
    h = [
        f"<html><head><meta charset='utf-8'><title>Restarts: {H.escape(TEAM)}</title><style>{CSS}</style></head><body><h1>How {H.escape(TEAM)} play out from restarts</h1>",
        f"<div class='small'>{nm} matches ({df.data.min()} to {df.data.max()}). Every possession starting from a goal kick, a keeper distribution or a throw-in. Intervals: 95% bootstrap over matches. 'Last 5' = the five most recent matches; highlighted when its value lies outside the season interval (a hint to check on video, not proof of a change).</div>",
    ]
    for k, r in res["kinds"].items():
        h.append(f"<h2>{k}: {r['n']} possessions ({r['per_match']:.1f} per match), {r['passes']:.1f} passes on average</h2><table><tr><th></th><th>Season</th><th>95% interval</th><th>Last 5 ({r['n_last5']})</th><th>Last 5 interval</th></tr>")
        for m, name in METRICS:
            v = r["metrics"][m]
            outside = v["last5"] is not None and not (v["ci"][0] <= v["last5"] <= v["ci"][1])
            h.append(f"<tr{' class=diff' if outside else ''}><td>{name}</td><td>{pc(v['season'])}</td><td>{ci(v['ci'])}</td><td>{pc(v['last5'])}</td><td>{ci(v['last5_ci'])}</td></tr>")
        h.append("</table>")
        if k in ("Goal kick", "Keeper"):
            h.append(f"<img src='data:image/png;base64,{pitch(df[df.kind == k], k)}' style='width:70%'>")
        if r.get("receivers"):
            who = ", ".join(f"{H.escape(p)} {pc(q['share'])}" for p, q in r["receivers"].items())
            h.append(f"<p><b>First pass received by:</b> {who} (completed passes only).</p>")
        if len(r["by_length"]) == 2:
            h.append("<table><tr><th>First pass</th><th>n</th><th>Reached opponent half</th><th>Ended in own half</th><th>Shot</th></tr>")
            for lb, q in r["by_length"].items():
                h.append(f"<tr><td>{lb}</td><td>{q['n']}</td><td>{pc(q['opp_half'])}</td><td>{pc(q['lost_own_half'])}</td><td>{pc(q['shot'])}</td></tr>")
            h.append("</table>")
    h.append(f"<p class='small'>Clips: restart_clips_{fn}.csv lists every possession above, labelled e.g. 'Goal kick short left'; convert it with src/report/clips_to_xml.py to import into a video tool. Limits: event data only, so the opponent's press and off-ball positions are not seen; 'ended in own half' uses the last recorded action of the possession.</p></body></html>")
    return "".join(h)


if __name__ == "__main__":
    df, nm = extract()
    fn = TEAM.replace(" ", "_")
    for s in ("left", "centre", "right"):
        df[s] = (df.side == s).astype(int)
    res = summarise(df, nm)
    json.dump(res, open(f"{BASE}/restarts_{fn}.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    write_clips(df, f"{BASE}/restart_clips_{fn}.csv")
    open(f"{BASE}/restarts_{fn}.html", "w", encoding="utf-8").write(html_page(res, df, nm, fn))
    print("saved", f"{BASE}/restarts_{fn}.html")
