"""Match-preparation page: one printable page with the main facts from the four sheets (report, restarts, set pieces, transitions) and links to them.
Usage:  python summary.py "<Team>" [data_dir=.]
Reads report_/restarts_/setpieces_/transitions_<Team>.json from data_dir and writes prep_<Team>.html there. No new estimates: every number comes from those files.
Each fact is compared with the other teams whose sheets are in data_dir (rank and mean). The reference teams can come from other leagues and seasons: the page says
which and how many. A fact is marked 'check on video' when the last 5 matches fall outside the season interval in the restart sheet."""
import sys, os, json, glob, html as H
import numpy as np
TEAM = sys.argv[1]; BASE = sys.argv[2] if len(sys.argv) > 2 else "."; fn = TEAM.replace(" ", "_")
load = lambda kind, f=fn: json.load(open(f"{BASE}/{kind}_{f}.json", encoding="utf-8")) if os.path.exists(f"{BASE}/{kind}_{f}.json") else None
others = lambda kind: {os.path.basename(p)[len(kind) + 1:-5].replace("_", " "): json.load(open(p, encoding="utf-8")) for p in glob.glob(f"{BASE}/{kind}_*.json") if os.path.basename(p) != f"{kind}_{fn}.json"}
REP, RS, SP, TR = load("report"), load("restarts"), load("setpieces"), load("transitions")
if REP is None: sys.exit(f"report_{fn}.json not found in {BASE}: run oppreport.py first")
pc = lambda x: f"{100 * x:.1f}%" if 0 < x < 0.01 else f"{100 * x:.0f}%"

def compare(kind, get, value, higher="more"):
    """Rank of the team among the reference teams that have this sheet (1 = highest value)."""
    vals = {}
    for t, d in others(kind).items():
        try: v = get(d)
        except (KeyError, TypeError): continue
        if v is not None and not (isinstance(v, float) and np.isnan(v)): vals[t] = v
    if len(vals) < 3: return ""
    allv = sorted(list(vals.values()) + [value], reverse=True); rank = allv.index(value) + 1; m = float(np.mean(list(vals.values())))
    return f" <span class='ref'>Rank {rank} of {len(allv)} teams (1 = most {higher}); other teams' mean {pc(m) if value < 1 else f'{m:.1f}'}.</span>"

def flag(kind_key, metric):
    if RS is None or kind_key not in RS["kinds"]: return ""
    v = RS["kinds"][kind_key]["metrics"][metric]
    return " <span class='chk'>last 5 differ: check on video</span>" if v["last5"] is not None and not (v["ci"][0] <= v["last5"] <= v["ci"][1]) else ""

facts = []
st = REP["style"]["team"]
facts.append(("Build-up", f"{st['passes']:.1f} passes per open-play sequence, long passes {pc(st['long'])}." + compare("report", lambda d: d["style"]["team"]["passes"], st["passes"], "passes per sequence")))
if RS:
    for k, lab in (("Goal kick", "Goal kicks"), ("Keeper", "Keeper distribution")):
        if k not in RS["kinds"]: continue
        r = RS["kinds"][k]; m = r["metrics"]; side = max(("left", "centre", "right"), key=lambda s: m[s]["season"])
        bl = r.get("by_length", {}); rec = r.get("receivers", {})
        txt = f"{r['per_match']:.1f} per match, first pass short {pc(m['short']['season'])}, most often to the {side} ({pc(m[side]['season'])}); possession ends in own half {pc(m['lost_own_half']['season'])}"
        if "short" in bl and "long" in bl: txt += f" (short {pc(bl['short']['lost_own_half'])}, long {pc(bl['long']['lost_own_half'])})"
        if rec: p, q = next(iter(rec.items())); txt += f". First receiver most often {H.escape(p)} ({pc(q['share'])})"
        facts.append((lab, txt + "." + compare("restarts", lambda d, k=k: d["kinds"][k]["metrics"]["short"]["season"], m["short"]["season"], "short first passes") + flag(k, "short")))
if SP and "Corner" in SP["kinds"]:
    c = SP["kinds"]["Corner"]; z, v = max(c["zones"].items(), key=lambda kv: kv[1]["share"])
    txt = f"{c['per_match']:.1f} per match, most deliveries to the {z} ({pc(v['share'])}), shot after {pc(c['shot'])}"
    if c.get("takers"): txt += ", taken mostly by " + " and ".join(H.escape(p) for p in list(c["takers"])[:2])
    facts.append(("Corners", txt + "." + compare("setpieces", lambda d: d["kinds"]["Corner"]["shot"], c["shot"], "shots after corners")))
