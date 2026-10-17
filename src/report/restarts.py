"""Restart sheet: how a team plays out from goal kicks, keeper distributions and throw-ins. Descriptive, one page, for pressing plans.
Usage:  python restarts.py <matches.json> "<Team>" [data_dir=.]
Output in data_dir: restarts_<Team>.html, restarts_<Team>.json and restart_clips_<Team>.csv (every restart possession with its label, same columns as clips_<Team>.csv).
Definitions (fixed before looking at any team):
- restart possession: possession of the team whose play pattern is From Goal Kick, From Keeper or From Throw In; throw-ins split by own half (x < 60) and opponent half.
- first pass: first pass of the team in the possession. Short = under 30 m (as in the long-pass share of the report). Side = end of the first pass, y in thirds (left, centre, right; StatsBomb y small = left).
- outcomes of the possession: reached the opponent half (any team action ending at x >= 60), reached the final third (x >= 80), shot, ended in own half (no shot and the last team action ends at x < 60: ball lost, out of play or foul).
Intervals are 95% bootstrap over matches. 'Last 5' uses only the five most recent matches and is shown with its own interval: with 5 matches it is wide."""
import sys, os, json, html as H
import numpy as np, pandas as pd
MF, TEAM = sys.argv[1], sys.argv[2]; BASE = sys.argv[3] if len(sys.argv) > 3 else "."
PP = {"From Goal Kick": "Goal kick", "From Keeper": "Keeper", "From Throw In": "Throw-in"}

def end_of(e):
    t = e["type"]["name"]
    if t == "Pass": return e["pass"]["end_location"]
    if t == "Carry": return e["carry"]["end_location"]
    return e.get("location")

def extract():
    ms = sorted([g for g in json.load(open(MF, encoding="utf-8")) if TEAM in (g["home_team"]["home_team_name"], g["away_team"]["away_team_name"])], key=lambda g: g["match_date"])
    rows = []
    for gi, g in enumerate(ms):
        opp = g["away_team"]["away_team_name"] if g["home_team"]["home_team_name"] == TEAM else g["home_team"]["home_team_name"]; poss = {}
        for e in json.load(open(f"{BASE}/ev/{g['match_id']}.json", encoding="utf-8")):
            if e.get("possession_team", {}).get("name") == TEAM and e["team"]["name"] == TEAM and e["play_pattern"]["name"] in PP and e["type"]["name"] in ("Pass", "Carry", "Shot", "Dribble"):
                poss.setdefault(e["possession"], []).append(e)
        for pid, es in poss.items():
            passes = [e for e in es if e["type"]["name"] == "Pass"]
            if not passes or es[0].get("location") is None: continue
            p0 = passes[0]; kind = PP[es[0]["play_pattern"]["name"]]
            if kind == "Throw-in": kind += " own half" if es[0]["location"][0] < 60 else " opp. half"
            ends = [end_of(e) for e in es if end_of(e) is not None]; xs = [p[0] for p in ends]
            shot = any(e["type"]["name"] == "Shot" for e in es); y = p0["pass"]["end_location"][1]
            t0 = es[0]["minute"] * 60 + es[0]["second"]; t1 = es[-1]["minute"] * 60 + es[-1]["second"]
            rows.append(dict(match=g["match_id"], gi=gi, data=g["match_date"], avv=opp, tempo=es[0]["period"], minuto=es[0]["minute"], sec=es[0]["second"], kind=kind,
                             short=int(p0["pass"].get("length", 0) < 30), side="left" if y < 80 / 3 else ("right" if y > 160 / 3 else "centre"), n_pass=len(passes), dur=max(t1 - t0, 0),
                             opp_half=int(max(xs) >= 60), final_third=int(max(xs) >= 80), shot=int(shot), lost_own_half=int(not shot and xs[-1] < 60)))
    return pd.DataFrame(rows), len(ms)

def boot(d, col, games, B=1000, seed=0):
    rng = np.random.default_rng(seed); by = {g: d[col].values[d.gi.values == g] for g in games}; out = []
    for _ in range(B):
        v = np.concatenate([by[g] for g in rng.choice(games, len(games))]); out.append(v.mean() if len(v) else np.nan)
    return [float(np.nanpercentile(out, 2.5)), float(np.nanpercentile(out, 97.5))]

