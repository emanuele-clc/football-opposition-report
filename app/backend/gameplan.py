"""Game plan: the opponent's formations and style in a few lines, plus rule-based hints on how to approach them, optionally against your own team.
HINTS, NOT ADVICE. Each hint fires from a fixed rule on where the opponent (and your team) ranks among the teams in the data folder, and shows the numbers
that made it fire. No rule was tested for whether following it changes results: they say where to look on video, not what will work.
Rules (fixed before looking at their output): 'top' = among the k highest of n teams, 'bottom' = among the k lowest, k = max(1, n // 5); no rank-based hint
with fewer than 4 teams. Matchup facts come from matchups_<Team>.json (only 'clear' differences not linked to how the groups are formed).
Coach brief: the fired hints rewritten as a short plan by phase (with the ball, without the ball, transitions, set pieces) and three priorities. Written by
fixed templates from the same numbers, offline: no language model and no external service."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src", "report"))
from keyplayers import events_view  # noqa: E402  (key players and timeline, shared with the pipeline)

FORM = lambda f: "-".join(f) if f and f.isdigit() else (f or "unknown")

# (id, side, condition, evidence, title, why, look). side 'opp' = only the opponent's ranks, 'both' = opponent and your team.
RULES = [
    ("gk_short_hi", "opp", lambda O, M: O("gk_short", "top"), ["gk_short", "gk_opp_half"], "They play goal kicks short",
     "Their first pass from goal kicks is short more often than almost every team here.",
     "Pressing their goal kicks may force errors or long balls. Check where the first pass goes and how often they still reach your half.", "restarts"),
    ("gk_short_lo", "opp", lambda O, M: O("gk_short", "bottom"), ["gk_short", "gk_opp_half"], "They go long from goal kicks",
     "Their goal kicks go long more often than almost every team here.",
     "Expect long balls: who wins the first header and the second ball matters more than pressing their keeper.", "restarts"),
    ("press_hard", "opp", lambda O, M: O("ppda", "bottom"), ["ppda", "press_pm"], "They press intensely",
     "They allow fewer opponent passes per defensive action (PPDA) than almost every team here.",
     "Plan an exit route: a target for longer passes or a quick switch. Short build-up under their pressure risks losing the ball in your half.", "defending"),
    ("press_high", "opp", lambda O, M: O("press_final", "top"), ["press_final"], "They press high up the pitch",
     "A larger share of their pressures is in the final third than for almost every team here.",
     "Your first passes from the back will be contested: check on video which routes out of their press worked against them.", "defending"),
    ("press_soft", "opp", lambda O, M: O("ppda", "top") and not O("press_final", "top"), ["ppda", "press_final"], "They let you have the ball",
     "They allow many passes before acting and rarely press in the final third.",
     "Expect a mid or low block: you will have the ball in your half; the problem is the space between and behind their lines.", "defending"),
    ("def_high", "opp", lambda O, M: O("def_height", "top"), ["def_height"], "They defend high",
     "Their defensive actions happen higher up the pitch than almost every team here.",
     "There may be space behind their defence: check on video how they cope with runs in behind (event data do not show their line).", "defending"),
    ("def_deep", "opp", lambda O, M: O("def_height", "bottom"), ["def_height"], "They defend deep",
     "Their defensive actions happen deeper than almost every team here.",
     "Little space in behind: look at how chances against them came (crosses, cut-backs, second balls).", "defending"),
    ("lose_ball", "opp", lambda O, M: O("losses_pm", "top"), ["losses_pm"], "They lose the ball often",
     "They lose possession in open play more often than almost every team here.",
     "Pressing and counter-pressing may win balls: check where they lose it on the transitions map.", "transitions"),
    ("win_high", "opp", lambda O, M: O("high_rec_pm", "top"), ["high_rec_pm"], "They win the ball high",
     "They recover the ball in the final third more often than almost every team here.",
     "Risky passes in your own third are punished more: check which build-up routes they intercept.", "transitions"),
    ("direct", "opp", lambda O, M: O("long", "top"), ["long", "passes"], "They play direct",
     "Their share of long passes is among the highest here.", "Second balls and aerial duels around your box will matter.", "build-up"),
    ("patient", "opp", lambda O, M: O("passes", "top"), ["passes", "dur"], "They keep the ball for long spells",
     "Their sequences have more passes than almost every team here.", "Expect long spells without the ball: decide where to press and where to wait.", "build-up"),
    ("corners", "opp", lambda O, M: O("corner_shot", "top"), ["corner_shot", "corner_pm"], "Dangerous from corners",
     "Their corners end in a shot more often than almost every team here.", "Conceding corners cheaply costs more against them: check delivery zones and takers.", "setpieces"),
    ("leaky", "opp", lambda O, M: O("xga_pm", "top"), ["xga_pm"], "They concede many chances",
     "Their xG conceded per match is among the highest here.", "Look at which situations the chances against them came from.", "defending"),
    ("solid", "opp", lambda O, M: O("xga_pm", "bottom"), ["xga_pm"], "Hard to create chances against them",
     "Their xG conceded per match is among the lowest here.", "Chances will be few: set pieces and transitions may count more than usual.", "defending"),
    ("my_short_vs_press", "both", lambda O, M: M("gk_short", "top") and (O("ppda", "bottom") or O("press_final", "top")), ["gk_short", "ppda", "press_final"],
     "Your short build-up meets their press", "You play goal kicks short more than most teams; they press high or hard.",
     "The key duel of the match: look at your own past matches against a high press on this page and decide whether to keep building short.", "matchups"),
    ("my_press_vs_short", "both", lambda O, M: M("press_final", "top") and O("gk_short", "top"), ["press_final", "gk_short"],
     "Your high press meets their short build-up", "You press often in the final third; they play goal kicks short.",
     "Check on video how they escaped high pressure in past matches (Restarts → where the first pass goes).", "restarts"),
    ("my_long_vs_high", "both", lambda O, M: M("long", "top") and O("def_height", "top"), ["long", "def_height"],
     "Your long balls against their high defence", "You play long more than most teams; they defend high.", "Balls in behind may find space: check their recovery runs on video.", "defending"),
]


def build(opp_key, my_key, teams, ranks, load):
    ts = teams(); n = len(ts); k = max(1, n // 5)
    def rk(key):
        R = {r["id"]: r for r in ranks(key)} if key else {}
        def at(mid, where):
            r = R.get(mid)
            if not r or n < 4: return False
            return r["rank"] <= k if where == "top" else r["rank"] > r["of"] - k
        return R, at
    OR, O = rk(opp_key); MR, M = rk(my_key) if my_key else ({}, lambda *_: False)

    def formations(key):
        mu = load("matchups", key)
        if not mu: return None
        fs = [r["formation"] for r in mu["per_match"]]; cnt = {}
        for f in fs: cnt[f] = cnt.get(f, 0) + 1
        return {"most_used": [{"formation": FORM(f), "raw": f, "matches": c} for f, c in sorted(cnt.items(), key=lambda x: -x[1])][:4],
                "last5": [{"formation": FORM(r["formation"]), "raw": r["formation"], "opponent": r["opponent"], "date": r["date"]} for r in mu["per_match"][-5:]],
                "matches": len(fs)}

    ev = lambda R, ids: [{"id": i, "label": R[i]["label"], "value": R[i]["value"], "unit": R[i]["unit"], "rank": R[i]["rank"], "of": R[i]["of"]} for i in ids if i in R]
    hints = []
    for hid, side, cond, ids, title, why, look, tab in [(r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7]) for r in RULES]:
        if side == "both" and not my_key: continue
        if cond(O, M):
            hints.append({"id": hid, "side": side, "title": title, "why": why, "look": look, "tab": tab,
                          "evidence": ev(OR, ids) if side == "opp" else [{**e, "team": "opponent"} for e in ev(OR, ids)] + [{**e, "team": "you"} for e in ev(MR, ids)]})

    pz = pressure_zones(opp_key, list(ts), load); ph = pressure_hint(pz)
    if ph: hints.insert(0, ph)

    def past(key):
        mu = load("matchups", key)
        if not mu: return []
        out = []
        for s in mu["splits"].values():
            ga, gb = s["groups"]
            for m in s["metrics"]:
                if m["verdict"] == "clear" and not m.get("linked"):
                    out.append({"split": s["label"], "label": m["label"], "unit": m["unit"], "a": m["a"], "b": m["b"], "ga": ga, "gb": gb, "n_a": s["n_a"], "n_b": s["n_b"]})
        return out

    my_press = None
    if my_key and (mu := load("matchups", my_key)):
        s = mu["splits"]["opp_press"]
        my_press = {"groups": s["groups"], "n_a": s["n_a"], "n_b": s["n_b"],
                    "metrics": [m for m in s["metrics"] if m["id"] in ("lost_own_half", "own_half_completion", "xg_against", "xg_for", "points")]}

    extreme = sorted(OR.values(), key=lambda r: -abs((r["rank"] - 1) / max(r["of"] - 1, 1) - 0.5))[:6] if n >= 4 else []
    return {"opponent": ts[opp_key]["team"], "mine": ts[my_key]["team"] if my_key else None, "teams_in_folder": n, "k": k,
            "formations": {"opponent": formations(opp_key), "mine": formations(my_key) if my_key else None},
            "profile": [{"id": r["id"], "label": r["label"], "value": r["value"], "unit": r["unit"], "rank": r["rank"], "of": r["of"]} for r in extreme],
            "hints": hints, "opp_past": past(opp_key), "my_vs_press": my_press,
            "pressure_zones": pz,
            "watch_first": watch_first(load("matchups", opp_key), load("defending", my_key) if my_key else None, load("matchups", my_key) if my_key else None) if load("matchups", opp_key) else None,
            "brief": brief(hints, past(opp_key), ts[opp_key]["team"], ts[my_key]["team"] if my_key else None)}


PHASE = {"with_ball": ("press_hard", "press_high", "def_high", "def_deep", "solid", "leaky", "my_short_vs_press", "my_long_vs_high"),
         "without_ball": ("press_zone", "gk_short_hi", "gk_short_lo", "direct", "patient", "my_press_vs_short"),
         "transitions": ("lose_ball", "win_high"), "set_pieces": ("corners",)}
PHASE_TITLE = {"with_ball": "With the ball", "without_ball": "Without the ball", "transitions": "Transitions", "set_pieces": "Set pieces"}


def brief(hints, past, opp, mine):
    """Same hints, as a plan by phase. Priority: 'you vs them' hints first, then hints where the opponent is the most extreme team of the folder."""
    def prio(h):
        ext = any(e["rank"] in (1, e["of"]) for e in h["evidence"] if e.get("team", "opponent") == "opponent")
        return (h["side"] == "both") * 2 + ext
    phases = {}
    for ph, ids in PHASE.items():
        hs = sorted([h for h in hints if h["id"] in ids], key=prio, reverse=True)
        lines = [f"{h['title']}. {h['look']}" for h in hs]
        if ph == "without_ball":
            f = lambda v, u: f"{100 * v:.0f}%" if u == "pct" else f"{v:.2f}" if u == "num2" else f"{v:.1f}"
            lines += [f"Their past matches: {p['label']} {f(p['a'], p['unit'])} per match {p['ga']} and {f(p['b'], p['unit'])} {p['gb']} ({p['n_a']} and {p['n_b']} matches)."
                      for p in past if p["split"] == "Opponent pressing"]
        phases[ph] = {"title": PHASE_TITLE[ph], "lines": lines or [f"Nothing stands out in {opp}'s numbers for this phase: prepare as usual and check on video."]}
    top = sorted(hints, key=prio, reverse=True)[:3]
    return {"priorities": [f"{h['title']}. {h['look']}" for h in top],
            "phases": phases,
            "intro": f"Plan against {opp}" + (f" for {mine}" if mine else "") + f", from {len(hints)} hints. Written by fixed rules from the numbers on this page, offline; hints to check on video, not tested advice."}


def watch_first(opp_mu, my_def, my_mu, n=5):
    """Their matches against opponents that defended most like your team: |log opponent PPDA - log your PPDA| + 0.5 if the back line differs.
    Without your team: their five most recent matches."""
    import math
    rows = opp_mu["per_match"]
    if not my_def or not my_mu:
        return {"rule": "their five most recent matches", "matches": [dict(r, distance=None) for r in rows[-n:][::-1]]}
    fs = {}
    for r in my_mu["per_match"]: fs[r["formation"]] = fs.get(r["formation"], 0) + 1
    f = max(fs, key=fs.get)
    line = "back four" if f[:1] == "4" else "back three/five" if f[:1] in ("3", "5") else "unknown"
    ppda = my_def["ppda"]["value"]

    def dist(r): return round(abs(math.log(max(r["opp_ppda"], 0.1) / ppda)) + 0.5 * (r["opp_back_line"] != line), 2)
    sc = sorted(rows, key=dist)
    return {"rule": f"opponents whose PPDA in that match was closest to yours ({ppda:.1f}) and with your back line ({line}, from {FORM(f)})",
            "matches": [dict(r, distance=dist(r)) for r in sc[:n]]}


# Where pressing hurts them: each own-half zone against the other teams in the folder (pooled), from keyplayers_<Team>.json.
# 'weaker' = completion under pressure at least 5 points below the other teams in that zone, with 40+ passes under pressure (fixed rule).
def pressure_zones(key, keys, load):
    me = load("keyplayers", key)
    if not me or "under_pressure" not in me: return None
    others = [load("keyplayers", k) for k in keys if k != key]; others = [o for o in others if o and "under_pressure" in o]
    zones = []
    for i, z in enumerate(me["under_pressure"]):
        up = sum(o["under_pressure"][i]["under_pressure"] for o in others); ok = sum(o["under_pressure"][i]["up_ok"] for o in others)
        lg = sum(o["under_pressure"][i]["up_long"] for o in others)
        ref = ok / up if up else None; ref_long = lg / up if up else None
        diff = None if ref is None else z["up_completion"] - ref
        zones.append({**z, "ref_completion": ref, "ref_long_share": ref_long, "diff": diff, "weaker": bool(diff is not None and diff <= -0.05 and not z["few"])})
    return {"zones": zones, "total": me["under_pressure_total"], "teams_in_reference": len(others), "matches": me["matches"]}


def zone_name(z):
    depth = {0: "around their own box", 20: "in their own third", 40: "just inside their half"}[z["x0"]]
    side = "left" if z["y0"] == 0 else "centre" if z["y0"] < 30 else "right"
    return f"{side}, {depth}"


def pressure_hint(pz):
    weak = sorted([z for z in pz["zones"] if z["weaker"]], key=lambda z: z["diff"]) if pz else []
    if not weak: return None
    z = weak[0]
    return {"id": "press_zone", "side": "opp", "title": "Where pressing hurts them",
            "why": f"Under pressure {zone_name(z)} they complete {z['up_completion']:.0%} of passes, against {z['ref_completion']:.0%} for the other teams there ({z['under_pressure']} passes)."
                   + (f" {len(weak) - 1} more zone(s) below the others." if len(weak) > 1 else ""),
            "look": "A pressing trigger worth checking on video: what happens when the ball reaches that zone, and who has it.", "tab": "gameplan",
            "evidence": []}


# Without a player: matches the player started vs matches he did not start (StatsBomb starting eleven). Same verdict rule as the matchup sheet.
WITHOUT_METRICS = [("xg_for", "xG created", "num2"), ("xg_against", "xG conceded", "num2"), ("shots_for", "Shots", "num"), ("shots_against", "Shots conceded", "num"),
                   ("points", "Points per match", "num2"), ("own_half_completion", "Own-half pass completion", "pct"), ("lost_own_half", "Balls lost in own half", "num")]


def without(key, player, load, clip_rows):
    import numpy as np
    kp, mu = load("keyplayers", key), load("matchups", key)
    if not kp or not mu or "starters" not in kp: return None
    starts = {}
    for names in kp["starters"].values():
        for n in names: starts[n] = starts.get(n, 0) + 1
    n_all = len(mu["per_match"])
    players = [{"player": p, "starts": s, "not_started": n_all - s, "usable": min(s, n_all - s) >= 6} for p, s in sorted(starts.items(), key=lambda x: -x[1])]
    if not player: return {"players": players}
    rows = {str(r["match"]): r for r in mu["per_match"]}
    A = [m for m in rows if player in kp["starters"].get(m, [])]; Bm = [m for m in rows if m not in A]
    seq = {}
    for r in clip_rows: seq.setdefault(str(r["match"]), []).append(r)
    fams = sorted({r["family"] for r in clip_rows if r["family"].startswith("B")})
    stats = [(m, l, u, (lambda ms, m=m: float(np.mean([rows[x][m] for x in ms])) if ms else np.nan)) for m, l, u in WITHOUT_METRICS]
    def ratio(ms, f):
        tot = sum(1 for x in ms for r in seq.get(x, []) if r["family"].startswith("B")); return sum(1 for x in ms for r in seq.get(x, []) if r["family"] == f) / tot if tot else np.nan
    def passes(ms):
        rs = [int(r["passes"]) for x in ms for r in seq.get(x, [])]; return float(np.mean(rs)) if rs else np.nan
    stats.append(("passes", "Passes per sequence", "num", passes))
    stats += [(f"fam_{f}", f"Share of build-up family {f}", "pct", (lambda ms, f=f: ratio(ms, f))) for f in fams]
    rng = np.random.default_rng(0); out = []
    for mid, lab, unit, st in stats:
        a, b = st(A), st(Bm)
        if not A or not Bm: out.append({"id": mid, "label": lab, "unit": unit, "a": a if A else None, "b": b if Bm else None, "diff": None, "ci": None, "verdict": "small group"}); continue
        d = [st(list(rng.choice(A, len(A)))) - st(list(rng.choice(Bm, len(Bm)))) for _ in range(1000)]
        lo, hi = (float(v) for v in np.nanpercentile(d, [2.5, 97.5]))
        verdict = "small group" if min(len(A), len(Bm)) < 6 else ("clear" if lo > 0 or hi < 0 else "uncertain")
        out.append({"id": mid, "label": lab, "unit": unit, "a": float(a), "b": float(b), "diff": float(a - b), "ci": [lo, hi], "verdict": verdict})
    return {"players": players, "player": player, "n_with": len(A), "n_without": len(Bm), "metrics": out,
            "without_matches": [{"date": rows[m]["date"], "opponent": rows[m]["opponent"], "score": rows[m]["score"]} for m in Bm]}
