"""Clip list -> XML timeline for video tools (Hudl Sportscode / Nacsport style: ALL_INSTANCES with ID, start, end, code, labels). One file per match.
Usage:  python clips_to_xml.py <clips.csv> <out_dir> [--video-offsets offsets.csv] [--pre 3] [--post 3] [--events-dir <dir with <match_id>.json>]
<clips.csv> is any clip list of the pipeline (clips_, restart_clips_, setpiece_clips_, transition_clips_, xt_clips_<Team>.csv). Code = column 'family'
(e.g. B2 or 'Goal kick short left'); labels = phase (B/A families), start type, passes, duration, half, clock, shot, opponent, date, plus any extra
column of the CSV (e.g. player, xt, goal).
--events-dir (StatsBomb-format events, e.g. <data dir>/ev): adds labels read from the events. For possession clips (sequences, restarts, set pieces) the
possession is the one of the team's first action at the clip time (as the app replay): shot outcome, xG (sum of the team's shots), goal, shooter, first
and last player, players involved, start and end third. For every clip: score and game state for the team before the clip (goals = shots with outcome
Goal + own goals). Transition and xT clips get only score and game state. Clips whose possession is not found get no event labels.
offsets.csv: match_id, half1_start, half2_start = video second at which each half kicks off (docs/data_format.md). Without it the video is assumed to start at
kick-off and to run without the half-time break, which is almost never true for a real video: the script warns and the times must be shifted in the tool.
NOT YET TESTED by importing into Sportscode or Nacsport: check one file in the tool before using it on a full season."""

import sys, os, colorsys, json, re
import pandas as pd
from xml.sax.saxutils import escape as E

a = sys.argv[1:]
opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
pos = [x for i, x in enumerate(a) if not x.startswith("--") and (i == 0 or not a[i - 1].startswith("--"))]
if len(pos) < 2:
    sys.exit(__doc__)
clips, out = pd.read_csv(pos[0], keep_default_na=False), pos[1]
pre, post = float(opt("--pre", 3)), float(opt("--post", 3))
evdir = opt("--events-dir")
os.makedirs(out, exist_ok=True)
offs = (
    pd.read_csv(opt("--video-offsets")).astype({"match_id": str}).set_index("match_id")
    if opt("--video-offsets")
    else None
)
if offs is None:
    print(
        "WARNING: without --video-offsets the times are the match clock (second half from 45:00): shift them in the video tool."
    )
codes = sorted(clips.family.astype(str).unique())
col = {c: colorsys.hsv_to_rgb(i / max(len(codes), 1), 0.55, 0.9) for i, c in enumerate(codes)}
base_name = os.path.basename(pos[0])
team = base_name.split("clips_", 1)[-1][:-4]
possession_clips = not base_name.startswith(("transition_clips_", "xt_clips_"))
STD = {"family", "match", "date", "opponent", "half", "minute", "second", "start_type", "passes", "duration_s", "ended_in_shot", "video_time"}
extra = [c for c in clips.columns if c not in STD]
third = lambda x: "Own third" if x < 40 else "Middle third" if x < 80 else "Final third"


def is_goal(e):
    return e["type"]["name"] == "Shot" and e["shot"]["outcome"]["name"] == "Goal"


