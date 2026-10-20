"""Set-piece sheet: how a team takes corners and free kicks in the attacking half. Descriptive, one page.
Usage:  python setpieces.py <matches.json> "<Team>" [data_dir=.]
Output in data_dir: setpieces_<Team>.html, setpieces_<Team>.json and setpiece_clips_<Team>.csv (same columns as clips_<Team>.csv).
Definitions (same delivery zones as the L3 corner study, src/week1/corners_leverkusen.py; event data only, no 360 frames needed):
- corner: possession of the team with play pattern From Corner; delivery = first pass (or shot) of the team. Side: corner taken from y < 40 = left, else right.
  Zone of the delivery end: short / outside box (x < 102 or less than 18 from the corner's touchline), near post (18-30), centre (30-50), far post (> 50).
- attacking free kick: possession From Free Kick whose first action is at x >= 80. Direct shot, cross into the box (pass ending at x >= 102, 18 <= y <= 62) or played short.
- outcomes: shot in the possession, goal, xG of the shots (only if the data contain xG), the taker and the player who receives the delivery (only if the data contain player names).
Intervals are 95% bootstrap over matches. With few corners per match, zone shares from under 10 matches are rough."""

import sys, os, json, collections, html as H
import numpy as np, pandas as pd

MF, TEAM = sys.argv[1], sys.argv[2]
BASE = sys.argv[3] if len(sys.argv) > 3 else "."
ZONES = ["short / outside box", "near post", "centre", "far post"]


def zone(end, y0):
    d = end[1] if y0 < 40 else 80 - end[1]
    if end[0] < 102 or d < 18:
        return ZONES[0]
    return ZONES[1] if d < 30 else (ZONES[2] if d <= 50 else ZONES[3])


def name(e, k="player"):
    v = e.get(k) if k == "player" else (e.get("pass") or {}).get("recipient")
    return v.get("name") if isinstance(v, dict) else None


def extract():
    ms = sorted(
        [
            g
            for g in json.load(open(MF, encoding="utf-8"))
            if TEAM in (g["home_team"]["home_team_name"], g["away_team"]["away_team_name"])
        ],
        key=lambda g: g["match_date"],
    )
    rows = []
    for gi, g in enumerate(ms):
        opp = (
            g["away_team"]["away_team_name"]
            if g["home_team"]["home_team_name"] == TEAM
            else g["home_team"]["home_team_name"]
        )
        poss = collections.OrderedDict()
        for e in json.load(open(f"{BASE}/ev/{g['match_id']}.json", encoding="utf-8")):
            if (
                e.get("possession_team", {}).get("name") == TEAM
                and e["team"]["name"] == TEAM
                and e["play_pattern"]["name"] in ("From Corner", "From Free Kick")
                and e["type"]["name"] in ("Pass", "Carry", "Shot", "Dribble")
            ):
                poss.setdefault(e["possession"], []).append(e)
        for pid, es in poss.items():
            e0 = next((e for e in es if e["type"]["name"] in ("Pass", "Shot")), None)
            if e0 is None or e0.get("location") is None:
                continue
            x0, y0 = e0["location"][:2]
            corner = es[0]["play_pattern"]["name"] == "From Corner"
            if not corner and x0 < 80:
                continue
            shots = [e for e in es if e["type"]["name"] == "Shot"]
            xg = [s.get("shot", {}).get("statsbomb_xg") for s in shots]
            r = dict(
                match=g["match_id"],
                gi=gi,
                data=g["match_date"],
                avv=opp,
                tempo=es[0]["period"],
                minuto=es[0]["minute"],
                sec=es[0]["second"],
                n_pass=sum(e["type"]["name"] == "Pass" for e in es),
                dur=max(es[-1]["minute"] * 60 + es[-1]["second"] - es[0]["minute"] * 60 - es[0]["second"], 0),
                shot=int(bool(shots)),
                goal=int(any(s.get("shot", {}).get("outcome", {}).get("name") == "Goal" for s in shots)),
                xg=(
                    float(sum(v for v in xg if v is not None))
                    if shots and all(v is not None for v in xg)
                    else (0.0 if not shots else np.nan)
                ),
                taker=name(e0),
                receiver=name(e0, "recipient") if e0["type"]["name"] == "Pass" else None,
                side="left" if y0 < 40 else "right",
            )
            if corner:
                r["kind"] = "Corner"
                r["zone"] = zone(e0["pass"]["end_location"], y0) if e0["type"]["name"] == "Pass" else "direct shot"
            else:
                r["kind"] = "Free kick"
                if e0["type"]["name"] == "Shot":
                    r["zone"] = "direct shot"
                else:
                    ex, ey = e0["pass"]["end_location"][:2]
                    r["zone"] = "cross into box" if ex >= 102 and 18 <= ey <= 62 else "played short / wide"
            rows.append(r)
    return pd.DataFrame(rows), len(ms)


def boot(v, gi, games, B=1000, seed=0):
    rng = np.random.default_rng(seed)
    by = {g: v[gi == g] for g in games}
    out = []
    for _ in range(B):
        s = np.concatenate([by[g] for g in rng.choice(games, len(games))])
        out.append(s.mean() if len(s) else np.nan)
    return [float(np.nanpercentile(out, 2.5)), float(np.nanpercentile(out, 97.5))]


