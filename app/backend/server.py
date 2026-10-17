"""Local API for the opposition report app.
Serves the files that src/oppreport.py writes (report_/restarts_/setpieces_/transitions_<Team>.json and the clip CSVs),
ranks each team against the other teams found in the same folder, exports filtered clip lists (CSV, video-tool XML)
and can run the pipeline for a new team when the folder holds StatsBomb match lists and events.
No new estimates: every number comes from the pipeline files.
Run:  python -X utf8 app/run.py [--data-dir <data_folder>]"""
import csv, functools, glob, io, json, os, re, subprocess, sys, tempfile, threading, time, uuid, zipfile
from urllib.parse import quote
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gameplan as GP

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA = os.path.abspath(os.environ.get("OPPREPORT_DATA") or os.path.join(ROOT, "examples"))
DIST = os.path.join(ROOT, "app", "frontend", "dist")
SHEETS = ("report", "restarts", "setpieces", "transitions", "defending", "matchups")
CLIPS = {"sequences": "clips", "restarts": "restart_clips", "setpieces": "setpiece_clips", "transitions": "transition_clips"}
INT_COLS = {"match", "half", "minute", "second", "passes", "duration_s", "ended_in_shot"}

app = FastAPI(title="Opposition report")


def key_of(team): return team.replace(" ", "_")