def event_labels(ev, r):
    """Labels from the raw events for one clip (empty list if the clip cannot be matched)."""
    us = lambda e: e["team"]["name"].replace(" ", "_") == team
    near = lambda e, d: e.get("period") == r.half and e.get("minute") == r.minute and abs(e.get("second", -9) - r.second) <= d
    at = [
        e
        for d in (0, 1)
        for e in ev
        if near(e, d) and us(e) and e.get("possession_team", {}).get("name", "").replace(" ", "_") == team
    ]
    anchor = at[0] if at else next((e for d in (0, 1) for e in ev if near(e, d)), None)
    if anchor is None:
        return []
    ours = theirs = 0
    for e in ev:
        if e["index"] >= anchor["index"]:
            break
        if is_goal(e) or e["type"]["name"] == "Own Goal For":
            if us(e):
                ours += 1
            else:
                theirs += 1
    lab = [
        ("Score", f"{ours}-{theirs}"),
        ("Game state", "Winning" if ours > theirs else "Losing" if ours < theirs else "Drawing"),
    ]
    if not (possession_clips and at):
        return lab
    es = [e for e in ev if e.get("period") == r.half and e.get("possession") == anchor["possession"] and us(e)]
    players = [e["player"]["name"] for e in es if "player" in e]
    shots = [e for e in es if e["type"]["name"] == "Shot"]
    with_loc = [e for e in es if "location" in e]
    if with_loc:
        last = with_loc[-1]
        end = (last.get("pass") or last.get("carry") or last.get("shot") or {}).get("end_location") or last["location"]
        lab += [("Start third", third(with_loc[0]["location"][0])), ("End third", third(end[0]))]
    if players:
        lab += [("First player", players[0]), ("Last player", players[-1]), ("Players involved", len(set(players)))]
    if shots:
        lab += [
            ("Shot outcome", shots[-1]["shot"]["outcome"]["name"]),
            ("xG", f"{sum(s['shot'].get('statsbomb_xg') or 0 for s in shots):.2f}"),
            ("Shooter", shots[-1].get("player", {}).get("name", "")),
        ]
    lab.append(("Goal", "yes" if any(is_goal(s) for s in shots) else "no"))
    return lab


missing = []
no_events = []
for mid, g in clips.groupby("match"):
    if offs is not None and str(mid) not in offs.index:
        missing.append(str(mid))
        continue
    evp = os.path.join(evdir, f"{mid}.json") if evdir else None
    ev = json.load(open(evp, encoding="utf-8")) if evp and os.path.exists(evp) else None
    if evdir and ev is None:
        no_events.append(str(mid))
    inst = []
    for i, r in enumerate(g.itertuples(), 1):
        clock = r.minute * 60 + r.second
        t = (
            clock
            if offs is None
            else float(offs.loc[str(mid), "half1_start" if r.half == 1 else "half2_start"])
            + clock
            - (0 if r.half == 1 else 2700)
        )
        fam = str(r.family)
        lab = (
            [("Phase", "Build-up" if fam[0] == "B" else "Advanced")] if re.fullmatch(r"[AB]\d+", fam) else []
        ) + [
            ("Start", r.start_type),
            ("Passes", r.passes),
            ("Duration (s)", r.duration_s),
            ("Half", r.half),
            ("Clock", f"{r.minute:02d}:{r.second:02d}"),
            ("Shot", "yes" if r.ended_in_shot else "no"),
            ("Opponent", r.opponent),
            ("Date", r.date),
        ]
        lab += [(c.replace("_", " ").capitalize() if c != "xt" else "xT", getattr(r, c)) for c in extra if str(getattr(r, c)) != ""]
        if ev is not None:
            lab += [x for x in event_labels(ev, r) if x[0] not in {k for k, _ in lab}]
        inst.append(
            f"<instance><ID>{i}</ID><start>{max(t - pre, 0):.1f}</start><end>{t + r.duration_s + post:.1f}</end><code>{E(fam)}</code>"
            + "".join(f"<label><group>{E(k)}</group><text>{E(str(v))}</text></label>" for k, v in lab)
            + "</instance>"
        )
    rows = "".join(
        f"<row><code>{E(c)}</code><R>{int(col[c][0] * 65535)}</R><G>{int(col[c][1] * 65535)}</G><B>{int(col[c][2] * 65535)}</B></row>"
        for c in codes
        if c in set(g.family.astype(str))
    )
    f = os.path.join(out, f"{team}_{g.date.iloc[0]}_{str(g.opponent.iloc[0]).replace(' ', '_')}_{mid}.xml")
    open(f, "w", encoding="utf-8").write(
        f"<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<file><ALL_INSTANCES>{''.join(inst)}</ALL_INSTANCES><ROWS>{rows}</ROWS></file>\n"
    )
print(
    f"{clips.match.nunique() - len(missing)} file XML in {out}"
    + (f"; {len(missing)} partite saltate perche' assenti da offsets.csv" if missing else "")
    + (f"; {len(no_events)} partite senza file eventi (solo etichette del CSV)" if no_events else "")
)
