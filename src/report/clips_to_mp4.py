"""Clip list -> one MP4 per clip, cut from the match video, plus a playlist: the analyst can use them with any video tool (no import needed).
Usage:  python clips_to_mp4.py <clips.csv> <video.mp4> <out_dir> --match <match_id> [--half1 <s>] [--half2 <s>] [--video-offsets offsets.csv]
                               [--family B1|B2] [--shot] [--pre 3] [--post 3] [--one-file]
<clips.csv>: any clip list of the pipeline (clips_, restart_clips_, setpiece_clips_, transition_clips_, xt_clips_<Team>.csv). One video is one match,
so --match is required. Times: video second = half start + match clock (second half: clock minus 45:00), as in docs/data_format.md. The half
starts come from --half1/--half2 or from offsets.csv (match_id, half1_start, half2_start); without either the video is assumed to start at
kick-off with no half-time break (true only for a test video), and the script says so.
Clip = from <pre> s before the clip time to <post> s after its end (duration_s); clips with no duration (transitions) last 10 s after the clip time.
--family keeps only those labels (separate with |); --shot only clips that ended in a shot; --one-file also joins all clips into all_clips.mp4.
Needs ffmpeg: the one bundled with the Python package imageio-ffmpeg (requirements.txt), or ffmpeg on the PATH.
Files: <nn>_<label>_<half>H_<mm>-<ss>.mp4 and playlist.m3u (opens in VLC and most players)."""

import os, re, shutil, subprocess, sys
import pandas as pd

a = sys.argv[1:]
opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
pos = [x for i, x in enumerate(a) if not x.startswith("--") and (i == 0 or not a[i - 1].startswith("--") or a[i - 1] in ("--shot", "--one-file"))]
if len(pos) < 3 or not opt("--match"):
    sys.exit(__doc__)
CSV, VIDEO, OUT = pos[:3]
MATCH = str(opt("--match"))
PRE, POST = float(opt("--pre", 3)), float(opt("--post", 3))


def ffmpeg():
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        exe = shutil.which("ffmpeg")
        if not exe:
            sys.exit("ffmpeg not found: pip install imageio-ffmpeg (or install ffmpeg and put it on the PATH).")
        return exe


if not os.path.exists(VIDEO):
    sys.exit(f"Video not found: {VIDEO}")
d = pd.read_csv(CSV, dtype={"match": str})
d = d[d["match"] == MATCH]
if opt("--family"):
    d = d[d["family"].isin(opt("--family").split("|"))]
if "--shot" in a:
    d = d[d["ended_in_shot"] == 1]
if d.empty:
    sys.exit(f"No clips of match {MATCH} in {CSV} with these filters.")

if opt("--half1") is not None or opt("--half2") is not None:
    h1, h2 = float(opt("--half1", 0)), float(opt("--half2", 2700))
elif opt("--video-offsets"):
    o = pd.read_csv(opt("--video-offsets"), dtype={"match_id": str}).set_index("match_id")
    if MATCH not in o.index:
        sys.exit(f"Match {MATCH} is not in {opt('--video-offsets')}.")
    h1, h2 = float(o.loc[MATCH, "half1_start"]), float(o.loc[MATCH, "half2_start"])
else:
    h1, h2 = 0.0, 2700.0
    print(
        "No half starts given (--half1/--half2 or --video-offsets): assuming the video starts at kick-off with no half-time break. "
        "For a real match video, give the video second of each kick-off."
    )

os.makedirs(OUT, exist_ok=True)
exe = ffmpeg()
files = []
d = d.sort_values(["half", "minute", "second"])
for n, r in enumerate(d.itertuples(), 1):
    clock = int(r.minute) * 60 + int(r.second)
    t0 = (h1 + clock) if int(r.half) == 1 else (h2 + clock - 2700)
    dur = float(getattr(r, "duration_s", 0) or 0)
    start = max(t0 - PRE, 0)
    length = (t0 - start) + (dur + POST if dur > 0 else 10)
    label = re.sub(r"[^A-Za-z0-9]+", "-", str(r.family)).strip("-")[:30]
    name = f"{n:02d}_{label}_{int(r.half)}H_{int(r.minute):02d}-{int(r.second):02d}.mp4"
    # re-encoded, so the cut starts exactly at the clip (a stream copy would start at the previous keyframe)
    p = subprocess.run(
        [exe, "-y", "-loglevel", "error", "-ss", f"{start:.2f}", "-i", VIDEO, "-t", f"{length:.2f}",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", "-c:a", "aac",
         os.path.join(OUT, name)],
        capture_output=True, text=True,
    )
    if p.returncode:
        print(f"skipped {name}: {p.stderr.strip()[:200]}")
        continue
    files.append(name)
    print(f"{name}  ({start:.0f}-{start + length:.0f} s of the video)")

with open(os.path.join(OUT, "playlist.m3u"), "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n" + "".join(f"{x}\n" for x in files))
if "--one-file" in a and files:
    lst = os.path.join(OUT, "_list.txt")
    with open(lst, "w", encoding="utf-8") as f:
        f.write("".join(f"file '{x}'\n" for x in files))
    subprocess.run([exe, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                    os.path.join(OUT, "all_clips.mp4")], check=True)
    os.remove(lst)
    print("all_clips.mp4 written")
print(f"{len(files)} clips in {OUT}")