def load(kind, key):
    p = os.path.join(DATA, f"{kind}_{key}.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


def teams():
    out = {}
    for p in sorted(glob.glob(os.path.join(DATA, "report_*.json"))):
        d = json.load(open(p, encoding="utf-8")); k = os.path.basename(p)[len("report_"):-5]
        out[k] = {"key": k, "team": d["team"], "matches": d["matches"], "period": d["period"], "sequences": d["sequences"],
                  "sheets": [s for s in SHEETS if os.path.exists(os.path.join(DATA, f"{s}_{k}.json"))],
                  "clips": [c for c, f in CLIPS.items() if os.path.exists(os.path.join(DATA, f"{f}_{k}.csv"))]}
    return out


def need(key):
    t = teams()
    if key not in t: raise HTTPException(404, f"No report for '{key}' in {DATA}. Run the pipeline for this team first.")
    return t[key]


# Facts ranked against the other teams in the data folder (rank 1 = highest value, as in src/report/summary.py).
def _m(kind, metric): return lambda d: d["kinds"][kind]["metrics"][metric]["season"]
def _mci(kind, metric): return lambda d: d["kinds"][kind]["metrics"][metric]["ci"]
METRICS = [
    # id, group, label, sheet, getter, ci getter, unit, caution
    ("passes", "Build-up", "Passes per sequence", "report", lambda d: d["style"]["team"]["passes"], lambda d: d["style"]["team_ci"]["passes"], "num", None),
    ("long", "Build-up", "Share of long passes (30+)", "report", lambda d: d["style"]["team"]["long"], lambda d: d["style"]["team_ci"]["long"], "pct", None),
    ("dur", "Build-up", "Duration (seconds)", "report", lambda d: d["style"]["team"]["dur"], lambda d: d["style"]["team_ci"]["dur"], "num", None),
    ("shot", "Build-up", "Sequences ending in a shot", "report", lambda d: d["style"]["team"]["shot"], lambda d: d["style"]["team_ci"]["shot"], "pct",
     "Shot rate could not be told apart between teams reliably even with 15 matches."),
    ("buildup_share", "Build-up", "Sequences starting in own half (x < 45)", "report", lambda d: d["style"]["team"]["buildup_share"], lambda d: d["style"]["team_ci"]["buildup_share"], "pct",
     "The share of sequences starting in the own half could not be told apart between teams reliably even with 15 matches."),
    ("gk_short", "Restarts", "Goal kicks: first pass short", "restarts", _m("Goal kick", "short"), _mci("Goal kick", "short"), "pct", None),
    ("gk_opp_half", "Restarts", "Goal kicks: reached opponent half", "restarts", _m("Goal kick", "opp_half"), _mci("Goal kick", "opp_half"), "pct", None),
    ("kp_short", "Restarts", "Keeper: first pass short", "restarts", _m("Keeper", "short"), _mci("Keeper", "short"), "pct", None),
    ("corner_pm", "Set pieces", "Corners per match", "setpieces", lambda d: d["kinds"]["Corner"]["per_match"], None, "num", None),
    ("corner_shot", "Set pieces", "Corners: shot after", "setpieces", lambda d: d["kinds"]["Corner"]["shot"], lambda d: d["kinds"]["Corner"]["shot_ci"], "pct", None),
    ("losses_pm", "Transitions", "Losses per match", "transitions", lambda d: d["losses"]["per_match"], None, "num", None),
    ("regain5", "Transitions", "Ball regained within 5 s of a loss", "transitions", lambda d: d["losses"]["regain5"], lambda d: d["losses"]["regain5_ci"], "pct",
     "The counter-press share varied little between the teams we tested (17-19%): it describes, it does not separate styles."),
    ("high_rec_pm", "Transitions", "Recoveries per match in the final third", "transitions", lambda d: d["recoveries"]["by_third"]["final third"]["per_match"],
     lambda d: d["recoveries"]["by_third"]["final third"]["per_match_ci"], "num", None),
    ("ppda", "Defending", "PPDA: opponent passes per defensive action", "defending", lambda d: d["ppda"]["value"], lambda d: d["ppda"]["ci"], "num",
     "PPDA: lower means more intense pressing; it also depends on how much the opponent has the ball, so read it with the pressures in the final third."),
    ("press_pm", "Defending", "Pressures per match", "defending", lambda d: d["pressures"]["per_match"], lambda d: d["pressures"]["ci"], "num", None),
    ("press_final", "Defending", "Share of pressures in the final third", "defending", lambda d: d["pressures"]["by_third"]["final third"]["share"], None, "pct", None),
    ("def_height", "Defending", "Height of defensive actions (mean x, 0-120)", "defending", lambda d: d["height"]["mean_x"], lambda d: d["height"]["ci"], "num", None),
    ("xga_pm", "Defending", "xG conceded per match", "defending", lambda d: d["conceded"]["xg_per_match"], lambda d: d["conceded"]["xg_ci"], "num2", None),
]


def ranks(key):
    cache = {s: {k: load(s, k) for k in teams()} for s in SHEETS}
    out = []
    for mid, group, label, sheet, get, getci, unit, caution in METRICS:
        vals = []
        for k, d in cache[sheet].items():
            try: v = get(d) if d else None
            except (KeyError, TypeError): v = None
            if v is not None and v == v: vals.append({"key": k, "team": d["team"], "value": v})
        mine = next((v for v in vals if v["key"] == key), None)
        if mine is None: continue
        vals.sort(key=lambda v: -v["value"])
        ci = None
        if getci:
            try: ci = getci(cache[sheet][key])
            except (KeyError, TypeError): ci = None
        out.append({"id": mid, "group": group, "label": label, "sheet": sheet, "unit": unit, "caution": caution, "value": mine["value"], "ci": ci,
                    "rank": [v["key"] for v in vals].index(key) + 1, "of": len(vals), "teams": vals})
    return out


@app.get("/api/info")
def info():
    return {"data_dir": DATA, "is_examples": os.path.normcase(DATA) == os.path.normcase(os.path.join(ROOT, "examples")), "can_generate": bool(sources()),
            "has_events": os.path.isdir(os.path.join(DATA, "ev"))}


@app.get("/api/teams")
def list_teams(): return list(teams().values())


def link_examples(key, rep):
    """Give each family example its match id (from the clip list) so the app can replay it from the events."""
    p = os.path.join(DATA, f"clips_{key}.csv")
    if not rep or not os.path.exists(p): return rep
    idx = {}
    with open(p, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f): idx[(r["family"], r["date"], r["opponent"], r["half"], r["minute"], r["second"])] = int(r["match"])
    for ph in rep["phases"].values():
        for fam in ph["families"]:
            for e in fam["examples"]:
                e["match"] = idx.get((fam["fam"], e["date"], e["opponent"], str(e["half"]), str(e["minute"]), str(e["second"])))
    return rep


@app.get("/api/teams/{key}")
def team(key: str):
    t = need(key)
    return {**t, **{s: load(s, key) for s in SHEETS}, "report": link_examples(key, load("report", key)), "ranks": ranks(key),
            "references": [v["team"] for k, v in teams().items() if k != key]}


# Replays: the actual actions of one clip, read from the StatsBomb events (only when <data>/ev exists).
ACTIONS = {"Pass", "Carry", "Shot", "Dribble", "Ball Recovery", "Interception", "Clearance", "Goal Keeper", "Miscontrol", "Dispossessed"}


@functools.lru_cache(maxsize=24)
def events(match):
    p = os.path.join(DATA, "ev", f"{match}.json")
    if not os.path.exists(p): raise HTTPException(404, f"Events for match {match} are not in {DATA}/ev: replays need the raw StatsBomb files.")
    return json.load(open(p, encoding="utf-8"))


def secs(ts):
    h, m, s = ts.split(":"); return int(h) * 3600 + int(m) * 60 + float(s)


@app.get("/api/teams/{key}/replay")
def replay(key: str, match: int, half: int, minute: int, second: int, window: bool = False):
    """Possession that starts at this clip time (sequences, restarts, set pieces) or, with window=true, every action from 6 s before to 10 s after
    (losses and recoveries). Coordinates are turned so that the team always attacks left to right (0-120 x 0-80)."""
    team_name = need(key)["team"]; ev = events(match)
    at = [e for e in ev if e.get("period") == half and e.get("minute") == minute and e.get("second") == second and e["type"]["name"] in ACTIONS]
    if not at:
        at = [e for e in ev if e.get("period") == half and e.get("minute") == minute and abs(e.get("second", -9) - second) <= 1 and e["type"]["name"] in ACTIONS]
    if not at: raise HTTPException(404, "No action found at that time in the event file.")
    first = next((e for e in at if e["team"]["name"] == team_name), at[0]); t0 = secs(first["timestamp"])
    if window: chosen = [e for e in ev if e.get("period") == half and t0 - 6 <= secs(e["timestamp"]) <= t0 + 10]
    else: chosen = [e for e in ev if e.get("period") == half and e.get("possession") == first.get("possession")]
    out = []
    for e in chosen:
        ty = e["type"]["name"]
        if ty not in ACTIONS or "location" not in e: continue
        us = e["team"]["name"] == team_name; flip = (lambda p: [p[0], p[1]]) if us else (lambda p: [120 - p[0], 80 - p[1]])
        a = {"t": round(secs(e["timestamp"]) - t0, 2), "type": ty, "us": us, "player": e.get("player", {}).get("name", ""), "x": flip(e["location"])[0], "y": flip(e["location"])[1]}
        end = (e.get("pass") or e.get("carry") or e.get("shot") or {}).get("end_location")
        if end: a["ex"], a["ey"] = flip(end)[:2]
        if ty == "Pass":
            a["ok"] = "outcome" not in e["pass"]; a["to"] = e["pass"].get("recipient", {}).get("name", "")
            a["long"] = e["pass"].get("length", 0) >= 30; a["kind"] = e["pass"].get("type", {}).get("name", "")
        if ty == "Shot":
            a["outcome"] = e["shot"]["outcome"]["name"]; a["xg"] = e["shot"].get("statsbomb_xg")
        out.append(a)
    if not out: raise HTTPException(404, "No actions with a location in this clip.")
    return {"match": match, "half": half, "minute": minute, "second": second, "play_pattern": first.get("play_pattern", {}).get("name", ""), "actions": out}


def read_clips(key, kind):
    if kind not in CLIPS: raise HTTPException(404, f"Unknown clip list '{kind}'. Use one of: {', '.join(CLIPS)}.")
    p = os.path.join(DATA, f"{CLIPS[kind]}_{key}.csv")
    if not os.path.exists(p): raise HTTPException(404, f"{os.path.basename(p)} not found in {DATA}.")
    with open(p, encoding="utf-8", newline="") as f:
        r = csv.DictReader(f); return r.fieldnames, list(r)


def filtered(key, kind, family, opponent, shot, half):
    cols, rows = read_clips(key, kind)
    fam = set(family.split("|")) if family else None
    rows = [r for r in rows if (not fam or r["family"] in fam) and (not opponent or r["opponent"] == opponent)
            and (not shot or r["ended_in_shot"] == "1") and (not half or r["half"] == str(half))]
    return cols, rows


@app.get("/api/teams/{key}/clips/{kind}")
def clips(key: str, kind: str):
    need(key); cols, rows = read_clips(key, kind)
    for r in rows:
        for c in INT_COLS & r.keys():
            try: r[c] = int(float(r[c]))
            except ValueError: pass
    return {"columns": cols, "rows": rows}


@app.get("/api/teams/{key}/export/{kind}.csv")
def export_csv(key: str, kind: str, family: str = "", opponent: str = "", shot: bool = False, half: int = 0):
    need(key); cols, rows = filtered(key, kind, family, opponent, shot, half)
    buf = io.StringIO(); w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n"); w.writeheader(); w.writerows(rows)
    name = f"{CLIPS[kind]}_{key}" + (f"_{family.replace('|', '+').replace(' ', '-')}" if family else "") + ".csv"
    return StreamingResponse(iter([buf.getvalue().encode("utf-8")]), media_type="text/csv",
                             headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}"})


@app.get("/api/teams/{key}/export/{kind}.zip")
def export_xml(key: str, kind: str, family: str = "", opponent: str = "", shot: bool = False, half: int = 0):
    """Video-tool XML (one file per match) through src/report/clips_to_xml.py, zipped."""
    need(key); cols, rows = filtered(key, kind, family, opponent, shot, half)
    if not rows: raise HTTPException(400, "No clips match these filters: nothing to export.")
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, f"{CLIPS[kind]}_{key}.csv")
        with open(src, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
        outd = os.path.join(tmp, "xml")
        r = subprocess.run([sys.executable, "-X", "utf8", os.path.join(ROOT, "src", "report", "clips_to_xml.py"), src, outd], capture_output=True, text=True, encoding="utf-8")
        if r.returncode: raise HTTPException(500, "XML export failed: " + (r.stderr or r.stdout)[-500:])
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for p in sorted(glob.glob(os.path.join(outd, "*"))): z.write(p, os.path.basename(p))
    return StreamingResponse(iter([buf.getvalue()]), media_type="application/zip",
                             headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(f'xml_{CLIPS[kind]}_{key}.zip')}"})


@app.get("/sheets/{name}")
def sheet(name: str):
    """The printable HTML sheets written by the pipeline (prep_, report_, restarts_, ...)."""
    if not re.fullmatch(r"(prep|report|restarts|setpieces|transitions|defending|review)_[^/\\]+\.html", name): raise HTTPException(404, "Not a report sheet.")
    p = os.path.join(DATA, name)
    if not os.path.exists(p): raise HTTPException(404, f"{name} not found in {DATA}.")
    return HTMLResponse(open(p, encoding="utf-8").read())


# Every sequence of a team as a path on the pitch (start, then the end of each pass and carry), as in src/week2/sequences_clustering.py.
def clip_index(key):
    p = os.path.join(DATA, f"clips_{key}.csv")
    if not os.path.exists(p): raise HTTPException(404, f"clips_{key}.csv not found in {DATA}.")
    with open(p, encoding="utf-8", newline="") as f: return list(csv.DictReader(f))


def possession_path(ev, team_name, half, minute, second):
    first = next((e for e in ev if e.get("period") == half and e.get("minute") == minute and e.get("second") == second
                  and e["team"]["name"] == team_name and e["type"]["name"] in ("Pass", "Carry", "Shot", "Dribble")), None)
    if first is None: return None
    es = [e for e in ev if e.get("period") == half and e.get("possession") == first.get("possession") and e["team"]["name"] == team_name
          and e["type"]["name"] in ("Pass", "Carry", "Shot", "Dribble")]
    pts = [es[0]["location"][:2]]
    for e in es:
        end = (e.get("pass") or e.get("carry") or {}).get("end_location") if e["type"]["name"] in ("Pass", "Carry") else None
        if end and end[:2] != pts[-1]: pts.append(end[:2])
    return [[round(x, 1), round(y, 1)] for x, y in pts]


@app.get("/api/teams/{key}/paths")
def paths(key: str):
    """Cached in <data>/app_cache. Needs <data>/ev."""
    team_name = need(key)["team"]; cache = os.path.join(DATA, "app_cache", f"paths_{key}.json")
    if os.path.exists(cache) and os.path.getmtime(cache) >= os.path.getmtime(os.path.join(DATA, f"clips_{key}.csv")):
        res = json.load(open(cache, encoding="utf-8"))
        if all("at" in q for q in res["paths"]): return res
    if not os.path.isdir(os.path.join(DATA, "ev")): raise HTTPException(404, "Paths need the raw event files in <data>/ev.")
    out, rows = [], clip_index(key)
    by_match = {}
    for r in rows: by_match.setdefault(int(r["match"]), []).append(r)
    for m, rs in by_match.items():
        ev = json.load(open(os.path.join(DATA, "ev", f"{m}.json"), encoding="utf-8"))
        for r in rs:
            pts = possession_path(ev, team_name, int(r["half"]), int(r["minute"]), int(r["second"]))
            if pts: out.append({"family": r["family"], "shot": int(r["ended_in_shot"]), "pts": pts, "at": [int(r["match"]), int(r["half"]), int(r["minute"]), int(r["second"])]})
    res = {"team": team_name, "n": len(out), "of": len(rows), "paths": out}
    os.makedirs(os.path.dirname(cache), exist_ok=True); json.dump(res, open(cache, "w", encoding="utf-8"))
    return res


def team_matches(key):
    """Match ids of a team, from its restart and sequence clip lists."""
    ids = set()
    for f in ("restart_clips", "clips"):
        p = os.path.join(DATA, f"{f}_{key}.csv")
        if os.path.exists(p):
            with open(p, encoding="utf-8", newline="") as fh: ids |= {int(r["match"]) for r in csv.DictReader(fh)}
    return sorted(ids)


def cached(key, name, build):
    """JSON cache in <data>/app_cache, rebuilt when the report is newer."""
    if not os.path.isdir(os.path.join(DATA, "ev")): raise HTTPException(404, "This view needs the raw event files in <data>/ev.")
    cache = os.path.join(DATA, "app_cache", f"{name}_{key}.json")
    if os.path.exists(cache) and os.path.getmtime(cache) >= os.path.getmtime(os.path.join(DATA, f"report_{key}.json")):
        return json.load(open(cache, encoding="utf-8"))
    res = build(); os.makedirs(os.path.dirname(cache), exist_ok=True); json.dump(res, open(cache, "w", encoding="utf-8"), ensure_ascii=False)
    return res


# Pressing map: first pass of every goal kick, keeper distribution and throw-in, with the same definitions as src/report/restarts.py.
RESTART_PP = {"From Goal Kick": "Goal kick", "From Keeper": "Keeper", "From Throw In": "Throw-in"}


def _end_of(e):
    t = e["type"]["name"]
    if t == "Pass": return e["pass"]["end_location"]
    if t == "Carry": return e["carry"]["end_location"]
    return e.get("location")


@app.get("/api/teams/{key}/pressing")
def pressing(key: str):
    team_name = need(key)["team"]

    def build():
        out = []
        for m in team_matches(key):
            ev = json.load(open(os.path.join(DATA, "ev", f"{m}.json"), encoding="utf-8")); poss = {}
            for e in ev:
                if e.get("possession_team", {}).get("name") == team_name and e["team"]["name"] == team_name and e["play_pattern"]["name"] in RESTART_PP and e["type"]["name"] in ("Pass", "Carry", "Shot", "Dribble"):
                    poss.setdefault(e["possession"], []).append(e)
            for es in poss.values():
                passes = [e for e in es if e["type"]["name"] == "Pass"]
                if not passes or es[0].get("location") is None: continue
                p0 = passes[0]; kind = RESTART_PP[es[0]["play_pattern"]["name"]]
                if kind == "Throw-in": kind += " own half" if es[0]["location"][0] < 60 else " opp. half"
                ends = [_end_of(e) for e in es if _end_of(e) is not None]; xs = [q[0] for q in ends]; shot = any(e["type"]["name"] == "Shot" for e in es)
                out.append({"kind": kind, "match": m, "half": es[0]["period"], "minute": es[0]["minute"], "second": es[0]["second"],
                            "x": p0["location"][0], "y": p0["location"][1], "ex": p0["pass"]["end_location"][0], "ey": p0["pass"]["end_location"][1],
                            "short": int(p0["pass"].get("length", 0) < 30), "receiver": (p0["pass"].get("recipient") or {}).get("name") or "",
                            "complete": int("outcome" not in p0["pass"]), "opp_half": int(max(xs) >= 60), "shot": int(shot), "lost_own_half": int(not shot and xs[-1] < 60)})
        return {"team": team_name, "restarts": out}
    return cached(key, "pressing", build)


# Who passes to whom inside each sequence family (completed passes with a recipient).
@app.get("/api/teams/{key}/network")
def network(key: str):
    team_name = need(key)["team"]

    def build():
        fams, by_match, shirt = {}, {}, {}
        for r in clip_index(key): by_match.setdefault(int(r["match"]), []).append(r)
        for m, rs in by_match.items():
            ev = json.load(open(os.path.join(DATA, "ev", f"{m}.json"), encoding="utf-8"))
            for e in ev:
                if e["type"]["name"] in ("Starting XI", "Tactical Shift") and e["team"]["name"] == team_name:
                    for pl in e.get("tactics", {}).get("lineup", []): shirt[pl["player"]["name"]] = pl.get("jersey_number")
            for r in rs:
                half, minute, second = int(r["half"]), int(r["minute"]), int(r["second"])
                first = next((e for e in ev if e.get("period") == half and e.get("minute") == minute and e.get("second") == second
                              and e["team"]["name"] == team_name and e["type"]["name"] in ("Pass", "Carry", "Shot", "Dribble")), None)
                if first is None: continue
                f = fams.setdefault(r["family"], {"sequences": 0, "nodes": {}, "edges": {}}); f["sequences"] += 1
                for e in ev:
                    if e.get("period") != half or e.get("possession") != first.get("possession") or e["team"]["name"] != team_name or e["type"]["name"] != "Pass": continue
                    if "outcome" in e["pass"] or not e["pass"].get("recipient"): continue
                    a, b = e["player"]["name"], e["pass"]["recipient"]["name"]
                    for who, loc in ((a, e["location"]), (b, e["pass"]["end_location"])):
                        n = f["nodes"].setdefault(who, [0, 0.0, 0.0]); n[0] += 1; n[1] += loc[0]; n[2] += loc[1]
                    k = " | ".join(sorted((a, b))); f["edges"][k] = f["edges"].get(k, 0) + 1
        res = {}
        for fam, f in fams.items():
            res[fam] = {"sequences": f["sequences"],
                        "nodes": [{"player": p, "shirt": shirt.get(p), "touches": n[0], "x": round(n[1] / n[0], 1), "y": round(n[2] / n[0], 1)} for p, n in f["nodes"].items()],
                        "edges": [{"a": k.split(" | ")[0], "b": k.split(" | ")[1], "passes": v} for k, v in f["edges"].items()]}
        return {"team": team_name, "families": res}
    return cached(key, "network", build)


# A replay as an animated GIF, to send to the players (same actions as /replay).
@app.get("/api/teams/{key}/replay.gif")
def replay_gif(key: str, match: int, half: int, minute: int, second: int, window: bool = False, title: str = ""):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation, PillowWriter
    r = replay(key, match, half, minute, second, window); acts = r["actions"]; team_name = need(key)["team"]
    fig, ax = plt.subplots(figsize=(7.2, 5.0), dpi=100); fig.patch.set_facecolor("#121a33"); fig.subplots_adjust(0.02, 0.1, 0.98, 0.88)
    ax.set_facecolor("#163a2a"); ax.set_xlim(-3, 123); ax.set_ylim(83, -3); ax.set_aspect("equal"); ax.axis("off")
    ax.add_patch(plt.Rectangle((-3, -3), 126, 86, color="#163a2a", lw=0))
    for i in range(1, 12, 2): ax.add_patch(plt.Rectangle((i * 10, 0), 10, 80, color="#19412f", lw=0))
    L = dict(color="white", alpha=0.4, lw=1)
    for xs, ys in (([0, 120, 120, 0, 0], [0, 0, 80, 80, 0]), ([60, 60], [0, 80]), ([0, 18, 18, 0], [18, 18, 62, 62]), ([120, 102, 102, 120], [18, 18, 62, 62]),
                   ([0, 6, 6, 0], [30, 30, 50, 50]), ([120, 114, 114, 120], [30, 30, 50, 50])): ax.plot(xs, ys, **L)
    ax.add_patch(plt.Circle((60, 40), 9.15, fill=False, **L))
    fig.text(0.03, 0.93, (title or f"{team_name}").upper(), color="#ffd23f", fontsize=15, fontweight="bold", style="italic")
    fig.text(0.97, 0.93, f"half {half}, {minute}:{second:02d}", color="#c9d1ea", fontsize=11, ha="right")
    cap = fig.text(0.03, 0.04, "", color="white", fontsize=11); ball, = ax.plot([], [], "o", ms=9, color="white", mec="#121a33", zorder=5)
    frames = list(range(len(acts) + 1)) + [len(acts)] * 6

    def draw(k):
        if k == 0 or k > len(acts): return
        a = acts[k - 1]; ex, ey = a.get("ex", a["x"]), a.get("ey", a["y"])
        col = "#ffd23f" if a["us"] else "#ff8a80"
        if a["type"] == "Pass": ax.annotate("", (ex, ey), (a["x"], a["y"]), arrowprops=dict(arrowstyle="-|>", color=col, lw=2, ls="-" if a.get("ok") else ":"))
        elif a["type"] == "Carry": ax.plot([a["x"], ex], [a["y"], ey], color="white" if a["us"] else col, lw=1.4, ls="--", alpha=0.85)
        elif a["type"] == "Shot": ax.plot([a["x"], ex], [a["y"], ey], color="#ff5a4e", lw=3)
        else: ax.plot(a["x"], a["y"], "x", color="white" if a["us"] else col, ms=7, mew=2)
        ball.set_data([ex], [ey])
        who = a["player"].split(" ")[-1] if a["player"] else ""
        txt = {"Pass": f"{who} → {a.get('to', '').split(' ')[-1]}" if a.get("ok") else f"{who}: pass not completed", "Carry": f"{who} carries", "Shot": f"{who} shoots: {a.get('outcome', '')}"}
        cap.set_text(("" if a["us"] else "Opponent: ") + txt.get(a["type"], f"{who}: {a['type'].lower()}"))
    anim = FuncAnimation(fig, draw, frames=frames, interval=700)
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "replay.gif"); anim.save(p, writer=PillowWriter(fps=1.4)); plt.close(fig)
        data = open(p, "rb").read()
    name = f"replay_{key}_{match}_{half}_{minute}-{second:02d}.gif"
    return StreamingResponse(iter([data]), media_type="image/gif", headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}"})


