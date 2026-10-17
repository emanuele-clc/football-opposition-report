"""Game plan: the opponent's formations and style in a few lines, plus rule-based hints on how to approach them, optionally against your own team.
HINTS, NOT ADVICE. Each hint fires from a fixed rule on where the opponent (and your team) ranks among the teams in the data folder, and shows the numbers
that made it fire. No rule was tested for whether following it changes results: they say where to look on video, not what will work.
Rules (fixed before looking at their output): 'top' = among the k highest of n teams, 'bottom' = among the k lowest, k = max(1, n // 5); no rank-based hint
with fewer than 4 teams. Matchup facts come from matchups_<Team>.json (only 'clear' differences not linked to how the groups are formed).
'Ask the AI' (optional) sends this page's numbers and the question to the Claude API: only with ANTHROPIC_API_KEY set; the data leave the computer."""
import json, os

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
     "The key duel of the match: look at your own past matches against a high press (below) and decide whether to keep building short.", "matchups"),
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
            "ai": bool(os.environ.get("ANTHROPIC_API_KEY"))}


SYSTEM = """You help a football analyst prepare a match against an opponent. You only know the numbers in the JSON below (StatsBomb open data, descriptive,
ranked against the other teams in the folder; seasons can differ). Rules: use only these numbers and say which ones you use; say clearly when the data cannot
answer (for example which formation would win: nothing here was tested for that); give ideas to check on video, not certainties; never invent players,
injuries or facts not in the data. Answer in the language of the question, in at most 180 words, plain text with short lines."""


def ask(plan, question):
    import anthropic
    client = anthropic.Anthropic()
    msg = client.messages.create(model=os.environ.get("OPPREPORT_MODEL", "claude-opus-5-5"), max_tokens=700, system=SYSTEM,
                                 messages=[{"role": "user", "content": f"DATA:\n{json.dumps(plan, ensure_ascii=False)}\n\nQUESTION: {question}"}])
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
