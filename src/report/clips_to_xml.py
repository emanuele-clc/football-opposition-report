"""Clip list -> XML timeline for video tools (Hudl Sportscode / Nacsport style: ALL_INSTANCES with ID, start, end, code, labels). One file per match.
Usage:  python clips_to_xml.py <clips.csv> <out_dir> [--video-offsets offsets.csv] [--pre 3] [--post 3]
<clips.csv> is clips_<Team>.csv or restart_clips_<Team>.csv. Code = column 'family' (e.g. B2 or 'Goal kick short left'); labels = start type, passes, shot, opponent.
offsets.csv: match_id, half1_start, half2_start = video second at which each half kicks off (docs/data_format.md). Without it the video is assumed to start at
kick-off and to run without the half-time break, which is almost never true for a real video: the script warns and the times must be shifted in the tool.
NOT YET TESTED by importing into Sportscode or Nacsport: check one file in the tool before using it on a full season."""

import sys, os, colorsys
import pandas as pd
from xml.sax.saxutils import escape as E

a = sys.argv[1:]
opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
pos = [x for i, x in enumerate(a) if not x.startswith("--") and (i == 0 or not a[i - 1].startswith("--"))]
if len(pos) < 2:
    sys.exit(__doc__)
clips, out = pd.read_csv(pos[0]), pos[1]
pre, post = float(opt("--pre", 3)), float(opt("--post", 3))
os.makedirs(out, exist_ok=True)
offs = (
    pd.read_csv(opt("--video-offsets")).astype({"match_id": str}).set_index("match_id")
    if opt("--video-offsets")
    else None
)
if offs is None:
    print(
        "AVVISO: senza --video-offsets i tempi sono l'orologio di gara (secondo tempo da 45:00): vanno spostati nel programma video."
    )
codes = sorted(clips.family.astype(str).unique())
col = {c: colorsys.hsv_to_rgb(i / max(len(codes), 1), 0.55, 0.9) for i, c in enumerate(codes)}
team = os.path.basename(pos[0]).split("clips_", 1)[-1][:-4]
missing = []
for mid, g in clips.groupby("match"):
    if offs is not None and str(mid) not in offs.index:
        missing.append(str(mid))
        continue
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
        lab = [
            ("Start", r.start_type),
            ("Passes", r.passes),
            ("Shot", "yes" if r.ended_in_shot else "no"),
            ("Opponent", r.opponent),
        ]
        inst.append(
            f"<instance><ID>{i}</ID><start>{max(t - pre, 0):.1f}</start><end>{t + r.duration_s + post:.1f}</end><code>{E(str(r.family))}</code>"
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
)
