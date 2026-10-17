"""Transition sheet: where a team loses and wins back the ball in open play, how quickly it counter-presses and what happens in the seconds after. Descriptive, one page.
Usage:  python transitions.py <matches.json> "<Team>" [data_dir=.]
Output in data_dir: transitions_<Team>.html, transitions_<Team>.json and transition_clips_<Team>.csv (same columns as clips_<Team>.csv).
Built only from the order of pass/carry/shot/dribble events of both teams, so it works with the generic CSV of any provider and does not depend on how a
provider defines possessions (StatsBomb, for example, does not open a new possession when the ball is lost and won back before the opponent controls it).
Definitions (fixed before looking at any team):
- loss: an action of the team followed by at least two consecutive actions of the opponent (or an opponent shot), in open play (the opponent action does not start a goal kick, throw-in, corner, free kick,
  kick-off or keeper restart) and not after a shot. Location: the team's last action. Balls out of play, fouls and keeper catches are not losses here.
- recovery: an action of the opponent followed by at least two consecutive actions of the team (or a shot), in open play. Location: the team's first action.
- counter-press regain: the team acts again within 5 s of the opponent's first action, in open play. Across 5 test teams this share varied little (17-19%),
  so it describes the team but separates styles poorly; read it with the losses by third and the recoveries in the final third. Shot conceded after a loss: the opponent shoots within 10 s, before the team regains.
- after a recovery: shot within 10 s and before the opponent touches the ball again; reached the final third (x >= 80) in the same spell of possession.
- thirds on the team's own attacking direction: own (x < 40), middle (40-80), final (x >= 80). Intervals: 95% bootstrap over matches."""
import sys, os, io, json, base64, html as H
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
MF, TEAM = sys.argv[1], sys.argv[2]; BASE = sys.argv[3] if len(sys.argv) > 3 else "."
CTRL = ("Pass", "Carry", "Shot", "Dribble"); OPEN = ("Regular Play", "From Counter"); THIRDS = ["own third", "middle third", "final third"]
third = lambda x: THIRDS[0] if x < 40 else (THIRDS[1] if x < 80 else THIRDS[2])

def end_of(e):
    t = e["type"]["name"]
    return (e.get("pass") or {}).get("end_location") if t == "Pass" else ((e.get("carry") or {}).get("end_location") if t == "Carry" else e.get("location"))

def extract():
    ms = sorted([g for g in json.load(open(MF, encoding="utf-8")) if TEAM in (g["home_team"]["home_team_name"], g["away_team"]["away_team_name"])], key=lambda g: g["match_date"])
    L, R = [], []
    for gi, g in enumerate(ms):
        opp = g["away_team"]["away_team_name"] if g["home_team"]["home_team_name"] == TEAM else g["home_team"]["home_team_name"]; seen = set(); A = []
        for e in json.load(open(f"{BASE}/ev/{g['match_id']}.json", encoding="utf-8")):
            first = e["possession"] not in seen; seen.add(e["possession"])
            if e["type"]["name"] in CTRL and e.get("location"):
                A.append(dict(e=e, team=e["team"]["name"] == TEAM, per=e["period"], t=e["minute"] * 60 + e["second"], x=e["location"][0], y=e["location"][1],
                              restart=first and e["play_pattern"]["name"] not in OPEN, shot=e["type"]["name"] == "Shot", end=(end_of(e) or e["location"])[0]))
        base = dict(match=g["match_id"], gi=gi, data=g["match_date"], avv=opp)
        for i in range(1, len(A)):
            a, b = A[i - 1], A[i]
            if a["team"] == b["team"] or a["per"] != b["per"] or b["restart"] or a["shot"]: continue
            # actions after b until the ball changes team again (or a restart, or the half ends)
            rest = []
            for c in A[i + 1:]:
                if c["per"] != b["per"] or c["restart"]: break
                rest.append(c)
            spell = [b] + [c for c in rest[:next((k for k, c in enumerate(rest) if c["team"] != b["team"]), len(rest))]]
            if len(spell) < 2 and not b["shot"]: continue   # a single touch (a loose ball, a deflected pass) is not a change of control
            e0 = a["e"] if a["team"] else b["e"]
            row = dict(base, tempo=e0["period"], minuto=e0["minute"], sec=e0["second"])
            if a["team"]:   # loss: a = our last action
                nxt = next((c for c in rest if c["team"]), None)
                L.append(dict(row, x=a["x"], y=a["y"], third=third(a["x"]), regain5=int(nxt is not None and nxt["t"] - b["t"] <= 5),
                              conceded10=int(any(c["shot"] and c["t"] - b["t"] <= 10 for c in spell)), n_pass=0, dur=0))
            else:           # recovery: b = our first action
                R.append(dict(row, x=b["x"], y=b["y"], third=third(b["x"]), shot10=int(any(c["shot"] and c["t"] - b["t"] <= 10 for c in spell)), shot=int(any(c["shot"] for c in spell)),
                              final_third=int(max(c["end"] for c in spell) >= 80), n_pass=sum(c["e"]["type"]["name"] == "Pass" for c in spell), dur=spell[-1]["t"] - b["t"]))
    return pd.DataFrame(L), pd.DataFrame(R), len(ms)