# "More like this": the sequences of the season closest to a chosen one (same numbers the families are built on, standardised).
def _seq_features(pts, passes, dur):
    import numpy as np
    P = np.array(pts, dtype=float); L = float(np.sum(np.linalg.norm(np.diff(P, axis=0), axis=1))) if len(P) > 1 else 0.0
    return [P[0, 0], abs(P[0, 1] - 40), P[-1, 0], abs(P[-1, 1] - 40), P[-1, 0] - P[0, 0], L, (P[-1, 0] - P[0, 0]) / max(L, 1), float(passes), float(P[:, 1].std()), float(dur)]


@app.get("/api/teams/{key}/similar")
def similar(key: str, match: int, half: int, minute: int, second: int, n: int = 8):
    import numpy as np
    by_at = {tuple(q["at"]): q for q in paths(key)["paths"]}
    rows = [r for r in clip_index(key) if (int(r["match"]), int(r["half"]), int(r["minute"]), int(r["second"])) in by_at]
    pth = [by_at[(int(r["match"]), int(r["half"]), int(r["minute"]), int(r["second"]))] for r in rows]
    X = np.array([_seq_features(q["pts"], int(r["passes"]), int(r["duration_s"])) for q, r in zip(pth, rows)])
    Z = (X - X.mean(0)) / np.where(X.std(0) > 0, X.std(0), 1)
    i = next((j for j, r in enumerate(rows) if int(r["match"]) == match and int(r["half"]) == half and int(r["minute"]) == minute and int(r["second"]) == second), None)
    if i is None: raise HTTPException(404, "This clip is not in the sequence list.")
    d = np.sqrt(((Z - Z[i]) ** 2).sum(1)); d[i] = np.inf; order = np.argsort(d)[:max(1, min(n, 20))]
    typical = float(np.median(np.sort(np.sqrt(((Z[:, None, :] - Z[None, :200, :]) ** 2).sum(-1)), axis=0)[1]))  # median nearest-neighbour distance, for scale
    return {"of": rows[i], "similar": [{**rows[j], "distance": round(float(d[j]), 2), "pts": pth[j]["pts"]} for j in order], "typical_nn_distance": round(typical, 2)}