if __name__ == "__main__":
    df, nm = extract()
    fn = TEAM.replace(" ", "_")
    games = np.arange(nm)
    res = {"team": TEAM, "matches": int(nm), "kinds": {}}
    has_xg = len(df) and df.xg.notna().all() and df.shot.sum() > 0
    has_names = len(df) and df.taker.notna().mean() > 0.5
    for k, zs in (
        ("Corner", ZONES + ["direct shot"]),
        ("Free kick", ["cross into box", "played short / wide", "direct shot"]),
    ):
        d = df[df.kind == k] if len(df) else df
        if not len(d):
            continue
        gi = d.gi.values
        r = dict(
            n=int(len(d)),
            per_match=float(len(d) / nm),
            shot=float(d.shot.mean()),
            shot_ci=boot(d.shot.values, gi, games),
            goals=int(d.goal.sum()),
            xg=float(d.xg.mean()) if has_xg else None,
            zones={},
            by_side={},
        )
        for z in zs:
            m = (d.zone == z).values.astype(float)
            if m.sum():
                r["zones"][z] = dict(
                    n=int(m.sum()),
                    share=float(m.mean()),
                    ci=boot(m, gi, games),
                    shot=float(d.shot[d.zone == z].mean()),
                    xg=float(d.xg[d.zone == z].mean()) if has_xg else None,
                )
        if k == "Corner":
            for s in ("left", "right"):
                q = d[d.side == s]
                if len(q):
                    r["by_side"][s] = dict(
                        n=int(len(q)), zones={z: float((q.zone == z).mean()) for z in zs if (q.zone == z).any()}
                    )
        if has_names:
            r["takers"] = d.taker.value_counts().head(3).to_dict()
            r["receivers"] = d.receiver.dropna().value_counts().head(5).to_dict()
        res["kinds"][k] = r
    json.dump(res, open(f"{BASE}/setpieces_{fn}.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    if len(df):
        df.assign(family=[f"{r.kind} {r.zone}" for r in df.itertuples()], start_type=df.kind).sort_values(
            ["family", "data", "tempo", "minuto", "sec"]
        )[["family", "match", "data", "avv", "tempo", "minuto", "sec", "start_type", "n_pass", "dur", "shot"]].rename(
            columns={
                "data": "date",
                "avv": "opponent",
                "tempo": "half",
                "minuto": "minute",
                "sec": "second",
                "n_pass": "passes",
                "dur": "duration_s",
                "shot": "ended_in_shot",
            }
        ).to_csv(
            f"{BASE}/setpiece_clips_{fn}.csv", index=False
        )
    pc = lambda x: "" if x is None else f"{100 * x:.0f}%"
    ci = lambda c: f"{100 * c[0]:.0f}-{100 * c[1]:.0f}%"
    css = "body{font-family:Arial,sans-serif;max-width:980px;margin:24px auto;color:#222;font-size:13px}h1,h2{color:#1F3A5F}h2{border-bottom:1px solid #ccc;padding-top:10px}table{border-collapse:collapse;width:100%;margin:6px 0}th,td{border:1px solid #ccc;padding:4px 6px;text-align:right}th{background:#E6ECF4}td:first-child,th:first-child{text-align:left}.small{color:#666;font-size:11px}"
    h = [
        f"<html><head><meta charset='utf-8'><title>Set pieces: {H.escape(TEAM)}</title><style>{css}</style></head><body><h1>{H.escape(TEAM)}: corners and attacking free kicks</h1>",
        f"<div class='small'>{nm} matches"
        + (f" ({df.data.min()} to {df.data.max()})" if len(df) else "")
        + ". Intervals: 95% bootstrap over matches. Zones as in the thesis corner study: distance of the delivery from the touchline of the corner taker.</div>",
    ]
    for k, r in res["kinds"].items():
        h.append(
            f"<h2>{k}s: {r['n']} ({r['per_match']:.1f} per match), shot after {pc(r['shot'])} ({ci(r['shot_ci'])}), {r['goals']} goals"
            + (f", mean xG {r['xg']:.3f}" if r["xg"] is not None else "")
            + "</h2>"
        )
        h.append(
            "<table><tr><th>Delivery</th><th>n</th><th>Share (95%)</th><th>Shot after</th>"
            + ("<th>Mean xG</th>" if r["xg"] is not None else "")
            + "</tr>"
        )
        for z, v in r["zones"].items():
            h.append(
                f"<tr><td>{z}</td><td>{v['n']}</td><td>{pc(v['share'])} ({ci(v['ci'])})</td><td>{pc(v['shot'])}</td>"
                + (f"<td>{v['xg']:.3f}</td>" if v["xg"] is not None else "")
                + "</tr>"
            )
        h.append("</table>")
        if r["by_side"]:
            zs = [z for z in r["zones"]]
            h.append(
                "<table><tr><th>Corner side</th><th>n</th>"
                + "".join(f"<th>{z}</th>" for z in zs)
                + "</tr>"
                + "".join(
                    f"<tr><td>{s}</td><td>{q['n']}</td>"
                    + "".join(f"<td>{pc(q['zones'].get(z, 0))}</td>" for z in zs)
                    + "</tr>"
                    for s, q in r["by_side"].items()
                )
                + "</table>"
            )
        if r.get("takers"):
            h.append(
                "<p><b>Takers:</b> "
                + ", ".join(f"{H.escape(p)} ({n})" for p, n in r["takers"].items())
                + ". <b>Most frequent first receivers:</b> "
                + (", ".join(f"{H.escape(p)} ({n})" for p, n in r["receivers"].items()) or "not recorded")
                + ".</p>"
            )
    h.append(
        f"<p class='small'>Clips: setpiece_clips_{fn}.csv (labels such as 'Corner far post'). Limits: event data only, so runs and blocks in the box are not seen; the receiver is recorded only when the delivery is completed. Shot and xG per zone rest on few cases: descriptive, not a recommendation. The thesis test (L3) found no reliable difference in xG between corner set-ups, with low power.</p></body></html>"
    )
    open(f"{BASE}/setpieces_{fn}.html", "w", encoding="utf-8").write("".join(h))
    print("saved", f"{BASE}/setpieces_{fn}.html")
