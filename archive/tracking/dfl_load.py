"""Loader for the DFL open tracking + event data (Bassek, Rein, Weber & Memmert 2025, "An integrated dataset of spatiotemporal and event data in elite soccer",
Scientific Data 12:195, CC BY 4.0, figshare 28196177): 7 Bundesliga / 2. Bundesliga matches 2022/23, positions of all players and the ball at 25 Hz plus official events.
Usage:  python dfl_load.py <dfl_dir>        (folder with the DFL_*.xml files; writes <dfl_dir>/npz/<MatchId>.npz and <MatchId>_events.json, skips matches done)
Raw files stay outside the repo, like the StatsBomb files.
What is stored, per half (1, 2): frame numbers N, ball x/y/z, ball alive (BallStatus 1), ball possession (1 home, 2 guest), and for every player x/y (NaN when not
on the pitch). Coordinates in metres, origin at the centre spot, x along the length (-52.5..52.5), y along the width (-34..34), as in the DFL files.
'dir' gives, per half, +1 if the home team attacks towards +x, else -1 (from the mean x of the home goalkeeper in the half: he stands on the side he defends).
Events: passes and crosses (Play) with team, player, recipient, outcome (successfullyCompleted = completed), operator time, and a frame:
- sync (fixed before looking at results): the operator time is converted to a frame (frame 10000 = first tracked frame of the half, 25 Hz); then, within
  +/- 1.5 s, the frame where the ball is closest to the passer is taken as the pass frame. Shots carry DFL's own 'CalculatedFrame', used to check the sync."""

import sys, os, re, json, glob
from datetime import datetime
import numpy as np

FR = re.compile(r'<Frame N="(\d+)"[^>]*? X="([-\d.]+)" Y="([-\d.]+)"(?: Z="([-\d.]+)")?')
BS = re.compile(r'BallPossession="(\d)" BallStatus="(\d)"')
FS = re.compile(r'<FrameSet GameSection="(\w+)" MatchId="[^"]+" TeamId="([^"]+)" PersonId="([^"]+)"')
HALF = {"firstHalf": 1, "secondHalf": 2}
ts = lambda s: datetime.fromisoformat(s).timestamp()


def info(path):
    s = open(path, encoding="utf-8").read()
    g = re.search(r"<General ([^>]*)/>", s).group(1)
    a = dict(re.findall(r'(\w+)="([^"]*)"', g))
    players = {}
    for team in re.finditer(r"<Team ([^>]*)>(.*?)</Team>", s, re.S):
        t = dict(re.findall(r'(\w+)="([^"]*)"', team.group(1)))
        for p in re.finditer(r"<Player ([^>]*)/>", team.group(2)):
            q = dict(re.findall(r'(\w+)="([^"]*)"', p.group(1)))
            players[q["PersonId"]] = dict(
                team=t["TeamId"],
                role=t["Role"],
                name=q.get("Shortname", q["PersonId"]),
                pos=q.get("PlayingPosition", ""),
                start=q.get("Starting") == "true",
            )
    return dict(
        match=a["MatchId"],
        home=a["HomeTeamId"],
        guest=a["GuestTeamId"],
        home_name=a["HomeTeamName"],
        guest_name=a["GuestTeamName"],
        result=a["Result"],
        date=a["KickoffTime"][:10],
        competition=a["CompetitionName"],
        players=players,
    )


def positions(path):
    sets = {}
    cur = None
    ball = False
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("<Frame "):
                m = FR.match(line)
                b = BS.search(line) if ball else None
                cur.append(
                    (
                        int(m[1]),
                        float(m[2]),
                        float(m[3]),
                        float(m[4] or 0),
                        int(b[1]) if b else 0,
                        int(b[2]) if b else 0,
                    )
                )
            elif line.startswith("<FrameSet"):
                m = FS.match(line)
                cur = []
                sets[(HALF.get(m[1], 0), m[2], m[3])] = cur
                ball = m[2] == "BALL"
    return sets


def events(path):
    s = open(path, encoding="utf-8").read()
    out = []
    for m in re.finditer(r"<Event ([^>]*)>\s*<(\w+) ([^>]*?)/?>(\s*<(\w+)[^>]*>)?", s):
        e = dict(re.findall(r'([\w-]+)="([^"]*)"', m.group(1)))
        a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(3)))
        kind = m.group(2)
        if kind == "KickOff":  # the kick-off pass is nested one level deeper; game section is on KickOff
            continue
        if kind not in ("Play", "ShotAtGoal"):
            continue
        out.append(
            dict(
                id=e["EventId"],
                kind="pass" if kind == "Play" else "shot",
                sub=m.group(5) or "",
                time=ts(e["EventTime"]),
                team=a.get("Team"),
                player=a.get("Player"),
                recipient=a.get("Recipient"),
                outcome=a.get("Evaluation", ""),
                open_play=a.get("FromOpenPlay", "true") == "true",
                calc_frame=int(e["CalculatedFrame"]) if "CalculatedFrame" in e else None,
                xg=float(a["xG"]) if "xG" in a else None,
            )
        )
    return out