def boot(v, gi, games, B=1000, seed=0):
    rng = np.random.default_rng(seed); by = {g: v[gi == g] for g in games}; out = []
    for _ in range(B):
        s = np.concatenate([by[g] for g in rng.choice(games, len(games))]); out.append(s.mean() if len(s) else np.nan)
    return [float(np.nanpercentile(out, 2.5)), float(np.nanpercentile(out, 97.5))]

def heat(d, title, cmap):
    fig, ax = plt.subplots(figsize=(5.4, 3.6)); hb, _, _ = np.histogram2d(d.x.clip(0, 119.9), d.y.clip(0, 79.9), bins=[6, 3], range=[[0, 120], [0, 80]]); hb = hb / max(hb.sum(), 1)
    ax.imshow(hb.T, extent=[0, 120, 80, 0], cmap=cmap, vmin=0, vmax=max(hb.max(), 0.01), aspect="equal")
    for i in range(6):
        for j in range(3): ax.text(10 + 20 * i, 13.3 + 26.7 * j, f"{100 * hb[i, j]:.0f}%", ha="center", va="center", fontsize=8, color="white" if hb[i, j] > 0.55 * hb.max() else "black")
    for xy in ([[0, 0], [120, 0], [120, 80], [0, 80], [0, 0]], [[60, 0], [60, 80]], [[0, 18], [18, 18], [18, 62], [0, 62]], [[120, 18], [102, 18], [102, 62], [120, 62]]):
        a = np.array(xy); ax.plot(a[:, 0], a[:, 1], color="#555", lw=0.8)
    ax.set_xticks([]); ax.set_yticks([]); ax.set_title(title + " (attacking left to right; top = left side)", fontsize=8.5)
    b = io.BytesIO(); fig.savefig(b, format="png", dpi=110, bbox_inches="tight"); plt.close(fig); return base64.b64encode(b.getvalue()).decode()

