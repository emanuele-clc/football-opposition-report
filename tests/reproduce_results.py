"""Reproducibility check: reruns the result scripts (held-out validation, simple-rule comparison, null baselines, sample size, 10-team summary) with the same code
and seeds in a SEPARATE work folder and compares every output with results/ in the repo. Nothing in results/ is written or replaced, and no decision depends on the
rerun: it only checks that the committed numbers come out of the committed code (it is not a second validation).
Usage:  python -X utf8 tests/reproduce_results.py <data_dir with matches/ and ev/> <work_dir> [--jobs 6] [--only "Team"]
Takes about 15-20 minutes for 10 teams on a laptop. Exit code 0 if every file is identical."""
import sys, os, json, math, shutil, subprocess, argparse, concurrent.futures as cf
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); RES = os.path.join(REPO, "results")
TEAMS = [("9_281", "Bayer Leverkusen"), ("2_27", "Leicester City"), ("11_27", "Barcelona"), ("2_27", "Arsenal"), ("11_27", "Atlético Madrid"), ("11_27", "Real Madrid"),
         ("12_27", "Napoli"), ("12_27", "Sassuolo"), ("7_27", "Gazélec Ajaccio"), ("7_27", "Bordeaux")]
ap = argparse.ArgumentParser(); ap.add_argument("data_dir"); ap.add_argument("work_dir"); ap.add_argument("--jobs", type=int, default=6); ap.add_argument("--only"); a = ap.parse_args()
WD = os.path.abspath(a.work_dir)
if os.path.abspath(WD) in (os.path.abspath(a.data_dir), RES): sys.exit("work_dir must be a new, separate folder")
os.makedirs(WD, exist_ok=True); shutil.copytree(os.path.join(a.data_dir, "matches"), os.path.join(WD, "matches"), dirs_exist_ok=True)

def scripts(team):
    fn = team.replace(" ", "_"); h = json.load(open(f"{RES}/holdout_{fn}.json", encoding="utf-8"))
    hv = "validate_replication.py" if "H3_pass" in h["costruzione"] else "validate_holdout.py"   # the first two teams were validated before H3 existed
    return [(f"week4/{hv}", ["--confirm"]), ("week4/compare_simple_rules.py", ["--confirm"]), ("week3/stability_null_baseline.py", []), ("week4/sample_size.py", [])]

def job(arg):
    m, team, (sc, fl) = arg   # data_dir is passed as the data folder; outputs go to the current folder WD (scripts write to their data folder argument)
    r = subprocess.run([sys.executable, "-X", "utf8", os.path.join(REPO, "src", sc), f"matches/{m}.json", team, "."] + fl, cwd=WD, capture_output=True, text=True, encoding="utf-8")
    return f"{team}: {sc} exit {r.returncode}" + (f"\n{r.stderr[-400:]}" if r.returncode else "")

ev = os.path.join(WD, "ev")
if not os.path.exists(ev):
    try: os.symlink(os.path.abspath(os.path.join(a.data_dir, "ev")), ev, target_is_directory=True)
    except OSError:
        if os.name == "nt": subprocess.run(["cmd", "/c", "mklink", "/J", ev, os.path.abspath(os.path.join(a.data_dir, "ev"))], check=True, capture_output=True)
        else: raise
jobs = [(m, t, s) for m, t in TEAMS if not a.only or t == a.only for s in scripts(t)]
with cf.ThreadPoolExecutor(a.jobs) as ex:
    for line in ex.map(job, jobs): print(line, flush=True)
if not a.only: subprocess.run([sys.executable, "-X", "utf8", os.path.join(REPO, "src", "week4", "summarize_replication10.py"), os.path.join(REPO, "docs", "replication10_selection.json"), WD, os.path.join(WD, "replication10_summary.json")], capture_output=True)

def diffs(x, y, p=""):
    if isinstance(x, dict) and isinstance(y, dict):
        return [f"{p}/{k}: only in one" for k in set(x) ^ set(y)] + [d for k in set(x) & set(y) for d in diffs(x[k], y[k], f"{p}/{k}")]
    if isinstance(x, list) and isinstance(y, list):
        return [f"{p}: length {len(x)} vs {len(y)}"] if len(x) != len(y) else [d for i, (u, v) in enumerate(zip(x, y)) for d in diffs(u, v, f"{p}[{i}]")]
    if isinstance(x, float) and isinstance(y, float) and (x == y or (math.isnan(x) and math.isnan(y)) or abs(x - y) <= 1e-9 * max(1, abs(x))): return []
    return [] if x == y else [f"{p}: {x} -> {y}"]
same, bad = 0, []
for n in sorted(os.listdir(WD)):
    if n.endswith(".json") and os.path.exists(os.path.join(RES, n)):
        d = diffs(json.load(open(os.path.join(RES, n), encoding="utf-8")), json.load(open(os.path.join(WD, n), encoding="utf-8")))
        if d: bad.append((n, d))
        else: same += 1
print(f"\nidentical: {same}, different: {len(bad)}")
for n, d in bad: print(f"  {n}: {len(d)} differences, e.g. {d[:3]}")
sys.exit(1 if bad or not same else 0)