if __name__ == "__main__":
    df, nm = extract(); fn = TEAM.replace(" ", "_"); games = np.arange(nm); last = games[-5:]
    for s in ("left", "centre", "right"): df[s] = (df.side == s).astype(int)
    METRICS = [("short", "First pass short (< 30 m)"), ("left", "First pass to the left"), ("centre", "First pass central"), ("right", "First pass to the right"),
               ("opp_half", "Reached the opponent half"), ("final_third", "Reached the final third"), ("lost_own_half", "Possession ended in own half (lost, out or foul)"), ("shot", "Ended in a shot")]
    KINDS = ["Goal kick", "Keeper", "Throw-in own half", "Throw-in opp. half"]; res = {"team": TEAM, "matches": int(nm), "kinds": {}}
    for k in KINDS:
        d = df[df.kind == k]; dl = d[d.gi.isin(last)]
        if not len(d): continue
        res["kinds"][k] = dict(n=int(len(d)), per_match=float(len(d) / nm), n_last5=int(len(dl)), passes=float(d.n_pass.mean()),
                               metrics={m: dict(season=float(d[m].mean()), ci=boot(d, m, games), last5=float(dl[m].mean()) if len(dl) else None, last5_ci=boot(dl, m, last) if len(dl) else None) for m, _ in METRICS})
        # short vs long goal kicks behave differently: outcome by first-pass length
        res["kinds"][k]["by_length"] = {lab: dict(n=int(len(q)), opp_half=float(q.opp_half.mean()), lost_own_half=float(q.lost_own_half.mean()), shot=float(q.shot.mean())) for lab, q in (("short", d[d.short == 1]), ("long", d[d.short == 0])) if len(q)}
    json.dump(res, open(f"{BASE}/restarts_{fn}.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    lab = lambda r: f"{r.kind} {'short' if r.short else 'long'} {r.side}"
    df.assign(family=[lab(r) for r in df.itertuples()]).sort_values(["family", "data", "tempo", "minuto", "sec"])[["family", "match", "data", "avv", "tempo", "minuto", "sec", "kind", "n_pass", "dur", "shot"]].rename(columns={"data": "date", "avv": "opponent", "tempo": "half", "minuto": "minute", "sec": "second", "kind": "start_type", "n_pass": "passes", "dur": "duration_s", "shot": "ended_in_shot"}).to_csv(f"{BASE}/restart_clips_{fn}.csv", index=False)
    pc = lambda x: "" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{100 * x:.0f}%"; ci = lambda c: "" if not c else f"{100 * c[0]:.0f}-{100 * c[1]:.0f}%"
    css = "body{font-family:Arial,sans-serif;max-width:980px;margin:24px auto;color:#222;font-size:13px}h1,h2{color:#1F3A5F}h2{border-bottom:1px solid #ccc;padding-top:10px}table{border-collapse:collapse;width:100%;margin:6px 0}th,td{border:1px solid #ccc;padding:4px 6px;text-align:right}th{background:#E6ECF4}td:first-child,th:first-child{text-align:left}.small{color:#666;font-size:11px}.diff{background:#FFF4D6}"
    h = [f"<html><head><meta charset='utf-8'><title>Restarts: {H.escape(TEAM)}</title><style>{css}</style></head><body><h1>How {H.escape(TEAM)} play out from restarts</h1>",
         f"<div class='small'>{nm} matches ({df.data.min()} to {df.data.max()}). Every possession starting from a goal kick, a keeper distribution or a throw-in. Intervals: 95% bootstrap over matches. 'Last 5' = the five most recent matches; highlighted when its value lies outside the season interval (a hint to check on video, not proof of a change).</div>"]
    for k, r in res["kinds"].items():
        h.append(f"<h2>{k}: {r['n']} possessions ({r['per_match']:.1f} per match), {r['passes']:.1f} passes on average</h2><table><tr><th></th><th>Season</th><th>95% interval</th><th>Last 5 ({r['n_last5']})</th><th>Last 5 interval</th></tr>")
        for m, name in METRICS:
            v = r["metrics"][m]; out = v["last5"] is not None and not (v["ci"][0] <= v["last5"] <= v["ci"][1])
            h.append(f"<tr{' class=diff' if out else ''}><td>{name}</td><td>{pc(v['season'])}</td><td>{ci(v['ci'])}</td><td>{pc(v['last5'])}</td><td>{ci(v['last5_ci'])}</td></tr>")
        h.append("</table>")
        if len(r["by_length"]) == 2:
            h.append("<table><tr><th>First pass</th><th>n</th><th>Reached opponent half</th><th>Ended in own half</th><th>Shot</th></tr>" + "".join(f"<tr><td>{lb}</td><td>{q['n']}</td><td>{pc(q['opp_half'])}</td><td>{pc(q['lost_own_half'])}</td><td>{pc(q['shot'])}</td></tr>" for lb, q in r["by_length"].items()) + "</table>")
    h.append(f"<p class='small'>Clips: restart_clips_{fn}.csv lists every possession above, labelled e.g. 'Goal kick short left'; convert it with src/report/clips_to_xml.py to import into a video tool. Limits: event data only, so the opponent's press and off-ball positions are not seen; 'ended in own half' uses the last recorded action of the possession.</p></body></html>")
    open(f"{BASE}/restarts_{fn}.html", "w", encoding="utf-8").write("".join(h)); print("saved", f"{BASE}/restarts_{fn}.html")
