"""One printable page with the main facts of the other sheets, before a match.

It does not compute anything new: it reads the JSON files and ranks the team against the other teams in the folder.

Usage:  python summary.py "<Team>" [data_dir=.]"""

import sys, os, json, glob, html as H
import numpy as np

TEAM = sys.argv[1]
BASE = sys.argv[2] if len(sys.argv) > 2 else "."
fn = TEAM.replace(" ", "_")


def load(kind, f=fn):
    path = f"{BASE}/{kind}_{f}.json"
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else None


def others(kind):
    """The same sheet of every other team in the folder, by team name."""
    out = {}
    for p in glob.glob(f"{BASE}/{kind}_*.json"):
        if os.path.basename(p) != f"{kind}_{fn}.json":
            out[os.path.basename(p)[len(kind) + 1:-5].replace("_", " ")] = json.load(open(p, encoding="utf-8"))
    return out


REP, RS, SP, TR, XT = load("report"), load("restarts"), load("setpieces"), load("transitions"), load("xthreat")
if REP is None:
    sys.exit(f"report_{fn}.json not found in {BASE}: run oppreport.py first")


def pc(x):
    return f"{100 * x:.1f}%" if 0 < x < 0.01 else f"{100 * x:.0f}%"


def compare(kind, get, value, higher="more"):
    """Rank of the team among the reference teams that have this sheet (1 = highest value)."""
    vals = {}
    for t, d in others(kind).items():
        try:
            v = get(d)
        except (KeyError, TypeError):
            continue
        if v is not None and not (isinstance(v, float) and np.isnan(v)):
            vals[t] = v
    if len(vals) < 3:
        return ""
    allv = sorted(list(vals.values()) + [value], reverse=True)
    rank = allv.index(value) + 1
    m = float(np.mean(list(vals.values())))
    mean = pc(m) if value < 1 else f"{m:.1f}"
    return f" <span class='ref'>Rank {rank} of {len(allv)} teams (1 = most {higher}); other teams' mean {mean}.</span>"


def flag(kind_key, metric):
    if RS is None or kind_key not in RS["kinds"]:
        return ""
    v = RS["kinds"][kind_key]["metrics"][metric]
    if v["last5"] is not None and not (v["ci"][0] <= v["last5"] <= v["ci"][1]):
        return " <span class='chk'>last 5 differ: check on video</span>"
    return ""


facts = []

st = REP["style"]["team"]
txt = f"{st['passes']:.1f} passes per open-play sequence, long passes {pc(st['long'])}."
facts.append(("Build-up", txt + compare("report", lambda d: d["style"]["team"]["passes"], st["passes"], "passes per sequence")))

if RS:
    for k, label in (("Goal kick", "Goal kicks"), ("Keeper", "Keeper distribution")):
        if k not in RS["kinds"]:
            continue
        r = RS["kinds"][k]
        m = r["metrics"]
        side = max(("left", "centre", "right"), key=lambda s: m[s]["season"])
        by_length = r.get("by_length", {})
        receivers = r.get("receivers", {})
        txt = f"{r['per_match']:.1f} per match, first pass short {pc(m['short']['season'])}, most often to the {side} ({pc(m[side]['season'])}); possession ends in own half {pc(m['lost_own_half']['season'])}"
        if "short" in by_length and "long" in by_length:
            txt += f" (short {pc(by_length['short']['lost_own_half'])}, long {pc(by_length['long']['lost_own_half'])})"
        if receivers:
            p, q = next(iter(receivers.items()))
            txt += f". First receiver most often {H.escape(p)} ({pc(q['share'])})"
        rank = compare("restarts", lambda d: d["kinds"][k]["metrics"]["short"]["season"], m["short"]["season"], "short first passes")
        facts.append((label, txt + "." + rank + flag(k, "short")))

if SP and "Corner" in SP["kinds"]:
    c = SP["kinds"]["Corner"]
    z, v = max(c["zones"].items(), key=lambda kv: kv[1]["share"])
    txt = f"{c['per_match']:.1f} per match, most deliveries to the {z} ({pc(v['share'])}), shot after {pc(c['shot'])}"
    if c.get("takers"):
        txt += ", taken mostly by " + " and ".join(H.escape(p) for p in list(c["takers"])[:2])
    facts.append(("Corners", txt + "." + compare("setpieces", lambda d: d["kinds"]["Corner"]["shot"], c["shot"], "shots after corners")))