# Style map: every team in the folder placed by its numbers (principal components of the standardised facts used for the ranks).
@app.get("/api/stylemap")
def stylemap():
    import numpy as np
    ts = teams(); keys = list(ts); per = {k: {r["id"]: r for r in ranks(k)} for k in keys}
    ids = [m[0] for m in METRICS if all(m[0] in per[k] for k in keys)]
    if len(keys) < 3 or len(ids) < 3: raise HTTPException(400, "The style map needs at least 3 teams with the same sheets.")
    X = np.array([[per[k][i]["value"] for i in ids] for k in keys]); Z = (X - X.mean(0)) / np.where(X.std(0) > 0, X.std(0), 1)
    U, S_, Vt = np.linalg.svd(Z, full_matrices=False); pc = U[:, :2] * S_[:2]; var = (S_ ** 2) / (S_ ** 2).sum()
    for a in range(2):
        j = int(np.argmax(np.abs(Vt[a])))
        if Vt[a, j] < 0: Vt[a] *= -1; pc[:, a] *= -1
    lab = {m[0]: m[2] for m in METRICS}
    axes = [{"explained": round(float(var[a]), 3), "loadings": sorted(({"id": i, "label": lab[i], "weight": round(float(Vt[a, n]), 3)} for n, i in enumerate(ids)), key=lambda x: -abs(x["weight"]))[:4]} for a in range(2)]
    D = np.sqrt(((Z[:, None, :] - Z[None]) ** 2).sum(-1))
    pts = [{"key": k, "team": ts[k]["team"], "period": ts[k]["period"], "x": round(float(pc[n, 0]), 3), "y": round(float(pc[n, 1]), 3),
            "nearest": [{"team": ts[keys[m]]["team"], "distance": round(float(D[n, m]), 2)} for m in np.argsort(D[n])[1:4]]} for n, k in enumerate(keys)]
    return {"metrics": [lab[i] for i in ids], "axes": axes, "teams": pts}