if __name__ == "__main__":
    L, R, nm = extract(); fn = TEAM.replace(" ", "_"); games = np.arange(nm); res = {"team": TEAM, "matches": int(nm)}
    res["losses"] = dict(n=int(len(L)), per_match=float(len(L) / nm), regain5=float(L.regain5.mean()), regain5_ci=boot(L.regain5.values, L.gi.values, games),
                         conceded10=float(L.conceded10.mean()), conceded10_ci=boot(L.conceded10.values, L.gi.values, games),
                         by_third={t: dict(n=int((L.third == t).sum()), per_match=float((L.third == t).sum() / nm), regain5=float(L.regain5[L.third == t].mean()), conceded10=float(L.conceded10[L.third == t].mean())) for t in THIRDS if (L.third == t).any()})
    res["recoveries"] = dict(n=int(len(R)), per_match=float(len(R) / nm), shot10=float(R.shot10.mean()), shot10_ci=boot(R.shot10.values, R.gi.values, games),
                             by_third={t: dict(n=int((R.third == t).sum()), per_match=float((R.third == t).sum() / nm), per_match_ci=[float(v) * len(R) / nm for v in boot((R.third == t).values.astype(float), R.gi.values, games)],
                                                shot10=float(R.shot10[R.third == t].mean()), shot=float(R.shot[R.third == t].mean()), final_third=float(R.final_third[R.third == t].mean())) for t in THIRDS if (R.third == t).any()})
    last = games[-5:]; L5, R5 = L[L.gi.isin(last)], R[R.gi.isin(last)]
    res["last5"] = dict(losses_per_match=float(len(L5) / len(last)), regain5=float(L5.regain5.mean()) if len(L5) else None, recoveries_final_third_per_match=float((R5.third == THIRDS[2]).sum() / len(last)))
    json.dump(res, open(f"{BASE}/transitions_{fn}.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    cols = ["family", "match", "data", "avv", "tempo", "minuto", "sec", "start_type", "n_pass", "dur", "shot"]
    clips = pd.concat([L.assign(family=["Loss " + t + (" - regained in 5 s" if r else "") for t, r in zip(L.third, L.regain5)], start_type="loss", shot=L.conceded10),
                       R.assign(family=["Recovery " + t + (" - shot within 10 s" if s else "") for t, s in zip(R.third, R.shot10)], start_type="recovery", shot=R.shot10)])
    clips.sort_values(["family", "data", "tempo", "minuto", "sec"])[cols].rename(columns={"data": "date", "avv": "opponent", "tempo": "half", "minuto": "minute", "sec": "second", "n_pass": "passes", "dur": "duration_s", "shot": "ended_in_shot"}).to_csv(f"{BASE}/transition_clips_{fn}.csv", index=False)
    pc = lambda x: "" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{100 * x:.0f}%"; ci = lambda c: f"{100 * c[0]:.0f}-{100 * c[1]:.0f}%"
    css = "body{font-family:Arial,sans-serif;max-width:980px;margin:24px auto;color:#222;font-size:13px}h1,h2{color:#1F3A5F}h2{border-bottom:1px solid #ccc;padding-top:10px}table{border-collapse:collapse;width:100%;margin:6px 0}th,td{border:1px solid #ccc;padding:4px 6px;text-align:right}th{background:#E6ECF4}td:first-child,th:first-child{text-align:left}.small{color:#666;font-size:11px}.two{display:flex;gap:8px}.two img{width:50%}"
    Lr, Rr, l5 = res["losses"], res["recoveries"], res["last5"]
    h = [f"<html><head><meta charset='utf-8'><title>Transitions: {H.escape(TEAM)}</title><style>{css}</style></head><body><h1>{H.escape(TEAM)}: losing and winning back the ball</h1>",
         f"<div class='small'>{nm} matches ({R.data.min()} to {R.data.max()}), open play only. Intervals: 95% bootstrap over matches. Locations are on the team's own attacking direction.</div>",
         f"<div class='two'><img src='data:image/png;base64,{heat(L, 'Where they lose the ball', 'Reds')}'><img src='data:image/png;base64,{heat(R, 'Where they win it back', 'Greens')}'></div>",
         f"<h2>After losing the ball: {Lr['per_match']:.1f} losses per match</h2><p>Counter-press: ball regained within 5 s after <b>{pc(Lr['regain5'])}</b> of losses ({ci(Lr['regain5_ci'])}). Opponent shot within 10 s after {pc(Lr['conceded10'])} ({ci(Lr['conceded10_ci'])}).</p>",
         "<table><tr><th>Where the ball is lost</th><th>Per match</th><th>Regained within 5 s</th><th>Opponent shot within 10 s</th></tr>" + "".join(f"<tr><td>{t}</td><td>{v['per_match']:.1f}</td><td>{pc(v['regain5'])}</td><td>{pc(v['conceded10'])}</td></tr>" for t, v in Lr["by_third"].items()) + "</table>",
         f"<h2>After winning the ball: {Rr['per_match']:.1f} recoveries per match</h2><p>Shot within 10 s after {pc(Rr['shot10'])} of recoveries ({ci(Rr['shot10_ci'])}).</p>",
         "<table><tr><th>Where the ball is won</th><th>Per match (95%)</th><th>Shot within 10 s</th><th>Shot in the possession</th><th>Reached final third</th></tr>" + "".join(f"<tr><td>{t}</td><td>{v['per_match']:.1f} ({v['per_match_ci'][0]:.1f}-{v['per_match_ci'][1]:.1f})</td><td>{pc(v['shot10'])}</td><td>{pc(v['shot'])}</td><td>{pc(v['final_third'])}</td></tr>" for t, v in Rr["by_third"].items()) + "</table>",
         f"<h2>Last 5 matches</h2><p>Losses per match {l5['losses_per_match']:.1f} (season {Lr['per_match']:.1f}); regained within 5 s {pc(l5['regain5'])} (season {pc(Lr['regain5'])}); recoveries in the final third per match {l5['recoveries_final_third_per_match']:.1f} (season {Rr['by_third'].get(THIRDS[2], {}).get('per_match', 0):.1f}). Five matches are few: use it as a hint for video.</p>",
         f"<p class='small'>Clips: transition_clips_{fn}.csv ('Loss final third - regained in 5 s', 'Recovery middle third - shot within 10 s', ...). Limits: built from the order of passes, carries, shots and dribbles, so a loss is located at the team's last action before an opponent action (not at the exact duel) and a recovery at the team's first action after it; single touches (loose balls, deflections) are ignored; pressing without a ball win is not seen. The counter-press share varied little across teams in our tests (17-19%). Balls out of play, fouls and keeper catches are excluded.</p></body></html>"]
    open(f"{BASE}/transitions_{fn}.html", "w", encoding="utf-8").write("".join(h)); print("saved", f"{BASE}/transitions_{fn}.html")