def build(dfl, mid):
    I = info(glob.glob(f"{dfl}/DFL_02_01_matchinformation_*_{mid}.xml")[0])
    S = positions(glob.glob(f"{dfl}/DFL_04_03_positions_raw_observed_*_{mid}.xml")[0])
    arr = {}
    meta = dict(I, halves={})
    for h in (1, 2):
        ball = np.array(next(v for (hh, t, p), v in S.items() if hh == h and t == "BALL"), dtype=float)
        N = ball[:, 0].astype(int)
        n0 = N[0]
        F = N[-1] - n0 + 1
        bx = np.full((F, 3), np.nan)
        bx[N - n0] = ball[:, 1:4]
        alive = np.zeros(F, np.int8)
        alive[N - n0] = ball[:, 5]
        poss = np.zeros(F, np.int8)
        poss[N - n0] = ball[:, 4]
        pids = sorted(p for (hh, t, p) in S if hh == h and t not in ("BALL", "referee"))
        xy = np.full((len(pids), F, 2), np.nan, dtype=np.float32)
        for i, p in enumerate(pids):
            v = np.array(next(vv for (hh, t, pp), vv in S.items() if hh == h and pp == p), dtype=float)
            k = v[:, 0].astype(int) - n0
            ok = (k >= 0) & (k < F)
            xy[i, k[ok]] = v[ok, 1:3]
        gk = [
            i
            for i, p in enumerate(pids)
            if I["players"].get(p, {}).get("pos") == "TW" and I["players"][p]["role"] == "home"
        ]
        d = -1 if gk and np.nanmean(xy[gk[0], :, 0]) > 0 else 1
        arr.update(
            {
                f"N0_{h}": n0,
                f"ball_{h}": bx.astype(np.float32),
                f"alive_{h}": alive,
                f"poss_{h}": poss,
                f"xy_{h}": xy,
                f"pids_{h}": np.array(pids),
            }
        )
        meta["halves"][h] = dict(n0=int(n0), frames=int(F), dir=d)
    return I, arr, meta


def frame_time(dfl, mid, h, n0):
    """UTC time of frame n0 of half h, read from the ball FrameSet."""
    path = glob.glob(f"{dfl}/DFL_04_03_positions_raw_observed_*_{mid}.xml")[0]
    inside = False
    for l in open(path, encoding="utf-8"):
        if l.startswith("<FrameSet"):
            inside = 'TeamId="BALL"' in l and f'GameSection="{["", "firstHalf", "secondHalf"][h]}"' in l
        elif inside and l.startswith(f'<Frame N="{n0}"'):
            return datetime.fromisoformat(l.split('T="')[1].split('"')[0]).timestamp()


def sync(E, arr, meta, dfl, mid):
    t0 = {h: frame_time(dfl, mid, h, meta["halves"][h]["n0"]) for h in (1, 2)}
    out = []
    for e in E:
        h = 2 if e["time"] >= t0[2] - 60 else 1
        n0 = meta["halves"][h]["n0"]
        F = meta["halves"][h]["frames"]
        f = int(round((e["time"] - t0[h]) * 25))
        if f < 0 or f >= F:
            continue
        e = dict(e, half=h, frame_raw=f + n0)
        pids = list(arr[f"pids_{h}"])
        if e["player"] in pids:
            lo, hi = max(f - 37, 0), min(f + 38, F)
            i = pids.index(e["player"])
            d = np.linalg.norm(arr[f"xy_{h}"][i, lo:hi] - arr[f"ball_{h}"][lo:hi, :2], axis=1)
            if np.isfinite(d).any():
                f = lo + int(np.nanargmin(d))
                e["sync_dist"] = float(np.nanmin(d))
        e["frame"] = f + n0
        out.append(e)
    return out


if __name__ == "__main__":
    dfl = sys.argv[1]
    os.makedirs(f"{dfl}/npz", exist_ok=True)
    for p in sorted(glob.glob(f"{dfl}/DFL_02_01_matchinformation_*.xml")):
        mid = p.rsplit("_", 1)[1][:-4]
        if os.path.exists(f"{dfl}/npz/{mid}.npz"):
            print("skip", mid)
            continue
        I, arr, meta = build(dfl, mid)
        E = sync(events(glob.glob(f"{dfl}/DFL_03_02_events_raw_*_{mid}.xml")[0]), arr, meta, dfl, mid)
        np.savez_compressed(f"{dfl}/npz/{mid}.npz", **arr)
        json.dump(dict(meta, events=E), open(f"{dfl}/npz/{mid}_events.json", "w", encoding="utf-8"), ensure_ascii=False)
        sh = [e for e in E if e["kind"] == "shot" and e["calc_frame"]]
        lag = [abs(e["frame"] - e["calc_frame"]) / 25 for e in sh]
        print(
            mid,
            I["home_name"],
            "-",
            I["guest_name"],
            I["result"],
            f"{sum(e['kind'] == 'pass' for e in E)} passes,",
            f"sync check on {len(sh)} shots: median |diff| {np.median(lag) if lag else float('nan'):.2f} s",
        )