if SP and "Free kick" in SP["kinds"]:
    f = SP["kinds"]["Free kick"]; z, v = max(f["zones"].items(), key=lambda kv: kv[1]["share"])
    facts.append(("Attacking free kicks", f"{f['per_match']:.1f} per match, most often {z} ({pc(v['share'])}), shot after {pc(f['shot'])}" + (", taken mostly by " + H.escape(next(iter(f["takers"]))) if f.get("takers") else "") + "."))
if TR:
    l, r = TR["losses"], TR["recoveries"]; worst = max(l["by_third"].items(), key=lambda kv: kv[1]["conceded10"])
    facts.append(("Losing the ball", f"{l['per_match']:.1f} losses per match; after losses in the {worst[0]} the opponent shoots within 10 s {pc(worst[1]['conceded10'])} of the time; ball regained within 5 s after {pc(l['regain5'])} of losses."
                  + compare("transitions", lambda d: d["losses"]["per_match"], l["per_match"], "losses per match")))
    ft = r["by_third"].get("final third")
    if ft: facts.append(("Winning the ball high", f"{ft['per_match']:.1f} recoveries per match in the final third, shot within 10 s after {pc(ft['shot10'])} of them." + compare("transitions", lambda d: d["recoveries"]["by_third"]["final third"]["per_match"], ft["per_match"], "high recoveries")))
fam = REP["phases"]["build-up"]; top = max(fam["families"], key=lambda r: r["share"])
facts.append(("Most common build-up family", f"{top['fam']}: {pc(top['share'])} of build-up sequences, from x {top['x0']:.0f} to {top['x1']:.0f}, {top['passes']:.1f} passes, shot rate {pc(top['shot'])}. Structure check: {fam['verdict']}."))

refs = sorted(set(others("report")) | set(others("restarts")))
links = [(f"report_{fn}.html", "Sequence families and style"), (f"restarts_{fn}.html", "Goal kicks, keeper, throw-ins"), (f"setpieces_{fn}.html", "Corners and free kicks"), (f"transitions_{fn}.html", "Losses, recoveries, transitions")]
css = ("body{font-family:Arial,sans-serif;max-width:900px;margin:20px auto;color:#222;font-size:13.5px}h1{color:#1F3A5F;margin-bottom:0}.sub{color:#666;font-size:11.5px;margin-bottom:12px}"
       "table{border-collapse:collapse;width:100%}td{border-bottom:1px solid #ddd;padding:7px 6px;vertical-align:top}td:first-child{font-weight:bold;color:#1F3A5F;width:170px}"
       ".ref{color:#666;font-size:11.5px}.chk{background:#FFF4D6;font-size:11.5px;padding:0 4px}.links a{margin-right:14px}.small{color:#666;font-size:11px;margin-top:12px}@media print{.links{display:none}}")
h = [f"<html><head><meta charset='utf-8'><title>Match preparation: {H.escape(TEAM)}</title><style>{css}</style></head><body><h1>Match preparation: {H.escape(TEAM)}</h1>",
     f"<div class='sub'>{REP['matches']} matches ({REP['period']}), open-play and restart events. Generated automatically from the four sheets linked below; every number can be traced there.</div><table>",
     "".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a, b in facts), "</table>",
     "<p class='links'>" + " ".join(f"<a href='{u}'>{t}</a>" for u, t in links if os.path.exists(f"{BASE}/{u}")) + "</p>",
     f"<p class='small'>Reference teams ({len(refs)}): {H.escape(', '.join(refs)) if refs else 'none'}. They may come from other leagues and seasons, so ranks are a rough guide. 'Check on video' = the last 5 matches fall outside the season interval: a hint, not proof of a change. "
     "Descriptive only: none of these facts was tested as a hypothesis, and the sequence families did not explain shots better than a simple rule on where the sequence ends (thesis validation, 10 teams).</p></body></html>"]
open(f"{BASE}/prep_{fn}.html", "w", encoding="utf-8").write("".join(h)); print("saved", f"{BASE}/prep_{fn}.html")
