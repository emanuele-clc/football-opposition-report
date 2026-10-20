"""Tracking lab: replays of the DFL open tracking data (Bassek et al. 2025, CC BY 4.0) with pitch control (src/tracking/pitch_control.py, literature parameters).
Reads <tracking dir>/npz written by src/tracking/dfl_load.py; the folder is OPPREPORT_TRACKING or ~/dfl_tracking. Not part of the StatsBomb report: other matches, other data."""

import functools, glob, json, os, sys
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "tracking"))
import pitch_control as PC

TRACK = os.path.abspath(os.environ.get("OPPREPORT_TRACKING") or os.path.join(os.path.expanduser("~"), "dfl_tracking"))
GX, GY = 24, 16  # control grid shown in the app (cells of about 4.4 x 4.3 m)


def results():
    """The two exploratory results files, as written by src/tracking/*.py (None when not produced yet)."""
    rd = os.path.join(ROOT, "results")
    out = {}
    for k, f in (("pitch_control", "exploratory_pitch_control.json"), ("ghosting", "exploratory_ghosting.json")):
        p = os.path.join(rd, f)
        out[k] = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None
    return out


def available():
    return bool(glob.glob(os.path.join(TRACK, "npz", "*.npz")))


@functools.lru_cache(maxsize=8)
def meta(mid):
    p = os.path.join(TRACK, "npz", f"{mid}_events.json")
    if not os.path.exists(p):
        return None
    return json.load(open(p, encoding="utf-8"))


@functools.lru_cache(maxsize=2)
def arrays(mid):
    a = np.load(os.path.join(TRACK, "npz", f"{mid}.npz"))
    return {k: a[k] for k in a.files}


def clock(m, h, frame):
    s = (frame - m["halves"][str(h)]["n0"]) / 25 + (45 * 60 if h == 2 else 0)
    return f"{int(s // 60)}:{int(s % 60):02d}"


def matches():
    out = []
    for p in sorted(glob.glob(os.path.join(TRACK, "npz", "*_events.json"))):
        m = meta(os.path.basename(p)[:-12])
        P = m["players"]
        name = lambda t: m["home_name"] if t == m["home"] else m["guest_name"]
        goals = [
            dict(
                half=e["half"],
                frame=e["frame"],
                team=name(e["team"]),
                side="home" if e["team"] == m["home"] else "guest",
                player=P.get(e["player"], {}).get("name", ""),
                clock=clock(m, e["half"], e["frame"]),
                xg=e.get("xg"),
            )
            for e in m["events"]
            if e["kind"] == "shot" and e["sub"] == "SuccessfulShot"
        ]
        out.append(
            dict(
                match=m["match"],
                date=m["date"],
                competition=m["competition"],
                home=m["home_name"],
                guest=m["guest_name"],
                result=m["result"],
                goals=goals,
            )
        )
    return sorted(out, key=lambda r: r["date"])


@functools.lru_cache(maxsize=32)
def clip(mid, half, frame, before=10.0, after=3.0):
    """Frames at 5 Hz from `before` s before to `after` s after `frame`; positions mapped to the app pitch (0-120 x 0-80, home attacking left to right
    in this half's picture is NOT forced: the picture shows the stadium view, with home's attacking direction given); control of the home team on a grid.
    """
    m = meta(mid)
    a = arrays(mid)
    P = m["players"]
    h = int(half)
    xy = a[f"xy_{h}"].astype(float)
    ball = a[f"ball_{h}"].astype(float)
    alive = a[f"alive_{h}"]
    n0 = int(a[f"N0_{h}"])
    pids = list(a[f"pids_{h}"])
    f = frame - n0
    lo, hi = max(f - int(before * 25), 5), min(f + int(after * 25), xy.shape[1] - 6)
    vel = PC.velocities(xy[:, lo - 5 : hi + 6])[:, 5:-5]
    home = np.array([P[p]["team"] == m["home"] for p in pids]).astype(int)
    gk = np.array([P[p]["pos"] == "TW" for p in pids])
    gx, gy = np.meshgrid(
        np.linspace(-52.5 + 105 / GX / 2, 52.5 - 105 / GX / 2, GX),
        np.linspace(-34 + 68 / GY / 2, 34 - 68 / GY / 2, GY),
        indexing="ij",
    )
    G = np.c_[gx.ravel(), gy.ravel()]
    X = lambda v: round(float((v + 52.5) / 105 * 120), 2)
    Y = lambda v: round(float((34 - v) / 68 * 80), 2)
    frames = []
    for k in range(lo, hi + 1, 5):
        pos = xy[:, k]
        v = vel[:, k - lo]
        b = ball[k, :2]
        c = PC.control(pos, v, home, gk, b, G) if np.isfinite(b).all() else np.full(len(G), 0.5)
        frames.append(
            dict(
                t=round((k - f) / 25, 2),
                alive=int(alive[k]),
                ball=[X(b[0]), Y(b[1])] if np.isfinite(b).all() else None,
                p=[[X(q[0]), Y(q[1])] if np.isfinite(q).all() else None for q in pos],
                pc=[int(round(100 * x)) for x in c],
            )
        )
    players = [
        dict(name=P[p]["name"], side="home" if P[p]["team"] == m["home"] else "guest", gk=bool(P[p]["pos"] == "TW"))
        for p in pids
    ]
    d = m["halves"][str(h)]["dir"]
    return dict(
        match=mid,
        half=h,
        clock=clock(m, h, frame),
        home=m["home_name"],
        guest=m["guest_name"],
        home_attacks="right" if d == 1 else "left",
        grid=[GX, GY],
        players=players,
        frames=frames,
    )