if SP and "Free kick" in SP["kinds"]:
    f = SP["kinds"]["Free kick"]
    z, v = max(f["zones"].items(), key=lambda kv: kv[1]["share"])
    txt = f"{f['per_match']:.1f} per match, most often {z} ({pc(v['share'])}), shot after {pc(f['shot'])}"
    if f.get("takers"):
        txt += ", taken mostly by " + H.escape(next(iter(f["takers"])))
    facts.append(("Attacking free kicks", txt + "."))

if TR:
    losses, recs = TR["losses"], TR["recoveries"]
    worst, w = max(losses["by_third"].items(), key=lambda kv: kv[1]["conceded10"])
    txt = f"{losses['per_match']:.1f} losses per match; after losses in the {worst} the opponent shoots within 10 s {pc(w['conceded10'])} of the time; ball regained within 5 s after {pc(losses['regain5'])} of losses."
    facts.append(("Losing the ball", txt + compare("transitions", lambda d: d["losses"]["per_match"], losses["per_match"], "losses per match")))
    ft = recs["by_third"].get("final third")
    if ft:
        txt = f"{ft['per_match']:.1f} recoveries per match in the final third, shot within 10 s after {pc(ft['shot10'])} of them."
        rank = compare("transitions", lambda d: d["recoveries"]["by_third"]["final third"]["per_match"], ft["per_match"], "high recoveries")
        facts.append(("Winning the ball high", txt + rank))

if XT:
    x = XT["xt"]
    who = XT["players"][0] if XT["players"] else None
    txt = f"{x['per_match']:.2f} xT added per match by completed passes and carries (carries {pc(XT['xt_carry']['per_match'] / x['per_match'])})"
    if who and who["share"]:
        txt += f"; most by {H.escape(who['player'])} ({pc(who['share'])} of the team's)"
    facts.append(("Moving the ball into danger", txt + "." + compare("xthreat", lambda d: d["xt"]["per_match"], x["per_match"], "xT added")))

fam = REP["phases"]["build-up"]
top = max(fam["families"], key=lambda r: r["share"])
facts.append((
    "Most common build-up family",
    f"{top['fam']}: {pc(top['share'])} of build-up sequences, from x {top['x0']:.0f} to {top['x1']:.0f}, {top['passes']:.1f} passes, shot rate {pc(top['shot'])}. Structure check: {fam['verdict']}.",
))

refs = sorted(set(others("report")) | set(others("restarts")))
links = [
    (f"report_{fn}.html", "Sequence families and style"),
    (f"restarts_{fn}.html", "Goal kicks, keeper, throw-ins"),
    (f"setpieces_{fn}.html", "Corners and free kicks"),
    (f"transitions_{fn}.html", "Losses, recoveries, transitions"),
    (f"xthreat_{fn}.html", "Threat (xT)"),
]
CSS = (
    "body{font-family:Arial,sans-serif;max-width:900px;margin:20px auto;color:#222;font-size:13.5px}h1{color:#1F3A5F;margin-bottom:0}.sub{color:#666;font-size:11.5px;margin-bottom:12px}"
    "table{border-collapse:collapse;width:100%}td{border-bottom:1px solid #ddd;padding:7px 6px;vertical-align:top}td:first-child{font-weight:bold;color:#1F3A5F;width:170px}"
    ".ref{color:#666;font-size:11.5px}.chk{background:#FFF4D6;font-size:11.5px;padding:0 4px}.links a{margin-right:14px}.small{color:#666;font-size:11px;margin-top:12px}@media print{.links{display:none}}"
)
link_html = " ".join(f"<a href='{u}'>{t}</a>" for u, t in links if os.path.exists(f"{BASE}/{u}"))
ref_names = H.escape(", ".join(refs)) if refs else "none"
h = [
    f"<html><head><meta charset='utf-8'><title>Match preparation: {H.escape(TEAM)}</title><style>{CSS}</style></head><body><h1>Match preparation: {H.escape(TEAM)}</h1>",
    f"<div class='sub'>{REP['matches']} matches ({REP['period']}), open-play and restart events. Generated automatically from the four sheets linked below; every number can be traced there.</div><table>",
    "".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a, b in facts),
    "</table>",
    f"<p class='links'>{link_html}</p>",
    f"<p class='small'>Reference teams ({len(refs)}): {ref_names}. They may come from other leagues and seasons, so ranks are a rough guide. 'Check on video' = the last 5 matches fall outside the season interval: a hint, not proof of a change. "
    "Descriptive only: none of these facts was tested as a hypothesis, and the sequence families did not explain shots better than a simple rule on where the sequence ends (thesis validation, 10 teams).</p></body></html>",
]
open(f"{BASE}/prep_{fn}.html", "w", encoding="utf-8").write("".join(h))
print("saved", f"{BASE}/prep_{fn}.html")