# Game plan: formations, style in a few lines and rule-based hints (app/backend/gameplan.py). Hints, not advice.
class AskIn(BaseModel):
    question: str
    mine: str | None = None


@app.get("/api/teams/{key}/gameplan")
def gameplan(key: str, mine: str | None = None):
    need(key)
    if mine: need(mine)
    return GP.build(key, mine if mine != key else None, teams, ranks, load)


@app.post("/api/teams/{key}/gameplan/ask")
def gameplan_ask(key: str, body: AskIn):
    if not os.environ.get("ANTHROPIC_API_KEY"): raise HTTPException(501, "Set ANTHROPIC_API_KEY before starting the app to use the AI assistant.")
    if not body.question.strip() or len(body.question) > 1000: raise HTTPException(400, "Write a question (up to 1000 characters).")
    plan = gameplan(key, body.mine)
    try: return {"answer": GP.ask(plan, body.question.strip())}
    except Exception as e: raise HTTPException(502, f"The AI request failed: {e}")


# Analyst review inside the app: the same sheet and five questions as review_<Team>.csv/.html (src/report/make_report.py).
QUESTIONS = ["Does this description match what you know about this team? What is right and what is wrong?", "Which parts would you use before a match and which would you skip?",
             "What is missing that you would need?", "Do the reliability notes change how you read the report?",
             "How long would it take you to get the same overview from video, and would this report shorten it?"]


@app.get("/api/teams/{key}/review")
def get_review(key: str):
    need(key); base = os.path.join(DATA, f"review_{key}.csv"); filled = os.path.join(DATA, f"review_{key}_filled.csv")
    if not os.path.exists(base): raise HTTPException(404, f"review_{key}.csv not found in {DATA}: run src/oppreport.py for this team.")
    with open(filled if os.path.exists(filled) else base, encoding="utf-8", newline="") as f: rows = list(csv.DictReader(f))
    idx = {(r["family"], r["date"], r["opponent"], r["half"], r["minute"], r["second"]): r["match"] for r in clip_index(key)}
    for r in rows: r["match"] = idx.get((r["family"], r["date"], r["opponent"], r["half"], r["minute"], r["second"]))
    ans = os.path.join(DATA, f"review_{key}_answers.json")
    return {"rows": rows, "questions": QUESTIONS, "answers": json.load(open(ans, encoding="utf-8")) if os.path.exists(ans) else None,
            "filled_file": os.path.basename(filled) if os.path.exists(filled) else None}


class ReviewIn(BaseModel):
    verdicts: list[str]
    comments: list[str]
    answers: list[str]
    reviewer: str = ""
    role: str = ""


@app.post("/api/teams/{key}/review")
def save_review(key: str, body: ReviewIn):
    """Writes review_<Team>_filled.csv (same columns as review_<Team>.csv, readable by src/report/summarize_review.py) and review_<Team>_answers.json.
    The original sheet is never changed."""
    need(key); base = os.path.join(DATA, f"review_{key}.csv")
    with open(base, encoding="utf-8", newline="") as f: r = csv.DictReader(f); cols, rows = r.fieldnames, list(r)
    if len(body.verdicts) != len(rows) or len(body.comments) != len(rows): raise HTTPException(400, f"Expected {len(rows)} verdicts and comments.")
    if any(v not in ("", "yes", "partly", "no") for v in body.verdicts): raise HTTPException(400, "Verdicts must be yes, partly, no or empty.")
    for row, v, c in zip(rows, body.verdicts, body.comments): row["coherent_with_family"], row["comment"] = v, c.strip()
    with open(os.path.join(DATA, f"review_{key}_filled.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
    json.dump({"team": need(key)["team"], "reviewer": body.reviewer, "role": body.role, "saved": time.strftime("%Y-%m-%d %H:%M"),
               "questions": [{"question": q, "answer": a} for q, a in zip(QUESTIONS, body.answers)]},
              open(os.path.join(DATA, f"review_{key}_answers.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return {"saved": f"review_{key}_filled.csv", "answered": sum(1 for v in body.verdicts if v)}


# Running the pipeline for a new team (needs StatsBomb match lists in <data>/matches and events in <data>/ev).
def sources():
    out = []
    if not os.path.isdir(os.path.join(DATA, "ev")): return out
    for p in sorted(glob.glob(os.path.join(DATA, "matches", "*.json"))):
        try: ms = json.load(open(p, encoding="utf-8"))
        except (ValueError, OSError): continue
        if not ms: continue
        count = {}
        for m in ms:
            for side in ("home_team", "away_team"):
                n = m[side][f"{side}_name"]; count[n] = count.get(n, 0) + 1
        out.append({"file": f"matches/{os.path.basename(p)}", "competition": ms[0]["competition"]["competition_name"], "season": ms[0]["season"]["season_name"],
                    "teams": sorted(({"team": t, "matches": n} for t, n in count.items()), key=lambda x: x["team"])})
    return out


@app.get("/api/sources")
def list_sources(): return sources()


JOBS = {}


class JobIn(BaseModel):
    source: str
    team: str


def _run(job):
    cmd = [sys.executable, "-X", "utf8", os.path.join(ROOT, "src", "oppreport.py"), "--statsbomb", job["source"], "--data-dir", DATA, "--team", job["team"], "--out", os.path.join(DATA, "reports_app")]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", env=dict(os.environ, MPLBACKEND="Agg"))
    for line in p.stdout:
        job["log"].append(line.rstrip()); job["log"] = job["log"][-200:]
    job["status"] = "done" if p.wait() == 0 else "failed"; job["ended"] = time.time()


@app.post("/api/jobs")
def start_job(j: JobIn):
    src = next((s for s in sources() if s["file"] == j.source), None)
    if not src: raise HTTPException(400, f"Match list {j.source} not found in {DATA}/matches.")
    if j.team not in {t["team"] for t in src["teams"]}: raise HTTPException(400, f"{j.team} does not play in {j.source}.")
    if any(x["status"] == "running" for x in JOBS.values()): raise HTTPException(409, "A report is already being generated. Wait for it to finish.")
    job = {"id": uuid.uuid4().hex[:8], "team": j.team, "key": key_of(j.team), "source": j.source, "status": "running", "log": [], "started": time.time(), "ended": None}
    JOBS[job["id"]] = job; threading.Thread(target=_run, args=(job,), daemon=True).start()
    return job


@app.get("/api/jobs/{jid}")
def get_job(jid: str):
    if jid not in JOBS: raise HTTPException(404, "Unknown job.")
    return JOBS[jid]


if os.path.isdir(DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST, "assets")), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        f = os.path.realpath(os.path.join(DIST, path))
        inside = f.startswith(os.path.realpath(DIST) + os.sep)
        if inside and os.path.isfile(f) and not f.endswith("index.html"): return FileResponse(f)
        # The page itself is never cached, so a rebuilt app shows up on a normal reload.
        return FileResponse(os.path.join(DIST, "index.html"), headers={"Cache-Control": "no-store"})
